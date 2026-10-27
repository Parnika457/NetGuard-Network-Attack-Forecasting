# NetGuard V1 — Research-demo integration freeze

This is **not** production validation. Do not train or test on the embargoed official TEST dataset as part of this step.

## Required existing reports

- `backend/model_release/netguard_v1_candidate.json`
- `backend/model_release/validation_windows_v1.json`
- `backend/model_release/detection_validation_v1.json`
- `backend/validation_data/windows_W10_VALIDATION.npz`

All are created by the previous verification and validation steps. This kit contains **no weights and no large datasets**.

## VS Code setup

Extract `NetGuard_V1_Integration_Freeze_Kit.zip` into your project root, with `backend/` next to `model/` and `frontend/`. Activate `.venv312`.

```bash
python backend/freeze_integration_release.py
cat backend/model_release/netguard_v1_integration_freeze.json
```

The script verifies selected artifact hashes, validates all 18,839 synthetic forecast validation rows and 35,167 detection development validation rows as recorded in the reports, and creates the manifest. It checks that the original run's labels and evaluation status remain consistent but **does not rerun inference**; those runs were performed separately.

The frozen manifest has status `FROZEN_FOR_RESEARCH_DEMO_INTEGRATION_DEV_VALIDATED`. This explicitly does *not* claim operational readiness or independent TEST scores. The script refuses to overwrite a differing existing release.

## Before committing to GitHub

Because the project was downloaded as a **GitHub ZIP**, it probably has **no `.git/` metadata**. `git status` will tell you. To publish, clone the actual repo and copy the `backend/` scripts and `backend/model_release/*.json` into the cloned repo.

In the cloned repo's ROOT `.gitignore`, add:

```
.venv/
.venv312/
__pycache__/
*.pyc
backend/validation_data/
```

Do not commit downloaded raw UNSW-NB15 CSV or `windows_W10_VALIDATION.npz`. Commit the manifests and source code. If adding a Git tag, give it a **demo/integration** name (`netguard-models-v1.0.0-demo`) and don't imply production validation.
