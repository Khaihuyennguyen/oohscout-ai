# GitHub Setup — Step by Step

**Purpose:** initialize this repo as git, push to GitHub, and create the first feature branch.

**Prerequisites:**
- GitHub account (I don't have your credentials, so YOU do this part)
- `git` installed locally
- A decision: **public repo or private?**
  - **Public** — portfolio value, but code is scrutinized publicly. Consider private until Track A ships.
  - **Private** — safer for pre-MVP. Can flip to public later at any time.

**Recommendation:** start **private**, flip to public around Week 22 (after Track B ships) when you have something impressive.

---

## Step 1 — Verify the reorg looks right (do this BEFORE git init)

```bash
cd "c:/Users/nguye/Documents/billboardAI/"
ls              # should see: backend/, frontend/, docs/, README.md, CLAUDE.md, pyproject.toml, .gitignore
ls docs/        # should see: PRD.md, FEATURES.md, MASTER_PLAN.md, DATA_VERIFICATION.md, CLAUDE.md, learning/, decisions/
ls backend/     # should see: src/, tests/, notebooks/, scripts/, geoai_utils.py, README.md
ls docs/learning/chapters/  # should see: geoai_ch04_data_prep/, geoai_ch05_segmentation/, ua_advanced_ch01_setup/
```

If any of these look wrong, tell me and we fix before initializing git.

---

## Step 2 — Delete the old originals (only after Step 1 looks good)

The reorg **copied** files (non-destructive). To clean up:

```bash
cd "c:/Users/nguye/Documents/billboardAI/"

# Old top-level docs (moved to docs/)
rm CLAUDE.md.old 2>/dev/null || true  # (we keep root CLAUDE.md; only delete the .old if any)
# We keep root CLAUDE.md because that's where Claude Code reads project instructions.
# But we also have a copy in docs/CLAUDE.md — remove that duplicate:
rm docs/CLAUDE.md

rm DATA_VERIFICATION_REPORT.md
rm OOHSCOUT_FEATURES.md
rm OOHSCOUT_MASTER_PLAN.md
rm oohscout_architecture_master.html

# Old notebooks folder — files were copied to backend/notebooks/, delete original
# ⚠️ BEFORE running this, verify backend/notebooks/ has what you need
rm -rf notebooks/  # ONLY after confirming backend/notebooks/ is complete

# Leftover from GeoAI Ch 1 setup (not needed for OOHScout product)
rm -rf geoai_layers/  # only if you're sure this can go
rm Chapter_01_Setup_Verification.ipynb  # copied to backend/, delete root copy
rm -rf quizzes/  # leftover from Ch 1 setup
rm -rf tmp/
rm -rf __pycache__/

# geoai_utils.py at root — moved to backend/
rm geoai_utils.py  # only if backend/geoai_utils.py exists
```

**Recommendation:** Do the deletions one line at a time. If unsure, keep it — you can delete later.

---

## Step 3 — Initialize git

```bash
cd "c:/Users/nguye/Documents/billboardAI/"

git init
git branch -M main
```

Verify `.gitignore` will hide sensitive things:

```bash
git status  # should NOT show data/, .venv/, .env, or Milan's course files
```

If TxDOT data or Milan's ipynb files appear in `git status`, STOP and fix `.gitignore` first.

---

## Step 4 — First commit

```bash
git add .
git status  # review what you're about to commit — should be roughly:
#   .env.example, .gitignore, .python-version, CLAUDE.md, README.md,
#   pyproject.toml, uv.lock, backend/**, docs/**, frontend/**

git commit -m "Initial commit: OOHScout AI foundation (frontend/backend/docs structure + PRD)"
```

---

## Step 5 — Create GitHub repo

**On github.com:**
1. Go to https://github.com/new
2. Repo name: `oohscout-ai` (or your choice)
3. Description: `AI-assisted OOH billboard site intelligence — GeoAI + Regulatory RAG + Autonomous Agent`
4. Visibility: **Private** (recommended for now)
5. Do NOT initialize with README/gitignore/license — you already have them locally
6. Click **Create repository**

GitHub will show you commands. Ignore theirs; use these:

---

## Step 6 — Push to GitHub

```bash
cd "c:/Users/nguye/Documents/billboardAI/"

# Replace YOUR_USERNAME with your GitHub username
git remote add origin https://github.com/YOUR_USERNAME/oohscout-ai.git

git push -u origin main
```

You may be prompted for authentication:
- Use a **Personal Access Token** (not password) — create one at https://github.com/settings/tokens
- Or configure GitHub CLI: `gh auth login`

---

## Step 7 — Create first feature branch

**⚠️ Important:** I recommend NOT creating a feature branch until you've actually started working on Feature 1 (Retargetable Study Area via UA Advanced Ch 1). Creating an empty branch adds noise.

**When you're ready to start Chapter 1:**

```bash
git checkout -b feature/f1-retargetable-study-area

# Then start the chapter workflow:
# 1. cp -r docs/learning/template docs/learning/chapters/ua_advanced_ch01_setup
# 2. Create and retype 01_milan_original.ipynb
# 3. Ask Claude to write 02_milan_explanation.md
# 4. Create and build 03_oohscout_adaptation.ipynb (with Claude's guidance)
# 5. Ask Claude to write 04_adaptation_explanation.md
# 6. Update PRD marking F1 (and F2, F5, F43) as complete
# 7. Commit and push

git add docs/learning/chapters/ua_advanced_ch01_setup/
git commit -m "F1, F2, F5, F43: retargetable study area for McLennan County (UA Adv Ch 1)"
git push -u origin feature/f1-retargetable-study-area
```

Then on GitHub, open a Pull Request from `feature/f1-retargetable-study-area` → `main` for self-review.

**Do NOT merge to main until:**
- All 4 files exist in the chapter folder
- PRD is updated
- The adaptation notebook runs end-to-end without errors

---

## Step 8 — Standard branch workflow (per chapter/feature going forward)

```bash
# Start a new chapter
git checkout main
git pull
git checkout -b feature/f10-f18-demand-engine  # multiple features from one chapter

# ... work ...

# When ready
git add .
git commit -m "F10-F15: advertiser POI clustering (UA Adv Ch 2)"
git push -u origin feature/f10-f18-demand-engine
```

---

## Common gotchas

**"remote origin already exists":**
```bash
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/oohscout-ai.git
```

**"Authentication failed":**
- Use a Personal Access Token, not your password
- Create one at https://github.com/settings/tokens
- Give it `repo` scope

**"Large files rejected":**
- GitHub has a 100MB per-file limit
- Check what's being pushed: `git ls-files | xargs ls -lh | sort -k5 -h | tail -20`
- If any large file slipped through .gitignore, add it and rewrite history:
  ```bash
  git rm --cached path/to/large/file
  echo "path/to/large/file" >> .gitignore
  git add .gitignore
  git commit -m "Ignore large file"
  git push --force  # only on your feature branch, never on main
  ```

**"I accidentally committed .env or secrets":**
- Change every secret immediately
- Use `git filter-repo` or BFG to remove from history
- Don't try to fix by force-push unless you've rotated the secret

---

## Post-push sanity check

After push completes, visit `https://github.com/YOUR_USERNAME/oohscout-ai` and verify:
- README displays with proper formatting
- `docs/PRD.md` renders as markdown
- No TxDOT data files or Milan's course notebooks are visible
- `.gitignore` is present

If any course files are visible, STOP and remove them via `git filter-repo`.

---

**When you're done with Step 6, come back and let me know. Then we can decide:**
- Do Chapter 1 today (aggressive path), or
- Buy Intro course first (Milan-recommended path)
