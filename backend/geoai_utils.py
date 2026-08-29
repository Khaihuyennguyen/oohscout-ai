"""
geoai_utils.py — GeoAI Essentials shared utility module
Canonical utilities used across Ch05–Ch14 of GeoAI Essentials by Milan Janosov.

Contents are organised into seven sections:

    SETUP               seed_everything, get_device
    FIGURE STYLE        apply_style() (opt-in)
    ARCHITECTURES       UNet, Siamese*, PatchClassifier, CarEncoder,
                        HeightRegressor, ScalarLSTM, ConvLSTM*, CloudAutoencoder
    DATASETS            PatchDataset, PatchClassDataset, CarPatchDataset,
                        HeightDataset, ChangeDataset, NDVISequenceDataset,
                        ScalarSeqDataset, InpaintDataset
    TRAINING            bce_dice, train_model, train_classifier,
                        train_regressor, plot_history
    EVALUATION          iou_score, evaluate_segmentation,
                        compute_class_weights, compute_ap
    SPATIAL UTILITIES   spatial_split_lr, stretch, extract_patches_balanced,
                        sliding_window_inference, predict_full_scene,
                        sliding_window_detect, majority_vote
    ANNOTATION          BBoxAnnotator
    SENTINEL-2 HELPERS  search_best_any, search_matched_reference,
                        file_grid_key, cache_is_valid, download_month,
                        assert_monthly_grids_match
"""

# ────────────────────────────────────────────────────────────────────────────
# ── IMPORTS ──
# ────────────────────────────────────────────────────────────────────────────

import random
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import torch
import torch.nn as nn
import torch.optim as optim
from pathlib import Path
from torch.utils.data import Dataset, DataLoader


# ────────────────────────────────────────────────────────────────────────────
# ── SETUP ──
# ────────────────────────────────────────────────────────────────────────────

def seed_everything(seed=42):
    """Seed Python random, NumPy, and PyTorch (+ CUDA) for reproducible runs."""
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(seed)


def get_device():
    """Return the best available device: CUDA > MPS > CPU."""
    if torch.cuda.is_available():
        return torch.device('cuda')
    if torch.backends.mps.is_available():
        return torch.device('mps')
    return torch.device('cpu')


# ────────────────────────────────────────────────────────────────────────────
# ── FIGURE STYLE ──
# ────────────────────────────────────────────────────────────────────────────
#
# Opt-in style: chapters call apply_style() in their Setting Up section.
# Not applied at module import — importing geoai_utils does not mutate any
# global matplotlib state.
#
# Usage in a chapter:
#     from geoai_utils import apply_style
#     apply_style()
#     fig, axes = plt.subplots(1, 3, figsize=(18, 5))


def apply_style():
    """Apply the GeoAI Essentials global matplotlib style (opt-in, per-chapter).

    Consolidates the rcParams block used across Ch07, Ch08, Ch11, Ch12, Ch13,
    and Ch14. Chapters call this once in their Setting Up section after the
    imports. Does nothing if never called — no side effects on import.
    """
    plt.rcParams.update({
        'figure.dpi':        120,
        'figure.titlesize':   16,
        'axes.titlesize':     13,
        'axes.labelsize':     11,
        'legend.fontsize':    10,
        'axes.spines.top':    False,
        'axes.spines.right':  False,
    })


# ────────────────────────────────────────────────────────────────────────────
# ── ARCHITECTURES ──
# ────────────────────────────────────────────────────────────────────────────

class UNet(nn.Module):
    """U-Net encoder-decoder with skip connections for pixel-level segmentation.

    in_channels: number of input bands (1 for single-channel, 4+ for Sentinel-2).
    n_classes:   1 for binary (BCEWithLogitsLoss); >1 multi-class (CrossEntropy).
    BatchNorm after every Conv2d stabilises training across varying input statistics.
    Returns raw logits — apply sigmoid (binary) or argmax (multi-class) at inference.
    """
    def __init__(self, in_channels=1, n_classes=1):
        """Build the U-Net encoder, bottleneck, and decoder blocks."""
        super().__init__()
        self.enc1 = nn.Sequential(
            nn.Conv2d(in_channels, 16, 3, padding=1), nn.BatchNorm2d(16), nn.ReLU(),
            nn.Conv2d(16, 16, 3, padding=1),          nn.BatchNorm2d(16), nn.ReLU()
        )
        self.pool1 = nn.MaxPool2d(2)
        self.enc2 = nn.Sequential(
            nn.Conv2d(16, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),
            nn.Conv2d(32, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU()
        )
        self.pool2 = nn.MaxPool2d(2)
        self.bottleneck = nn.Sequential(
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(),
            nn.Conv2d(64, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU()
        )
        self.up1  = nn.ConvTranspose2d(64, 32, 2, stride=2)
        self.dec1 = nn.Sequential(
            nn.Conv2d(64, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),
            nn.Conv2d(32, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU()
        )
        self.up2  = nn.ConvTranspose2d(32, 16, 2, stride=2)
        self.dec2 = nn.Sequential(
            nn.Conv2d(32, 16, 3, padding=1), nn.BatchNorm2d(16), nn.ReLU(),
            nn.Conv2d(16, 16, 3, padding=1), nn.BatchNorm2d(16), nn.ReLU()
        )
        self.out = nn.Conv2d(16, n_classes, 1)   # raw logits — no activation

    def forward(self, x):
        """Encode, decode with cropped skip connections, and return logits."""
        e1 = self.enc1(x);  p1 = self.pool1(e1)
        e2 = self.enc2(p1); p2 = self.pool2(e2)
        b  = self.bottleneck(p2)
        d1 = self.up1(b)
        d1 = self.dec1(torch.cat([d1, e2[:, :, :d1.shape[2], :d1.shape[3]]], 1))
        d2 = self.up2(d1)
        d2 = self.dec2(torch.cat([d2, e1[:, :, :d2.shape[2], :d2.shape[3]]], 1))
        return self.out(d2)


class SiameseEncoder(nn.Module):
    """Shared encoder branch for bi-temporal change detection (Ch09).

    Applied independently to both dates; returns bottleneck + skip connections.
    Output: (bottleneck (B,64,H/4,W/4), e1 (B,16,H,W), e2 (B,32,H/2,W/2)).
    NOTE: architecture differs from UNet — no decoder here; used inside
    SiameseChangeDetector only.
    """
    def __init__(self, in_channels=3):
        """Build the shared encoder and bottleneck blocks."""
        super().__init__()
        self.enc1 = nn.Sequential(
            nn.Conv2d(in_channels, 16, 3, padding=1), nn.BatchNorm2d(16), nn.ReLU(),
            nn.Conv2d(16, 16, 3, padding=1),           nn.BatchNorm2d(16), nn.ReLU()
        )
        self.pool1 = nn.MaxPool2d(2)
        self.enc2  = nn.Sequential(
            nn.Conv2d(16, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),
            nn.Conv2d(32, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU()
        )
        self.pool2 = nn.MaxPool2d(2)
        self.bottleneck = nn.Sequential(
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(),
            nn.Conv2d(64, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU()
        )

    def forward(self, x):
        """Return the bottleneck plus the two skip-connection maps."""
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool1(e1))
        b  = self.bottleneck(self.pool2(e2))
        return b, e1, e2   # bottleneck + skip connections for decoder


class SiameseChangeDetector(nn.Module):
    """Siamese U-Net for binary pixel-level change detection (Ch09).

    Two shared-weight SiameseEncoder branches process t1 and t2 independently.
    Bottleneck features are concatenated and decoded to a per-pixel change map.
    Output: (B, 1, H, W) logits — apply sigmoid to get change probability.
    """
    def __init__(self, in_channels=3):
        """Build the shared encoder and the change-map decoder."""
        super().__init__()
        self.encoder = SiameseEncoder(in_channels)   # shared weights for both dates
        # 64+64 concatenated bottleneck
        self.up1  = nn.ConvTranspose2d(128, 64, 2, stride=2)
        self.dec1 = nn.Sequential(
            nn.Conv2d(64 + 32 + 32, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),
            nn.Conv2d(32, 32, 3, padding=1),             nn.BatchNorm2d(32), nn.ReLU()
        )
        self.up2  = nn.ConvTranspose2d(32, 16, 2, stride=2)
        self.dec2 = nn.Sequential(
            nn.Conv2d(16 + 16 + 16, 16, 3, padding=1), nn.BatchNorm2d(16), nn.ReLU(),
            nn.Conv2d(16, 16, 3, padding=1),             nn.BatchNorm2d(16), nn.ReLU()
        )
        self.out  = nn.Conv2d(16, 1, 1)   # binary change logit

    def forward(self, x1, x2):
        """Encode both dates, fuse features, and return the change logits."""
        b1, e1_t1, e2_t1 = self.encoder(x1)
        b2, e1_t2, e2_t2 = self.encoder(x2)
        b  = torch.cat([b1, b2], dim=1)                       # (B, 128, H/4, W/4)
        d1 = self.up1(b)
        e2_skip = torch.cat([e2_t1, e2_t2], dim=1)            # (B, 64, H/2, W/2)
        d1 = self.dec1(torch.cat([d1, e2_skip[
            :, :, :d1.shape[2], :d1.shape[3]]], dim=1))
        d2 = self.up2(d1)
        e1_skip = torch.cat([e1_t1, e1_t2], dim=1)            # (B, 32, H, W)
        d2 = self.dec2(torch.cat([d2, e1_skip[
            :, :, :d2.shape[2], :d2.shape[3]]], dim=1))
        return self.out(d2)                                    # (B, 1, H, W) logits


class PatchClassifier(nn.Module):
    """Single encoder block + GAP + two-layer head for patch classification (Ch06).

    One MaxPool stage is sufficient for 16×16 patches — two stages collapse
    the spatial map to 2×2 before GAP runs. BatchNorm after every Conv2d
    stabilises training on small patch datasets.
    Output: (B, n_classes) logits — one prediction per patch.
    """
    def __init__(self, in_channels=5, n_classes=3):
        """Build the encoder, global pooling, and classification head."""
        super().__init__()
        self.enc = nn.Sequential(
            nn.Conv2d(in_channels, 32, 3, padding=1),
            nn.BatchNorm2d(32), nn.ReLU(),
            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64), nn.ReLU(),
            nn.MaxPool2d(2),                         # (B, 64, 8, 8) for 16×16 input
            nn.Conv2d(64, 128, 3, padding=1),
            nn.BatchNorm2d(128), nn.ReLU(),
        )
        self.gap  = nn.AdaptiveAvgPool2d(1)          # (B, 128, 1, 1)
        self.head = nn.Sequential(
            nn.Linear(128, 64), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(64, n_classes),
        )

    def forward(self, x):
        """Encode, pool, and return per-patch class logits."""
        x = self.gap(self.enc(x)).flatten(1)
        return self.head(x)


class CarEncoder(nn.Module):
    """Lightweight binary classifier for 64×64 RGB patches (Ch07, car detection).

    Conv block + BatchNorm + Global Average Pooling + linear head.
    Output: (B,) scalar logits — sigmoid gives car probability.
    Architecture: binary variant (one logit, BCEWithLogitsLoss).
    """
    def __init__(self, in_channels=3):
        """Build the encoder, global pooling, and binary head."""
        super().__init__()
        self.enc = nn.Sequential(
            nn.Conv2d(in_channels, 16, 3, padding=1),
            nn.BatchNorm2d(16), nn.ReLU(),
            nn.Conv2d(16, 32, 3, padding=1),
            nn.BatchNorm2d(32), nn.ReLU(),
            nn.MaxPool2d(2),
        )
        self.gap  = nn.AdaptiveAvgPool2d(1)
        self.head = nn.Sequential(
            nn.Linear(32, 16),
            nn.BatchNorm1d(16), nn.ReLU(),
            nn.Dropout(0.3),                         # regularises a small training set
            nn.Linear(16, 1),
        )

    def forward(self, x):
        """Encode, pool, and return one logit per patch."""
        features = self.enc(x)                       # (B, 32, H/2, W/2)
        pooled   = self.gap(features)                # (B, 32, 1, 1)
        flat     = pooled.flatten(1)                 # (B, 32)
        logit    = self.head(flat)                   # (B, 1)
        return logit.squeeze(1)                      # (B,) — one logit per patch


class HeightRegressor(nn.Module):
    """CNN encoder + GAP + scalar output for patch-level height regression (Ch08).

    Three Conv2d→BatchNorm2d→ReLU blocks with no MaxPool — same building
    block pattern as Ch06/Ch07 encoders, different depth and no decoder.
    Patch-size-agnostic: GAP collapses any spatial input to (B, 64).
    Output: (B,) scalar in metres — no activation, raw linear value.
    """
    def __init__(self, in_channels=5):
        """Build the encoder, global pooling, and regression head."""
        super().__init__()
        self.enc = nn.Sequential(
            nn.Conv2d(in_channels, 16, 3, padding=1),
            nn.BatchNorm2d(16), nn.ReLU(),
            nn.Conv2d(16, 32, 3, padding=1),
            nn.BatchNorm2d(32), nn.ReLU(),
            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64), nn.ReLU(),
        )
        self.gap  = nn.AdaptiveAvgPool2d(1)
        self.head = nn.Sequential(
            nn.Linear(64, 32), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(32, 1),
        )

    def forward(self, x):
        """Encode, pool, and return one height value per patch."""
        features = self.enc(x)                       # (B, 64, H, W)
        pooled   = self.gap(features)                # (B, 64, 1, 1)
        flat     = pooled.flatten(1)                 # (B, 64)
        output   = self.head(flat)                   # (B, 1)
        return output.squeeze(1)                     # (B,) — height in metres


class ScalarLSTM(nn.Module):
    """Stacked LSTM over a scalar time series; predicts the next value (Ch10).

    Input:  (B, T, 1) — sequence of mean NDVI values.
    Output: (B, 1)    — predicted next value.
    """
    def __init__(self, hidden_size=32, num_layers=2):
        """Build the stacked LSTM and the linear output head."""
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=1, hidden_size=hidden_size,
            num_layers=num_layers, batch_first=True, dropout=0.2,
        )
        self.head = nn.Linear(hidden_size, 1)

    def forward(self, x):
        """Run the LSTM and map the last step to the next value."""
        out, _ = self.lstm(x)                        # (B, T, hidden)
        return self.head(out[:, -1])                 # last time step → (B, 1)


class ConvLSTMCell(nn.Module):
    """Single ConvLSTM cell; replaces LSTM matrix multiplies with convolutions (Ch10).

    Input and hidden state are spatial feature maps (not vectors).
    All four gates (i, f, g, o) are computed in one convolution for efficiency.
    """
    def __init__(self, in_channels, hidden_channels, kernel_size=3):
        """Build the single fused gate convolution."""
        super().__init__()
        pad = kernel_size // 2
        self.gates = nn.Conv2d(
            in_channels + hidden_channels,
            4 * hidden_channels,
            kernel_size, padding=pad,
        )
        self.hidden_channels = hidden_channels

    def forward(self, x, h, c):
        # x: (B, C, H, W)   h, c: (B, hidden, H, W)
        """Advance the cell one step and return the new hidden and cell state."""
        combined = torch.cat([x, h], dim=1)
        gates    = self.gates(combined)
        i, f, g, o = gates.chunk(4, dim=1)
        i = torch.sigmoid(i)    # input gate  — how much new info enters
        f = torch.sigmoid(f)    # forget gate — how much past info survives
        g = torch.tanh(g)       # cell gate   — new candidate values
        o = torch.sigmoid(o)    # output gate — how much cell state to expose
        c = f * c + i * g
        h = o * torch.tanh(c)
        return h, c


class ConvLSTMForecaster(nn.Module):
    """ConvLSTM time-series forecaster for monthly NDVI maps (Ch10).

    Input:  (B, T, 1, H, W) — T monthly NDVI maps.
    Output: (B, 1, H, W)    — predicted next-month NDVI map.
    """
    def __init__(self, hidden_channels=16, kernel_size=3):
        """Build the ConvLSTM cell and the 1x1 output head."""
        super().__init__()
        self.cell   = ConvLSTMCell(1, hidden_channels, kernel_size)
        self.head   = nn.Conv2d(hidden_channels, 1, 1)   # 1×1 → NDVI
        self.hidden = hidden_channels

    def forward(self, x):
        """Roll the cell over all time steps and return the next-month map."""
        B, T, C, H, W = x.shape                      # (B, T, 1, H, W)
        h = torch.zeros(B, self.hidden, H, W, device=x.device)
        c = torch.zeros(B, self.hidden, H, W, device=x.device)
        for t in range(T):
            h, c = self.cell(x[:, t], h, c)
        return self.head(h)                          # (B, 1, H, W)


class CloudAutoencoder(nn.Module):
    """Convolutional autoencoder for cloud gap filling (Ch12).

    No skip connections — bottleneck must encode full scene context.
    BatchNorm after every Conv2d for stable training across patch content.
    Output in [0, 1] via Sigmoid — matches normalised reflectance.

    Args:
        in_channels:  number of input channels. Pass C + 1 to feed BGRN reflectance
                      plus an explicit binary mask channel (recommended — the model
                      knows where to fill rather than inferring it from spurious zeros).
        out_channels: number of output channels (typically C = 4 for BGRN). If None,
                      defaults to in_channels for backward compatibility with the
                      no-mask-channel setup.
    """
    def __init__(self, in_channels=4, out_channels=None):
        """Build the encoder and decoder for cloud gap filling."""
        super().__init__()
        if out_channels is None:
            out_channels = in_channels
        self.encoder = nn.Sequential(
            nn.Conv2d(in_channels, 32, 3, padding=1),
            nn.BatchNorm2d(32), nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64), nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1),
            nn.BatchNorm2d(128), nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.Conv2d(128, 64, 3, padding=1),
            nn.BatchNorm2d(64), nn.ReLU(),
            nn.Upsample(scale_factor=2, mode='bilinear', align_corners=False),
            nn.Conv2d(64, 32, 3, padding=1),
            nn.BatchNorm2d(32), nn.ReLU(),
            nn.Upsample(scale_factor=2, mode='bilinear', align_corners=False),
            nn.Conv2d(32, out_channels, 3, padding=1),
            # No BatchNorm before output — would distort final activation range
            nn.Sigmoid(),
        )

    def forward(self, x):
        """Encode then decode the input patch."""
        return self.decoder(self.encoder(x))


# ────────────────────────────────────────────────────────────────────────────
# ── DATASETS ──
# ────────────────────────────────────────────────────────────────────────────

class PatchDataset(Dataset):
    """Balanced patch sampler for segmentation training (Ch05).

    multiclass=True  → returns long labels for CrossEntropyLoss.
    multiclass=False → returns float labels with channel dim for BCELoss.
    """
    def __init__(self, image, labels, patch_size=64, n_patches=256,
                 pos_ratio=0.5, augment=False, seed=42, multiclass=False):
        """Sample balanced segmentation patches and store options."""
        self.patches, self.labels = extract_patches_balanced(
            image, labels, patch_size, n_patches, pos_ratio, seed)
        self.augment    = augment
        self.multiclass = multiclass

    def __len__(self):
        """Return the number of sampled patches."""
        return len(self.patches)

    def __getitem__(self, idx):
        """Return one optionally augmented (patch, label) tensor pair."""
        x = self.patches[idx].copy()
        y = self.labels[idx].copy()
        if self.augment:
            if random.random() > 0.5: x = np.flip(x, 2).copy(); y = np.flip(y, 1).copy()
            if random.random() > 0.5: x = np.flip(x, 1).copy(); y = np.flip(y, 0).copy()
            k = random.randint(0, 3)
            x = np.rot90(x, k, (1, 2)).copy()
            y = np.rot90(y, k).copy()
        xt = torch.from_numpy(x).float()
        yt = (torch.from_numpy(y.astype(np.int64)) if self.multiclass
              else torch.from_numpy(y.astype(np.float32)).unsqueeze(0))
        return xt, yt


class PatchClassDataset(Dataset):
    """Patch-level classification dataset; excludes uncertain (255) patches (Ch06).

    image:        (C, H, W) — full scene
    patch_labels: (H_p, W_p) — one integer class label per non-overlapping patch
    patch_size:   P — must match the grid used by majority_vote
    augment:      horizontal/vertical flip + 90-degree rotation
    """
    def __init__(self, image, patch_labels, patch_size=16,
                 augment=False, seed=42):
        """Collect per-patch samples, skipping uncertain (255) labels."""
        self.P       = patch_size
        self.augment = augment
        self.patches = []
        self.labels  = []
        H_p, W_p = patch_labels.shape
        for pr in range(H_p):
            for pc in range(W_p):
                lbl = patch_labels[pr, pc]
                if lbl == 255: continue
                r, c  = pr * patch_size, pc * patch_size
                patch = image[:, r:r+patch_size, c:c+patch_size]
                if patch.shape[1] < patch_size or patch.shape[2] < patch_size:
                    continue
                self.patches.append(patch)
                self.labels.append(int(lbl))
        random.seed(seed)

    def __len__(self):
        """Return the number of stored patches."""
        return len(self.patches)

    def __getitem__(self, idx):
        """Return one optionally augmented (patch, label) tensor pair."""
        x = self.patches[idx].copy()
        y = self.labels[idx]
        if self.augment:
            if random.random() > 0.5: x = np.flip(x, 2).copy()
            if random.random() > 0.5: x = np.flip(x, 1).copy()
            k = random.randint(0, 3)
            x = np.rot90(x, k, (1, 2)).copy()
        return torch.from_numpy(x).float(), torch.tensor(y, dtype=torch.long)


class CarPatchDataset(Dataset):
    """Wrap (patches, labels) arrays; augment randomly when training (Ch07)."""
    def __init__(self, patches, labels, augment=False):
        """Store the patch and label arrays and the augment flag."""
        self.patches = patches
        self.labels  = labels
        self.augment = augment

    def __len__(self):
        """Return the number of patches."""
        return len(self.patches)

    def __getitem__(self, idx):
        """Return one optionally augmented (patch, label) tensor pair."""
        x = self.patches[idx].copy()                # (3, 64, 64)
        y = self.labels[idx]
        if self.augment:
            if random.random() > 0.5:
                x = np.flip(x, 2).copy()             # horizontal flip
            if random.random() > 0.5:
                x = np.flip(x, 1).copy()             # vertical flip
            x = np.rot90(x, random.randint(0, 3), (1, 2)).copy()
        return torch.from_numpy(x).float(), torch.tensor(y, dtype=torch.long)


class HeightDataset(Dataset):
    """Non-overlapping grid patch dataset for height regression (Ch08).

    image:  (C, H, W) — Sentinel-2 scene
    target: (H, W)    — height map at the same resolution
    Each patch produces one sample: the patch array and the mean height of that
    patch as the regression target.
    """
    def __init__(self, image, target, patch_size=16, augment=False):
        """Tile the scene into grid patches with mean-height targets."""
        self.P       = patch_size
        self.augment = augment
        self.patches = []
        self.targets = []
        C, H, W = image.shape
        for r in range(0, H - patch_size + 1, patch_size):
            for c in range(0, W - patch_size + 1, patch_size):
                patch  = image[:, r:r + patch_size, c:c + patch_size]
                height = target[r:r + patch_size, c:c + patch_size].mean()
                self.patches.append(patch)
                self.targets.append(float(height))

    def __len__(self):
        """Return the number of patches."""
        return len(self.patches)

    def __getitem__(self, idx):
        """Return one optionally augmented (patch, height) tensor pair."""
        x = self.patches[idx].copy()
        y = self.targets[idx]
        if self.augment:
            if random.random() > 0.5: x = np.flip(x, 2).copy()
            if random.random() > 0.5: x = np.flip(x, 1).copy()
            x = np.rot90(x, random.randint(0, 3), (1, 2)).copy()
        x_t = torch.from_numpy(x).float()
        y_t = torch.tensor(y, dtype=torch.float32)
        return x_t, y_t


class ChangeDataset(Dataset):
    """Paired patch sampler for bi-temporal change detection (Ch09).

    Returns (t1_patch, t2_patch, label) triples; label is {0, 1, 255}.
    Samples positive/negative centres in the requested ratio, then crops
    patches around them with boundary clamping.
    """
    def __init__(self, t1, t2, labels, patch_size=64,
                 n_patches=1000, pos_ratio=0.5, augment=False, seed=42):
        """Sample paired bi-temporal patches around positive and negative centres."""
        rng = np.random.default_rng(seed)
        _, H, W = t1.shape; P = patch_size
        self.augment = augment; self.t1 = []; self.t2 = []; self.lbls = []
        pos_rc = np.argwhere(labels == 1)
        neg_rc = np.argwhere(labels == 0)
        n_pos  = int(n_patches * pos_ratio)
        n_neg  = n_patches - n_pos
        _sample = lambda a, n: (a[rng.choice(len(a), min(n, len(a)), replace=False)]
                                if len(a) else [])
        for centres, n in [(pos_rc, n_pos), (neg_rc, n_neg)]:
            for r, c in _sample(centres, n):
                r0 = max(0, min(r - P // 2, H - P))
                c0 = max(0, min(c - P // 2, W - P))
                self.t1.append(t1[:, r0:r0+P, c0:c0+P])
                self.t2.append(t2[:, r0:r0+P, c0:c0+P])
                self.lbls.append(labels[r0:r0+P, c0:c0+P])

    def __len__(self):
        """Return the number of patch pairs."""
        return len(self.t1)

    def __getitem__(self, idx):
        """Return one optionally augmented (t1, t2, label) triple."""
        x1 = self.t1[idx].copy()
        x2 = self.t2[idx].copy()
        y  = self.lbls[idx].copy()
        if self.augment:
            if random.random() > 0.5:
                x1 = np.flip(x1, 2).copy(); x2 = np.flip(x2, 2).copy()
                y  = np.flip(y, 1).copy()
            if random.random() > 0.5:
                x1 = np.flip(x1, 1).copy(); x2 = np.flip(x2, 1).copy()
                y  = np.flip(y, 0).copy()
            k  = random.randint(0, 3)
            x1 = np.rot90(x1, k, (1, 2)).copy()
            x2 = np.rot90(x2, k, (1, 2)).copy()
            y  = np.rot90(y,  k, (0, 1)).copy()
        return (torch.from_numpy(x1).float(),
                torch.from_numpy(x2).float(),
                torch.from_numpy(y.astype(np.int64)))


class NDVISequenceDataset(Dataset):
    """Spatial-temporal patch dataset for NDVI forecasting (Ch10, ConvLSTM).

    input_cube : (T, H, W) — NDVI for T months
    target_map : (H, W)    — NDVI for the target month
    Returns x of shape (T, 1, P, P) and y of shape (1, P, P).
    """
    def __init__(self, input_cube, target_map, patch_size=16,
                 n_patches=2000, augment=False, seed=42):
        """Sample spatial-temporal NDVI patch sequences and targets."""
        rng = np.random.default_rng(seed)
        T, H, W = input_cube.shape
        P = patch_size
        self.seqs, self.tgts = [], []
        self.augment = augment
        rows = rng.integers(0, H - P + 1, n_patches)
        cols = rng.integers(0, W - P + 1, n_patches)
        for r, c in zip(rows, cols):
            seq = input_cube[:, r:r+P, c:c+P]        # (T, P, P)
            tgt = target_map[   r:r+P, c:c+P]        # (P, P)
            self.seqs.append(seq[:, np.newaxis])     # (T, 1, P, P)
            self.tgts.append(tgt[np.newaxis])        # (1, P, P)

    def __len__(self):
        """Return the number of sequences."""
        return len(self.seqs)

    def __getitem__(self, idx):
        """Return one optionally augmented (sequence, target) tensor pair."""
        x = self.seqs[idx].copy()
        y = self.tgts[idx].copy()
        if self.augment:
            if random.random() > 0.5:
                x = np.flip(x, 3).copy()
                y = np.flip(y, 2).copy()
            if random.random() > 0.5:
                x = np.flip(x, 2).copy()
                y = np.flip(y, 1).copy()
        return (
            torch.from_numpy(x).float(),
            torch.from_numpy(y).float(),
        )


class ScalarSeqDataset(Dataset):
    """Scalar time-series dataset for the LSTM NDVI baseline (Ch10).

    x : (T, 1) — sequence of patch-mean NDVI values over T months
    y : scalar — patch-mean NDVI for the target month
    """
    def __init__(self, input_cube, target_map, patch_size=16,
                 n_patches=2000, seed=42):
        """Sample patch-mean NDVI scalar sequences and targets."""
        rng = np.random.default_rng(seed)
        T, H, W = input_cube.shape
        P = patch_size
        self.xs, self.ys = [], []
        rows = rng.integers(0, H - P + 1, n_patches)
        cols = rng.integers(0, W - P + 1, n_patches)
        for r, c in zip(rows, cols):
            seq = input_cube[:, r:r+P, c:c+P].mean(axis=(1, 2))   # (T,)
            tgt = float(target_map[r:r+P, c:c+P].mean())
            self.xs.append(seq)
            self.ys.append(tgt)

    def __len__(self):
        """Return the number of sequences."""
        return len(self.xs)

    def __getitem__(self, idx):
        """Return one (sequence, target) tensor pair."""
        x = torch.tensor(self.xs[idx], dtype=torch.float32).unsqueeze(-1)
        y = torch.tensor(self.ys[idx], dtype=torch.float32)
        return x, y


class InpaintDataset(Dataset):
    """Self-supervised inpainting dataset for the cloud autoencoder (Ch12).

    Each __getitem__ returns (masked_patch, original_patch, block_mask):
    a random rectangle covering 25–75% of the patch is zeroed and the model
    learns to reconstruct it from surrounding context.

    Args:
        image:       (C, H, W) source scene.
        patch_size:  side length of square patches.
        n_patches:   number of patches to sample.
        augment:     if True, apply random horizontal and vertical flips on __getitem__.
        seed:        RNG seed for reproducible patch positions and masks.
        cloud_mask:  optional (H, W) boolean array marking real cloud pixels in `image`.
                     If provided, any candidate patch whose footprint overlaps the cloud
                     is rejected and re-sampled, so the autoencoder is never trained
                     against real cloud reflectance in unmasked input. Set to None to
                     accept all patches (backward-compatible default).
    """
    def __init__(self, image, patch_size=384, n_patches=2000,
                 augment=False, seed=42, cloud_mask=None):
        """Sample patches, optionally rejecting any that overlap clouds."""
        rng      = np.random.default_rng(seed)       # reproducible patch positions
        C, H, W  = image.shape
        P        = patch_size
        self.patches = []
        self.augment = augment
        self.rng     = np.random.default_rng(seed + 1)   # separate rng for masks

        # Reject patches overlapping any cloud pixel; cap attempts to avoid loops.
        if cloud_mask is None:
            rows = rng.integers(0, H - P + 1, n_patches)
            cols = rng.integers(0, W - P + 1, n_patches)
            for r, c in zip(rows, cols):
                self.patches.append(image[:, r:r+P, c:c+P].copy())
        else:
            assert cloud_mask.shape == (H, W), (
                f'cloud_mask shape {cloud_mask.shape} does not match image {(H, W)}'
            )
            max_attempts = n_patches * 20
            attempts = 0
            while len(self.patches) < n_patches and attempts < max_attempts:
                r = int(rng.integers(0, H - P + 1))
                c = int(rng.integers(0, W - P + 1))
                attempts += 1
                if cloud_mask[r:r+P, c:c+P].any():
                    continue   # this patch contains real cloud reflectance — skip
                self.patches.append(image[:, r:r+P, c:c+P].copy())
            if len(self.patches) < n_patches:
                import warnings
                warnings.warn(
                    f'InpaintDataset: only {len(self.patches)}/{n_patches} cloud-free '
                    f'patches found after {attempts} attempts. Scene may be too cloudy '
                    'or patch_size too large for cloud_mask=True rejection.'
                )

    def __len__(self):
        """Return the number of patches."""
        return len(self.patches)

    def __getitem__(self, idx):
        """Return one (masked, original, mask) tensor triple."""
        orig = self.patches[idx].copy()
        if self.augment:
            if random.random() > 0.5: orig = np.flip(orig, 2).copy()   # horiz flip
            if random.random() > 0.5: orig = np.flip(orig, 1).copy()   # vert  flip
        P = orig.shape[1]

        # Block mask: random rectangle covering 25–75% of the patch area.
        bh = self.rng.integers(P // 4, int(P * 0.75))
        bw = self.rng.integers(P // 4, int(P * 0.75))
        r0 = self.rng.integers(0, P - bh)
        c0 = self.rng.integers(0, P - bw)
        mask = np.zeros((P, P), dtype=np.float32)
        mask[r0:r0+bh, c0:c0+bw] = 1.0

        masked = orig.copy()
        # zero the block — model fills from edges
        masked[:, mask == 1] = 0.0
        return (torch.from_numpy(masked).float(),
                torch.from_numpy(orig).float(),
                torch.from_numpy(mask).float())


# ────────────────────────────────────────────────────────────────────────────
# ── TRAINING ──
# ────────────────────────────────────────────────────────────────────────────

def bce_dice(pred, target, alpha=0.5):
    """Combined BCE + Dice loss for binary segmentation; pred must be raw logits.

    BCE term:  penalises wrong pixel probabilities (good for recall on rare positives).
    Dice term: optimises overlap ratio directly (good precision on small objects).
    alpha=0.5 weights both terms equally.
    """
    bce          = nn.BCEWithLogitsLoss()(pred, target)
    pred_sigmoid = torch.sigmoid(pred)
    inter        = (pred_sigmoid * target).sum(dim=(2, 3))
    denom        = pred_sigmoid.sum(dim=(2, 3)) + target.sum(dim=(2, 3)) + 1
    dice         = 1 - (2 * inter + 1) / denom
    return alpha * bce + (1 - alpha) * dice.mean()


def train_model(model, train_dl, val_dl, criterion, epochs=50, lr=1e-3,
                patience=8, save_path=None, multiclass=False, device=None):
    """Segmentation loop: Adam + ReduceLROnPlateau + early stop; tracks IoU.

    Returns history dict with keys 'tr' (train loss), 'va' (val loss), 'iou'.
    device defaults to get_device() when not supplied.
    """
    if device is None: device = get_device()
    opt   = optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    sched = optim.lr_scheduler.ReduceLROnPlateau(
        opt, patience=patience // 2, factor=0.5)
    best_val = float('inf'); wait = 0
    history  = {'tr': [], 'va': [], 'iou': []}

    for ep in range(1, epochs + 1):
        model.train(); tl = 0
        for xb, yb in train_dl:
            xb, yb = xb.to(device), yb.to(device)
            loss = criterion(model(xb), yb)
            opt.zero_grad(); loss.backward(); opt.step()
            tl += loss.item()

        model.eval(); vl = 0; vi = 0
        with torch.no_grad():
            for xb, yb in val_dl:
                xb, yb = xb.to(device), yb.to(device)
                pred = model(xb)
                vl  += criterion(pred, yb).item()
                if not multiclass: vi += iou_score(pred.cpu(), yb.cpu())

        tl /= len(train_dl); vl /= len(val_dl)
        if not multiclass: vi /= len(val_dl)
        history['tr'].append(tl); history['va'].append(vl); history['iou'].append(vi)
        sched.step(vl)

        if vl < best_val:
            best_val = vl; wait = 0
            if save_path: torch.save(model.state_dict(), save_path)
        else:
            wait += 1
            if wait >= patience: print(f'  Early stop ep {ep}'); break

        if ep % 5 == 0 or ep == 1:
            iou_str = f'  IoU {vi:.3f}' if not multiclass else ''
            print(f'  Ep {ep:3d} | tr {tl:.4f} | va {vl:.4f}{iou_str}')

    if save_path: model.load_state_dict(torch.load(save_path, map_location=device))
    return history


def train_classifier(model, train_dl, val_dl, epochs=30, lr=1e-3,
                     patience=8, save_path=None, class_weights=None, device=None):
    """Classification loop: CrossEntropyLoss + Adam + early stop; tracks accuracy.

    Returns history dict with keys 'tr' (train loss), 'va' (val loss), 'acc'.
    device defaults to get_device() when not supplied.
    """
    if device is None: device = get_device()
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    opt   = optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    sched = optim.lr_scheduler.ReduceLROnPlateau(
        opt, patience=patience // 2, factor=0.5)
    best_val = float('inf'); wait = 0
    history  = {'tr': [], 'va': [], 'acc': []}

    for ep in range(1, epochs + 1):
        model.train(); tl = 0
        for xb, yb in train_dl:
            xb, yb = xb.to(device), yb.to(device)
            loss = criterion(model(xb), yb)
            opt.zero_grad(); loss.backward(); opt.step()
            tl += loss.item()

        model.eval(); vl = 0; correct = 0; total = 0
        with torch.no_grad():
            for xb, yb in val_dl:
                xb, yb  = xb.to(device), yb.to(device)
                logits  = model(xb)
                vl     += criterion(logits, yb).item()
                preds   = logits.argmax(dim=1)
                correct += (preds == yb).sum().item()
                total   += yb.size(0)

        tl /= len(train_dl); vl /= len(val_dl)
        acc = correct / max(total, 1)
        history['tr'].append(tl); history['va'].append(vl); history['acc'].append(acc)
        sched.step(vl)

        if vl < best_val:
            best_val = vl; wait = 0
            if save_path: torch.save(model.state_dict(), save_path)
        else:
            wait += 1
            if wait >= patience: print(f'  Early stop ep {ep}'); break

        if ep % 5 == 0 or ep == 1:
            print(f'  Ep {ep:3d} | tr {tl:.4f} | va {vl:.4f} | acc {acc:.3f}')

    if save_path: model.load_state_dict(torch.load(save_path, map_location=device))
    return history


def train_regressor(model, train_dl, val_dl, epochs=100, lr=1e-3,
                    patience=20, save_path=None, device=None):
    """Regression training loop: MSELoss + Adam + early stopping; tracks MAE.

    Returns history dict with keys 'tr' (train loss), 'va' (val loss), 'mae'.
    Portable signature matching train_model / train_classifier. device defaults
    to get_device() when not supplied.
    """
    if device is None: device = get_device()
    criterion = nn.MSELoss()
    opt   = optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    sched = optim.lr_scheduler.ReduceLROnPlateau(opt, patience=5, factor=0.5)
    best_val = float('inf'); wait = 0
    history  = {'tr': [], 'va': [], 'mae': []}

    for ep in range(1, epochs + 1):
        model.train(); tl = 0
        for xb, yb in train_dl:
            xb, yb = xb.to(device), yb.to(device)
            loss = criterion(model(xb), yb)
            opt.zero_grad(); loss.backward(); opt.step()
            tl += loss.item()

        model.eval(); vl = 0; mae_sum = 0; n_pts = 0
        with torch.no_grad():
            for xb, yb in val_dl:
                xb, yb = xb.to(device), yb.to(device)
                preds  = model(xb)
                vl    += criterion(preds, yb).item()
                mae_sum += (preds - yb).abs().sum().item()
                n_pts   += len(yb)

        tl /= len(train_dl); vl /= len(val_dl)
        mae_val = mae_sum / max(n_pts, 1)
        history['tr'].append(tl); history['va'].append(vl)
        history['mae'].append(mae_val)
        sched.step(vl)

        if vl < best_val:
            best_val = vl; wait = 0
            if save_path: torch.save(model.state_dict(), save_path)
        else:
            wait += 1
            if wait >= patience: print(f'  Early stop ep {ep}'); break

        if ep % 10 == 0 or ep == 1:
            print(f'  Ep {ep:3d} | tr {tl:.4f} | va {vl:.4f} | mae {mae_val:.2f}')

    if save_path: model.load_state_dict(torch.load(save_path, map_location=device))
    return history


def plot_history(history, title, metric='iou'):
    """Two-panel training curve: loss (left) and secondary metric (right).

    Metric keys: 'iou' (Ch05), 'acc' (Ch06/Ch07/Ch09),
    'mae' (Ch08/Ch10/Ch12).
    If the metric key is absent or all zeros the right panel shows a placeholder.
    """
    fig, axes = plt.subplots(1, 2, figsize=(10, 3))
    ep = range(1, len(history['tr']) + 1)
    axes[0].plot(ep, history['tr'], label='Train')
    axes[0].plot(ep, history['va'], label='Val')
    axes[0].set_xlabel('Epoch'); axes[0].set_ylabel('Loss')
    axes[0].legend(); axes[0].grid(alpha=0.3)
    if metric in history and any(v > 0 for v in history[metric]):
        colour = 'green' if metric == 'iou' else 'steelblue'
        axes[1].plot(ep, history[metric], color=colour)
        metric_labels = {'iou': 'Val IoU', 'acc': 'Val Accuracy', 'mae': 'Val MAE'}
        axes[1].set_ylabel(metric_labels.get(metric, metric))
        if metric in ('iou', 'acc'):
            axes[1].set_ylim(0, 1)
    else:
        axes[1].text(0.5, 0.5, f'{metric} not tracked',
                     ha='center', va='center', transform=axes[1].transAxes)
    axes[1].set_xlabel('Epoch'); axes[1].grid(alpha=0.3)
    plt.suptitle(title, fontweight='bold')
    plt.tight_layout(); plt.show()


# ────────────────────────────────────────────────────────────────────────────
# ── EVALUATION ──
# ────────────────────────────────────────────────────────────────────────────

def iou_score(pred, target, threshold=0.5):
    """IoU for binary segmentation; applies sigmoid to raw logits."""
    pred_prob = torch.sigmoid(pred)
    p = (pred_prob > threshold).float()
    i = (p * target).sum()
    u = p.sum() + target.sum() - i
    return (i / (u + 1e-6)).item()


def evaluate_segmentation(pred_map, te_lbl, class_names):
    """Per-class IoU on the test split; excludes uncertain pixels (255)."""
    pred = pred_map.flatten(); true = te_lbl.flatten()
    mask = true != 255
    pred = pred[mask]; true = true[mask]
    results = {}
    print('  Per-class IoU:')
    for cls, name in enumerate(class_names):
        tp  = ((pred == cls) & (true == cls)).sum()
        fp  = ((pred == cls) & (true != cls)).sum()
        fn  = ((pred != cls) & (true == cls)).sum()
        iou = float(tp / (tp + fp + fn + 1e-6))
        results[name] = iou
        print(f'    {name:<12} IoU: {iou:.3f}')
    print(f'    {"Mean":<12}     {np.mean(list(results.values())):.3f}')
    return results


def compute_class_weights(labels, n_classes, device):
    """Inverse-frequency class weighting normalised to sum to 1.0.

    Rare classes receive higher weight to prevent the model from ignoring them.
    Uncertain pixels (255) are excluded from the count.
    """
    counts = np.array(
        [(labels[labels != 255] == c).sum() for c in range(n_classes)],
        dtype=np.float32)
    w = 1.0 / (counts + 1e-6)
    return torch.tensor(w / w.sum()).to(device)


def compute_ap(det_boxes, det_scores, gt_boxes, iou_threshold=0.3):
    """Average Precision at a given IoU threshold for object detection (Ch07).

    Self-contained: inlines bounding-box IoU so utils has no naming overlap
    with iou_score (segmentation IoU).
    Returns (precision array, recall array, AP scalar).
    """
    if len(det_boxes) == 0:
        return np.array([1.0]), np.array([0.0]), 0.0

    def _bbox_iou(b1, b2):
        """Return the IoU of two (x1, y1, x2, y2) boxes."""
        xi1 = max(b1[0], b2[0]); yi1 = max(b1[1], b2[1])
        xi2 = min(b1[2], b2[2]); yi2 = min(b1[3], b2[3])
        inter = max(0, xi2 - xi1) * max(0, yi2 - yi1)
        area1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
        area2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
        return inter / (area1 + area2 - inter + 1e-6)

    order      = np.argsort(det_scores)[::-1]
    det_boxes  = det_boxes[order]
    det_scores = det_scores[order]

    n_gt       = len(gt_boxes)
    gt_matched = np.zeros(n_gt, dtype=bool)
    tp = np.zeros(len(det_boxes))
    fp = np.zeros(len(det_boxes))

    for i, db in enumerate(det_boxes):
        best_iou = 0.0; best_j = -1
        for j, gb in enumerate(gt_boxes):
            if gt_matched[j]: continue
            score = _bbox_iou(db, gb)
            if score > best_iou:
                best_iou = score; best_j = j
        if best_iou >= iou_threshold and best_j >= 0:
            tp[i] = 1
            gt_matched[best_j] = True
        else:
            fp[i] = 1

    cum_tp = np.cumsum(tp); cum_fp = np.cumsum(fp)
    rec    = cum_tp / (n_gt + 1e-6)
    prec   = cum_tp / (cum_tp + cum_fp + 1e-6)
    rec_full  = np.concatenate([[0], rec,  [rec[-1]]])
    prec_full = np.concatenate([[1], prec, [0]])

    # NumPy 2.0+ renamed trapz → trapezoid; remain compatible with 1.x
    try:
        ap = np.trapezoid(prec_full, rec_full)
    except AttributeError:
        ap = np.trapz(prec_full, rec_full)

    return prec, rec, ap


# ────────────────────────────────────────────────────────────────────────────
# ── SPATIAL UTILITIES ──
# ────────────────────────────────────────────────────────────────────────────

def spatial_split_lr(image, labels=None, split_col=None, buffer_px=0):
    """Left/right geographic split with optional buffer to prevent spatial leakage.

    Superset signature used across chapters:
      - Ch05/Ch06/Ch08: pass labels and split_col positionally.
      - Ch12: pass labels=None for unsupervised tasks (cloud autoencoder).
      - split_col defaults to image midpoint when not supplied.

    Returns:
      (tr_img, tr_lbl, te_img, te_lbl)  when labels is not None
      (tr_img, te_img)                   when labels is None
    """
    if split_col is None:
        split_col = image.shape[2] // 2
    tr_img = image[:, :, :split_col - buffer_px]
    te_img = image[:, :,  split_col + buffer_px:]
    if labels is not None:
        tr_lbl = labels[:,    :split_col - buffer_px]
        te_lbl = labels[:,     split_col + buffer_px:]
        return tr_img, tr_lbl, te_img, te_lbl
    return tr_img, te_img


def stretch(b, plo=2, phi=98):
    """Percentile contrast stretch for display; returns float array in [0, 1]."""
    vals = b[b > 0]
    if len(vals) == 0: return np.zeros_like(b)       # guard: all-zero band
    lo, hi = np.percentile(vals, [plo, phi])
    return np.clip((b - lo) / (hi - lo + 1e-6), 0, 1)


def extract_patches_balanced(image, labels, patch_size, n_patches,
                              pos_ratio=0.5, seed=42):
    """Sample patches with a guaranteed foreground fraction.

    Uncertain pixels marked 255 are excluded from foreground detection.
    For a 4000×4000 image with patch_size=128 this can take 30–60 s — run once
    and reuse (PatchDataset calls it internally in __init__).
    """
    rng = np.random.default_rng(seed)
    C, H, W = image.shape; P = patch_size
    pos, neg = [], []
    for r in range(H - P + 1):
        for c in range(W - P + 1):
            patch_lbl = labels[r:r+P, c:c+P]
            valid = patch_lbl[patch_lbl != 255]
            if len(valid) == 0: continue
            (pos if valid.max() > 0 else neg).append((r, c))
    if len(pos) == 0:
        chosen = [neg[i] for i in rng.integers(0, len(neg), n_patches)]
    elif len(neg) == 0:
        chosen = [pos[i] for i in rng.integers(0, len(pos), n_patches)]
    else:
        n_pos = int(n_patches * pos_ratio); n_neg = n_patches - n_pos
        chosen = ([pos[i] for i in rng.integers(0, len(pos), n_pos)] +
                  [neg[i] for i in rng.integers(0, len(neg), n_neg)])
    patches = [image[:, r:r+P, c:c+P] for r, c in chosen]
    lbls    = [labels[r:r+P, c:c+P]   for r, c in chosen]
    return np.array(patches), np.array(lbls)


def sliding_window_inference(model, image, patch_size, stride, device,
                             n_classes=1):
    """Run model over a full scene with overlapping patches; average predictions.

    Averaging across overlapping windows removes tile-boundary artefacts.
    n_classes=1: returns (H, W) float probability map (sigmoid applied).
    n_classes>1: returns (n_classes, H, W) raw logit map (no softmax).
    """
    model.eval(); C, H, W = image.shape; P = patch_size
    out = np.zeros((H, W) if n_classes == 1 else (n_classes, H, W), dtype=np.float32)
    cnt = np.zeros((H, W), dtype=np.float32)
    with torch.no_grad():
        for r in range(0, H - P + 1, stride):
            for c in range(0, W - P + 1, stride):
                patch = image[:, r:r+P, c:c+P]
                t    = torch.from_numpy(patch).float().unsqueeze(0).to(device)
                pred = model(t).squeeze(0).cpu()
                if n_classes == 1:
                    pred = torch.sigmoid(pred)
                    out[r:r+P, c:c+P]  += pred.squeeze().numpy()
                else:
                    out[:, r:r+P, c:c+P] += pred.numpy()
                cnt[r:r+P, c:c+P] += 1
    denom = np.maximum(cnt, 1)
    return out / denom if n_classes == 1 else out / denom[np.newaxis]


def predict_full_scene(model, image, patch_size, device):
    """Tile scene with non-overlapping patches and assemble a full-scene map (Ch08).

    Returns a map of shape (H, W) — same spatial extent as image. One scalar
    per patch is broadcast to the patch area. Edge pixels not covered by a
    complete patch remain zero.
    """
    model.eval()
    H, W     = image.shape[1], image.shape[2]
    pred_map = np.zeros((H, W), dtype=np.float32)
    with torch.no_grad():
        for r in range(0, H - patch_size + 1, patch_size):
            for c in range(0, W - patch_size + 1, patch_size):
                patch   = image[:, r:r + patch_size, c:c + patch_size]
                patch_t = torch.from_numpy(patch).float().unsqueeze(0).to(device)
                value   = model(patch_t).item()
                pred_map[r:r + patch_size, c:c + patch_size] = value
    return pred_map


def sliding_window_detect(model, image, patch_size, stride,
                          conf_threshold, device):
    """Slide a binary patch classifier over an image in a dense grid (Ch07).

    Returns (boxes, scores) — boxes in (x1, y1, x2, y2) pixel coordinates.
    One forward pass per grid position — O(H×W/stride²) GPU calls. Pair with
    NMS to deduplicate overlapping detections.
    """
    model.eval()
    C, H, W = image.shape
    P = patch_size
    boxes, scores = [], []

    with torch.no_grad():
        for r in range(0, H - P + 1, stride):
            for c in range(0, W - P + 1, stride):
                patch = image[:, r:r+P, c:c+P]       # (3, P, P)
                x     = torch.from_numpy(patch).float()
                x     = x.unsqueeze(0).to(device)    # (1, 3, P, P)
                logit = model(x).squeeze(0).cpu()    # scalar
                prob  = torch.sigmoid(logit).item()
                if prob >= conf_threshold:
                    boxes.append([c, r, c + P, r + P])
                    scores.append(prob)

    return np.array(boxes, dtype=np.float32), np.array(scores)


def majority_vote(pixel_labels, patch_size, majority_thresh=0.7, n_classes=3):
    """Convert a pixel-level label map to patch-level labels (Ch06).

    Returns an (H_patches, W_patches) uint8 array. Patches below the majority
    threshold (or fully 255) receive label 255 and are excluded downstream.
    """
    H, W = pixel_labels.shape
    P    = patch_size
    H_p  = H // P
    W_p  = W // P
    patch_labels = np.full((H_p, W_p), 255, dtype=np.uint8)
    for pr in range(H_p):
        for pc in range(W_p):
            block = pixel_labels[pr*P:(pr+1)*P, pc*P:(pc+1)*P]
            valid = block[block != 255]
            if len(valid) == 0:
                continue
            for cls in range(n_classes):
                if (valid == cls).sum() / len(valid) >= majority_thresh:
                    patch_labels[pr, pc] = cls
                    break
    return patch_labels


# ────────────────────────────────────────────────────────────────────────────
# ── ANNOTATION ──
# ────────────────────────────────────────────────────────────────────────────

class BBoxAnnotator:
    """Interactive bounding box annotation tool for object detection (Ch07).

    Launches a matplotlib window for annotating car and not-car boxes on an
    aerial image tile. Saves annotations in YOLO format.

    Controls:
        Drag  — draw a box in the current class mode
        c     — switch to car mode   (lime boxes)
        n     — switch to not-car mode (red boxes)
        u     — undo the last box
        d     — done: save and close

    Outputs:
        <save_dir>/cars.txt     — car annotations in YOLO format
        <save_dir>/not_cars.txt — not-car annotations in YOLO format

    Note: requires an interactive matplotlib backend (e.g. TkAgg).
    Do NOT use in non-interactive environments (Colab, JupyterLab server).
    """

    def __init__(self, image_rgb, save_dir, img_w, img_h):
        """Open the annotation figure and wire up the event handlers."""
        self.save_dir  = Path(save_dir)
        self.img_w     = img_w
        self.img_h     = img_h
        self.boxes     = []   # list of (x1, y1, x2, y2, class_id)
        self.mode      = 0    # 0 = car, 1 = not-car
        self._drawing  = False
        self._x0 = self._y0 = 0
        self._rect = None

        self.fig, self.ax = plt.subplots(figsize=(12, 12))
        self.ax.imshow(image_rgb)
        self.ax.axis('off')
        self._update_title()

        self.fig.canvas.mpl_connect('button_press_event',   self._on_press)
        self.fig.canvas.mpl_connect('button_release_event', self._on_release)
        self.fig.canvas.mpl_connect('motion_notify_event',  self._on_motion)
        self.fig.canvas.mpl_connect('key_press_event',      self._on_key)

        plt.tight_layout()
        plt.show(block=True)

    def _mode_color(self, mode=None):
        """Return the box colour for the given (or current) class mode."""
        return 'lime' if (mode if mode is not None else self.mode) == 0 else 'tomato'

    def _mode_name(self, mode=None):
        """Return the class name for the given (or current) mode."""
        return 'car' if (mode if mode is not None else self.mode) == 0 else 'not-car'

    def _update_title(self):
        """Refresh the title with the current mode and box counts."""
        n_car    = sum(1 for b in self.boxes if b[4] == 0)
        n_notcar = sum(1 for b in self.boxes if b[4] == 1)
        self.ax.set_title(
            f'Mode: [{self._mode_name()}]  |  '
            f'car: {n_car}  not-car: {n_notcar}  |  '
            f'c=car  n=not-car  u=undo  d=done & save',
            fontweight='bold', fontsize=10,
            color=self._mode_color())
        self.fig.canvas.draw_idle()

    def _on_press(self, event):
        """Begin drawing a box on left-button press inside the axes."""
        if event.inaxes and event.button == 1:
            self._drawing = True
            self._x0, self._y0 = event.xdata, event.ydata
            self._rect = mpatches.Rectangle(
                (self._x0, self._y0), 0, 0,
                edgecolor='yellow', facecolor='none', lw=1.5)
            self.ax.add_patch(self._rect)

    def _on_motion(self, event):
        """Resize the in-progress box as the cursor moves."""
        if self._drawing and event.inaxes and self._rect:
            self._rect.set_width(event.xdata  - self._x0)
            self._rect.set_height(event.ydata - self._y0)
            self.fig.canvas.draw_idle()

    def _on_release(self, event):
        """Finalise and store the drawn box on button release."""
        if self._drawing and event.inaxes and event.button == 1:
            self._drawing = False
            x1 = int(min(self._x0, event.xdata))
            y1 = int(min(self._y0, event.ydata))
            x2 = int(max(self._x0, event.xdata))
            y2 = int(max(self._y0, event.ydata))
            if self._rect:
                self._rect.remove()
            self._rect = None
            if x2 - x1 > 5 and y2 - y1 > 5:
                self.boxes.append((x1, y1, x2, y2, self.mode))
                self.ax.add_patch(mpatches.Rectangle(
                    (x1, y1), x2 - x1, y2 - y1,
                    edgecolor=self._mode_color(), facecolor='none', lw=1.5))
                self._update_title()
                print(f'  [{self._mode_name()}] box {len(self.boxes):3d}: '
                      f'({x1},{y1}) -> ({x2},{y2})')

    def _on_key(self, event):
        """Handle mode-switch, undo, and save key presses."""
        if event.key == 'c':
            self.mode = 0
            self._update_title()
        elif event.key == 'n':
            self.mode = 1
            self._update_title()
        elif event.key == 'u' and self.boxes:
            removed = self.boxes.pop()
            for patch in list(self.ax.patches):
                patch.remove()
            for (x1, y1, x2, y2, cls) in self.boxes:
                self.ax.add_patch(mpatches.Rectangle(
                    (x1, y1), x2 - x1, y2 - y1,
                    edgecolor=self._mode_color(cls), facecolor='none', lw=1.5))
            self._update_title()
            print(f'  Undo: removed [{self._mode_name(removed[4])}] {removed[:4]}')
        elif event.key == 'd':
            self._save()
            plt.close(self.fig)

    def _save(self):
        """Write car and not-car boxes to YOLO-format files."""
        self.save_dir.mkdir(exist_ok=True)
        car_path     = self.save_dir / 'cars.txt'
        not_car_path = self.save_dir / 'not_cars.txt'

        with open(car_path, 'w') as fc, open(not_car_path, 'w') as fn:
            for (x1, y1, x2, y2, cls) in self.boxes:
                cx   = ((x1 + x2) / 2) / self.img_w
                cy   = ((y1 + y2) / 2) / self.img_h
                w    = (x2 - x1) / self.img_w
                h    = (y2 - y1) / self.img_h
                line = f'0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n'
                (fc if cls == 0 else fn).write(line)

        n_car    = sum(1 for b in self.boxes if b[4] == 0)
        n_notcar = sum(1 for b in self.boxes if b[4] == 1)
        print(f'\nSaved {n_car} car boxes     -> {car_path}')
        print(f'Saved {n_notcar} not-car boxes -> {not_car_path}')


# ────────────────────────────────────────────────────────────────────────────
# ── SENTINEL-2 HELPERS ──
# ────────────────────────────────────────────────────────────────────────────
# STAC search, grid-aware caching, per-month download, and time-series grid
# assertions for Ch4 Steps 30 + 31. Chapter-local catalog, bbox, and spectral
# helpers are passed in as explicit args to keep the module chapter-independent.

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling, transform_geom
from rasterio.transform import Affine
from rasterio.mask import mask as rio_mask


# SCL class codes flagged as invalid for the local valid-pixel check.
# 0 = NO_DATA, 3 = CLOUD_SHADOW, 8 = CLOUD_MEDIUM, 9 = CLOUD_HIGH, 10 = THIN_CIRRUS
SCL_INVALID = {0, 3, 8, 9, 10}


def search_best_any(catalog, bbox, date_range, max_cloud=30,
                    stac_pin=None, region_key=None,
                    fetch_item_fn=None):
    """Return Sentinel-2 L2A candidates for a date range, sorted by cloud cover.

    Honours `stac_pin[(region_key, date_range)]` if set — fetches by ID for
    reproducibility. Otherwise hits the live STAC search and sorts results
    by (cloud cover, item id) so re-runs pick the same scene among ties.
    """
    if stac_pin is not None and region_key is not None:
        pin = stac_pin.get((region_key, date_range))
        if pin is not None and fetch_item_fn is not None:
            return [fetch_item_fn(pin)]
    results = catalog.search(
        collections=['sentinel-2-l2a'],
        bbox=bbox,
        datetime=date_range,
        query={'eo:cloud_cover': {'lt': max_cloud}},
    )
    items = list(results.items())
    if not items:
        raise ValueError(f'No scenes under {max_cloud}% cloud for {date_range}')
    return sorted(items, key=lambda x: (x.properties['eo:cloud_cover'], x.id))


def search_matched_reference(catalog, bbox, reference_item, date_range,
                             max_cloud=30,
                             stac_pin=None, region_key=None,
                             fetch_item_fn=None):
    """Return the least-cloudy Sentinel-2 scene on the SAME MGRS tile as
    `reference_item` over `date_range`.

    Used to build a pixel-aligned external-validation pair: when the
    reference scene (typically a partially cloudy one) sits on one
    orbital track, the matched-reference scene (typically clear, same
    season) must come from the same MGRS tile so the two share a
    native grid. Without the tile constraint, scenes from adjacent
    orbital tracks land on different UTM origins (~1.1 km y-offset is
    typical), defeating any pixel-level validation downstream.

    Resolution order:
      1. If `stac_pin[(region_key, date_range)]` is set, fetch by ID.
      2. Else, STAC search with bbox + cloud filter + tile constraint;
         pick the lowest-cloud candidate with `(cloud, id)` tie-break.
      3. If no tile-matched candidate exists, fall back to ANY tile
         (warns, since downstream warping will then be required).

    Args:
        catalog: pystac_client.Client (already opened).
        bbox: [W, S, E, N] bounding box for the search.
        reference_item: STAC Item whose MGRS tile we must match.
        date_range: 'YYYY-MM-DD/YYYY-MM-DD' string.
        max_cloud: max scene-level cloud cover for candidates.
        stac_pin, region_key, fetch_item_fn: optional reproducibility hooks
            mirroring `search_best_any`.

    Returns the matched STAC Item.
    """
    if stac_pin is not None and region_key is not None:
        pin = stac_pin.get((region_key, date_range))
        if pin is not None and fetch_item_fn is not None:
            item = fetch_item_fn(pin)
            print(f'  {date_range}: {item.datetime.date()}  '
                  f'cloud={item.properties["eo:cloud_cover"]:.1f}%  [pinned]')
            return item

    ref_tile = (reference_item.properties.get('grid:code') or
                reference_item.properties.get('s2:mgrs_tile'))
    if ref_tile is None:
        raise ValueError(
            'reference_item has no MGRS tile in grid:code or s2:mgrs_tile — '
            'cannot constrain search to a matching tile.'
        )

    results = catalog.search(
        collections=['sentinel-2-l2a'],
        bbox=bbox,
        datetime=date_range,
        query={
            'eo:cloud_cover': {'lt': max_cloud},
            'grid:code':      {'eq': ref_tile},
        },
    )
    items = list(results.items())

    if not items:
        print(f'  ⚠ no {date_range} scene under {max_cloud}% cloud on tile '
              f'{ref_tile} — falling back to any tile (downstream warping '
              f'may be needed).')
        results = catalog.search(
            collections=['sentinel-2-l2a'],
            bbox=bbox,
            datetime=date_range,
            query={'eo:cloud_cover': {'lt': max_cloud}},
        )
        items = list(results.items())
        if not items:
            raise ValueError(
                f'No scenes under {max_cloud}% cloud for {date_range} '
                f'on any tile.'
            )

    best = min(items, key=lambda x: (x.properties['eo:cloud_cover'], x.id))
    cloud = best.properties['eo:cloud_cover']
    best_tile = (best.properties.get('grid:code') or
                 best.properties.get('s2:mgrs_tile', '?'))
    matched = '' if best_tile != ref_tile else ' (tile-matched)'
    print(f'  {date_range}: {best.datetime.date()}  cloud={cloud:.1f}%  '
          f'tile={best_tile}{matched}')
    print(f"    → pin: STAC_PIN[({region_key!r}, {date_range!r})] = {best.id!r}")
    return best


def file_grid_key(path):
    """Return (epsg, tl_x, tl_y, count, h, w) for a saved GeoTIFF, or None.

    Used to compare grids between monthly time-series files. Equal shape
    alone is not enough to prove co-registration — two scenes from different
    orbital tracks can land on identically-sized rasters whose top-left
    corners are offset by up to half a pixel.
    """
    try:
        with rasterio.open(path) as src:
            tf = src.transform
            return (
                src.crs.to_epsg() if src.crs else None,
                round(tf.c, 1), round(tf.f, 1),
                src.count, src.height, src.width,
            )
    except Exception:
        return None


def cache_is_valid(path, ref_grid=None, ref_count=5):
    """A cached monthly file passes if its band count is right AND (if
    ref_grid is given) its grid matches the reference exactly.

    The grid check exists to invalidate files written under an earlier
    alignment strategy — those legacy files have the right shape but a
    different top-left origin from the dominant orbital track.
    """
    if not path.exists():
        return False
    grid = file_grid_key(path)
    if grid is None or grid[3] != ref_count:
        return False
    if ref_grid is not None:
        if grid[0] != ref_grid[0]:
            return False
        if grid[1:] != ref_grid[1:]:
            return False
    return True


def _reproject_to_ref(s5, item, ref_grid, geom):
    """Reproject a (5, H, W) reflectance+NDVI stack onto ref_grid.

    Bilinear resampling for all 5 channels — the pre-computed NDVI band is
    continuous, so bilinear is the correct choice.
    """
    ref_epsg, ref_tlx, ref_tly, _, ref_h, ref_w = ref_grid
    ref_crs = rasterio.crs.CRS.from_epsg(ref_epsg)
    ref_tf  = Affine(10.0, 0.0, ref_tlx, 0.0, -10.0, ref_tly)

    with rasterio.open(item.assets['red'].href) as ref_src:
        geom_native = transform_geom('EPSG:4326', ref_src.crs, geom[0])
        _, src_tf   = rio_mask(ref_src, [geom_native], crop=True)
        src_crs     = ref_src.crs

    out = np.zeros((s5.shape[0], ref_h, ref_w), dtype=np.float32)
    for b in range(s5.shape[0]):
        reproject(
            source=s5[b],
            destination=out[b],
            src_transform=src_tf, src_crs=src_crs,
            dst_transform=ref_tf, dst_crs=ref_crs,
            resampling=Resampling.bilinear,
            src_nodata=np.nan, dst_nodata=np.nan,
        )
    return out


def download_month(label, date_range, cache_path,
                   *, catalog, bbox, geom, h_ref, w_ref,
                   to_reflectance_fn, ndvi_fn, download_item_fn,
                   save_geotiff_fn, ref_grid=None,
                   stac_pin=None, fetch_item_fn=None,
                   region_key='hungary_ts', min_valid_frac=0.90):
    """Download the best available Sentinel-2 scene for one calendar month.

    Returns (s5, item) on success, (None, None) if no usable scene exists.

    Quality gates:
      1. Footprint covers at least 95% of the reference spatial extent.
      2. Local SCL valid-pixel fraction over the crop must be at least
         `min_valid_frac` (default 0.90).
      3. If `ref_grid` is supplied AND the candidate's native grid doesn't
         match, the 5-channel stack is reprojected (bilinear) onto ref_grid
         before saving.

    Side effects: writes the accepted scene to `cache_path` as a 5-band
    GeoTIFF (BGRN + NDVI). Skips the download if the cache passes
    `cache_is_valid(cache_path, ref_grid)`.
    """
    if cache_is_valid(cache_path, ref_grid=ref_grid):
        with rasterio.open(cache_path) as src:
            s5 = src.read().astype(np.float32)
        print(f'  {label}: cache  NDVI mean={np.nanmean(s5[4]):.3f}')
        return s5, None

    candidates = search_best_any(
        catalog, bbox, date_range,
        stac_pin=stac_pin, region_key=region_key,
        fetch_item_fn=fetch_item_fn,
    )
    for item in candidates:
        raw, scl = download_item_fn(item, with_scl=True)
        if raw.shape[1] < h_ref * 0.95 or raw.shape[2] < w_ref * 0.95:
            continue
        invalid    = np.isin(scl, list(SCL_INVALID))
        valid_frac = 1.0 - invalid.mean()
        if valid_frac < min_valid_frac:
            print(f'  {label}: skip  valid_frac={valid_frac:.2%}  '
                  f'(SCL cloud/shadow/nodata over crop)')
            continue
        s    = to_reflectance_fn(raw, item=item)
        nv   = ndvi_fn(s)
        s5   = np.concatenate([s, nv[np.newaxis]], axis=0)

        if ref_grid is not None:
            with rasterio.open(item.assets['red'].href) as red:
                geom_native  = transform_geom('EPSG:4326', red.crs, geom[0])
                _, native_tf = rio_mask(red, [geom_native], crop=True)
                native_epsg  = red.crs.to_epsg()
            native_origin = (round(native_tf.c, 1), round(native_tf.f, 1))
            ref_origin    = (ref_grid[1], ref_grid[2])
            if native_epsg != ref_grid[0] or native_origin != ref_origin:
                s5 = _reproject_to_ref(s5, item, ref_grid, geom)
                print(f'  {label}: reprojected onto reference grid '
                      f'(native origin {native_origin} → ref {ref_origin})')

        if ref_grid is not None:
            tf  = Affine(10.0, 0.0, ref_grid[1], 0.0, -10.0, ref_grid[2])
            crs = rasterio.crs.CRS.from_epsg(ref_grid[0])
            C_, H_, W_ = s5.shape
            with rasterio.open(
                cache_path, 'w',
                driver='GTiff', height=H_, width=W_,
                count=C_, dtype='float32',
                crs=crs, transform=tf, nodata=np.nan,
            ) as dst:
                dst.write(s5)
            print(f'Saved: {cache_path.name}  {s5.shape}  '
                  f'{cache_path.stat().st_size / 1e6:.1f} MB')
        else:
            save_geotiff_fn(s5, cache_path, item, nodata=np.nan)

        cloud = item.properties['eo:cloud_cover']
        print(f'  {label}: NDVI={np.nanmean(s5[4]):.3f}  '
              f'cloud={cloud:.1f}%  valid_frac={valid_frac:.2%}')
        print(f"    → pin: STAC_PIN[({region_key!r}, {date_range!r})]"
              f' = {item.id!r}')
        return s5, item
    return None, None


def assert_monthly_grids_match(month_labels, data_dir, filename_pattern):
    """Assert every monthly file shares (CRS, top-left, shape) and clip
    each file to the common valid (non-NaN) extent across all months.

    Returns the shared grid tuple and the (r0, r1, c0, c1) crop window.
    Raises AssertionError on grid mismatch or empty valid extent.
    """
    grids = {}
    arrays = {}
    paths = {}
    for entry in month_labels:
        label = entry[0] if isinstance(entry, tuple) else entry
        cache_path = data_dir / filename_pattern.format(label=label.lower())
        if not cache_path.exists():
            continue
        with rasterio.open(cache_path) as src:
            tf = src.transform
            grids[label] = (
                src.crs.to_epsg(),
                round(tf.c, 1), round(tf.f, 1),
                src.count, src.height, src.width,
            )
            arrays[label] = src.read().astype(np.float32)
            paths[label] = (cache_path, src.crs, tf)

    unique = set(grids.values())
    assert len(unique) == 1, (
        f'Monthly files have mismatched grids (CRS / origin / shape): {grids}'
    )

    # Find common valid extent — intersection of non-NaN pixels across all months
    stack = np.stack([arrays[k] for k in arrays], axis=0)  # (T, C, H, W)
    valid_mask = np.all(~np.isnan(stack[:, 0, :, :]), axis=0)  # (H, W)
    assert valid_mask.any(), 'No pixel is valid across all 12 months.'
    rows_valid = np.where(valid_mask.any(axis=1))[0]
    cols_valid = np.where(valid_mask.any(axis=0))[0]
    r0, r1 = int(rows_valid[0]), int(rows_valid[-1]) + 1
    c0, c1 = int(cols_valid[0]), int(cols_valid[-1]) + 1

    # Overwrite each file clipped to the common valid window
    for label, (cache_path, crs, tf) in paths.items():
        clipped = arrays[label][:, r0:r1, c0:c1]
        from rasterio.transform import from_origin
        new_tf = rasterio.transform.from_bounds(
            tf.c + c0 * tf.a,
            tf.f + r1 * tf.e,
            tf.c + c1 * tf.a,
            tf.f + r0 * tf.e,
            c1 - c0, r1 - r0,
        )
        C, H, W = clipped.shape
        with rasterio.open(
            cache_path, 'w',
            driver='GTiff', height=H, width=W,
            count=C, dtype='float32',
            crs=crs, transform=new_tf,
            nodata=np.nan,
        ) as dst:
            dst.write(clipped)

    shared = next(iter(unique))
    print(f'All {len(grids)} monthly files share grid: '
          f'CRS=EPSG:{shared[0]}, clipped shape=({r1-r0}, {c1-c0})')
    return shared, (r0, r1, c0, c1)
