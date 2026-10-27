# NetGuard model contract and interpretation boundaries

The project has two different tasks. Current attack detection classifies individual UNSW-NB15-derived network flows into ten categories: Normal, Analysis, Backdoor, DoS, Exploits, Fuzzers, Generic, Reconnaissance, Shellcode, and Worms. Forecasting models operate on distinct synthetic minute-level data derived from CIC-IDS2017 and UNSW-NB15. These inputs MUST NOT be treated as one shared feature schema.

Available research checkpoint families include current detection XGBoost and CatBoost; future-risk LSTM, TCN, XGBoost and graph forecasting. Checkpoints are not an executable inference API. Their preprocessing and actual output contracts must be verified before backend integration.

A target=any_attack forecast means risk of some attack within the specified horizon. It does NOT imply a class-specific forecast. A target=specific_attack result can mention a specific future class only if the producing model explicitly supports that output. Do not assume class-specific functionality from saved weights or notebook filenames.

H5 and H10 denote future windows in minutes when that convention is verified for the actual model. The incoming horizon_minutes field states the intended window but MUST match the producing model's implementation. Raw model scores are not necessarily calibrated probabilities; inspect held-out evaluation, class imbalance and calibration before claiming a literal incidence rate. Development-validation scores must not be represented as independent external tests.

RAG retrieves reference content, summarizes evidence, and proposes investigation steps. It does not run models, observe traffic, confirm malicious actions, provide forensic attribution, or prove a future event will occur. Synthetic demonstration event values are not telemetry.
