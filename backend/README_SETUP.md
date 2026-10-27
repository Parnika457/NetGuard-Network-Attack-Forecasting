# NetGuard V1 candidate model verification (macOS / VS Code)

## Install location
Copy the **backend** folder next to your existing **frontend** and **model** folders in `Network-Attack-Forecasting-Project-main`.

## Commands from the project root in VS Code terminal

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
python backend/verify_and_freeze.py
```

Use **Python 3.12** if possible. If `python3` is older than 3.11 or dependencies fail to install, install Python 3.12 and use `python3.12 -m venv .venv` instead. The saved detection preprocessor requires **scikit-learn 1.6.1**, which is pinned in requirements.

## Expected result

- 3 artifact-hash checks PASS
- 3 smoke checks PASS
- A JSON candidate manifest at `backend/model_release/netguard_v1_candidate.json`

The sample input is **all-zero fake network data** solely to check that the saved
weights and preprocessing run. Any predicted values printed are NOT an attack
assessment, nor independent accuracy validation.

## Freezing properly (second step)

Before creating a Git version tag, obtain actual `windows_W10_VALIDATION.npz`
and saved reference predictions from the original Google Drive development
folder. Check model predictions against those exact saved reference outputs.
The GitHub model ZIP includes no such frozen validation window/reference
pairs. Recheck Python dependencies and feature contract, and choose alert
thresholds based on proper evaluation. **Do not label this candidate production ready.**

## Cautions

- DO NOT rerun training notebooks to "freeze" the weights.
- DO NOT fit a new scaler on input data.
- DO NOT mix 42-feature current-detection records with 10×14 forecasting windows.
- The detection pipeline uses joblib/pickle; only load trusted local files after checking hashes.
- Forecasting input columns must exactly match feature names and ordering in the manifest.

## Confirm the scikit-learn version

```bash
python -c "import sklearn; print(sklearn.__version__)"
```

It must print `1.6.1`. If not, use a clean venv and reinstall requirements.
