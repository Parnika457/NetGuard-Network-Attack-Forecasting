# NetGuard forecasting analyst guide

This guide is project-authored technical documentation for the frozen NetGuard research demo. It is not a source of live observations or external threat intelligence.

## Independent predictions and correct interpretation

The Stacked LSTM predicts a probability that ANY attack will begin within the next 5, 10, and 15 minutes based on a synthetic 10-minute sequence of 14 minute-level input features. These H5/H10/H15 probabilities refer to general attack onset, not to any specific future family. They should be monotonically nondecreasing. Forecasting performance and risk thresholds on synthetic validation data must not be presented as real-world operational calibration.

The separately trained Competing-Risk LSTM estimates P(onset in 15 minutes) and the distribution of future attack families and onset minutes CONDITIONAL ON an onset occurring during the 15-minute horizon. The top conditional family, its probability, and expected ETA are not unconditional probabilities or an exact time-to-attack countdown. The two models are trained separately; their outputs cannot be multiplied together or treated as one jointly calibrated distribution without separate validation.

Future-family vocabulary is BRUTE_AUTH, DOS_DDOS, EXPLOIT_APP, FUZZING, RECON_SCAN. This is distinct from the present-traffic UNSW-NB15 detection vocabulary (Normal, Analysis, Backdoor, DoS, Exploits, Fuzzers, Generic, Reconnaissance, Shellcode, Worms). Similar-sounding labels are not an identical prediction target.

## Investigating an elevated general onset forecast

Review recent flows per minute, packets per second, bytes per second, packet ratios, short-term trends, change windows, and available logs. Correlate with independently observed firewall, IDS, application, authentication, and endpoint signals. Determine whether traffic is expected maintenance, authorized testing, a legitimate spike, or suspicious activity. Validate data collection, feature preprocessing, sensor completeness, and model input units before escalating. A forecast does not by itself verify an attack.

## Investigating conditional family estimates

BRUTE_AUTH: review authentication failures, unusual credential attempts, affected accounts and identity-provider logs if available. DOS_DDOS: examine concentration by destination and source, volume and connection exhaustion, service latency and upstream provider signals if available. EXPLOIT_APP: examine web/application errors, unusual request patterns, relevant vulnerability assessment records, and application logs. FUZZING: correlate malformed or varied inputs and error patterns with authorized testing schedules. RECON_SCAN: inspect unusual destination diversity, port contact rates and authorized scanning schedules. These are investigation hypotheses conditioned on a possible future onset, NOT observations made by this model.

For any suggested blocking, escalation or mitigation, first corroborate with operational telemetry and local authorization. No automatic defense actions are executed by NetGuard's RAG component.
