"""Smoke-test the Chapter 1 environment and report optional credentials."""

from __future__ import annotations

import importlib
import importlib.metadata
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Some current Windows builds no longer ship WMIC, which joblib uses when
# probing physical cores. This smoke test is intentionally single-threaded.
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")

# Make the workspace-level geoai_utils.py importable when this file is invoked
# directly as ``python scripts/verify_environment.py``.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from geoai_layers import FOUR_LAYERS


SUPPORT_IMPORTS = {
    "geotessera": "geotessera",
    "opencv-python": "cv2",
    "torchinfo": "torchinfo",
    "torchvision": "torchvision",
}


def check_imports() -> list[str]:
    failures: list[str] = []
    seen: set[str] = set()
    print("Chapter 1 four-layer imports:")
    for layer, packages in FOUR_LAYERS.items():
        print(f"\n  {layer} layer")
        for distribution, module_name in packages.items():
            if distribution in seen:
                print(f"    [ok] {distribution:<21} shared with another layer")
                continue
            seen.add(distribution)
            try:
                importlib.import_module(module_name)
                version = importlib.metadata.version(distribution)
                print(f"    [ok] {distribution:<21} {version}")
            except Exception as exc:  # Native-library failures also land here.
                failures.append(f"{distribution}: {exc}")
                print(f"    [FAIL] {distribution:<19} {exc}")

    print("\n  Supporting environment packages")
    for distribution, module_name in SUPPORT_IMPORTS.items():
        try:
            importlib.import_module(module_name)
            version = importlib.metadata.version(distribution)
            print(f"    [ok] {distribution:<21} {version}")
        except Exception as exc:
            failures.append(f"{distribution}: {exc}")
            print(f"    [FAIL] {distribution:<19} {exc}")
    return failures


def check_computation() -> None:
    import geopandas as gpd
    import numpy as np
    import scipy.ndimage
    import torch
    from shapely.geometry import Point
    from sklearn.cluster import DBSCAN

    from geoai_utils import apply_style, get_device, seed_everything

    seed_everything(42)
    apply_style()
    device = get_device()

    scene = scipy.ndimage.gaussian_filter(
        np.random.default_rng(42).standard_normal((64, 64)), sigma=5
    )
    labels = DBSCAN(eps=0.5, min_samples=2, n_jobs=1).fit_predict(
        np.array([[0.0, 0.0], [0.1, 0.1], [5.0, 5.0]])
    )
    frame = gpd.GeoDataFrame(
        {"cluster": labels},
        geometry=[Point(0, 0), Point(0.1, 0.1), Point(5, 5)],
        crs="EPSG:4326",
    ).to_crs("EPSG:3857")
    tensor = torch.from_numpy(scene).float().to(device)
    result = tensor.square().mean().item()

    print("\nRuntime checks:")
    print(f"  Python:       {sys.version.split()[0]}")
    print(f"  Device:       {device}")
    print(f"  PyTorch CUDA: {torch.version.cuda or 'not compiled'}")
    if torch.cuda.is_available():
        print(f"  GPU:          {torch.cuda.get_device_name(0)}")
    print(f"  GeoDataFrame: {len(frame)} projected features")
    print(f"  Tensor mean:  {result:.6f}")


def check_credentials() -> None:
    load_dotenv()
    print("\nOptional services:")
    for name in ("GEE_PROJECT_ID", "GROQ_API_KEY"):
        value = os.getenv(name, "")
        configured = bool(value and "replace" not in value and "your-" not in value)
        status = "configured" if configured else "not configured (expected for now)"
        print(f"  {name}: {status}")


def main() -> int:
    failures = check_imports()
    if failures:
        print("\nImport failures:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    check_computation()
    check_credentials()
    print("\nEnvironment verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
