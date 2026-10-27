import { useEffect, useState } from "react";
import "./modelReplayPanel.css";
import RagAnalysis from "./RagAnalysis.jsx";

const pct = (p) => {
  if (!Number.isFinite(p)) return "—";
  const value = p * 100;
  if (value === 0) return "0%";
  if (value < 0.001) return "<0.001%";
  if (value < 0.1) return `${value.toFixed(3)}%`;
  if (value < 1) return `${value.toFixed(2)}%`;
  return `${value.toFixed(1)}%`;
};

export default function ModelReplayPanel({ enabled, onReplay, backendStatus, replayEnabled }) {
  const [index, setIndex] = useState(0);
  const [forecast, setForecast] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!enabled) return;
    const controller = new AbortController();
    setLoading(true);
    setError("");
    onReplay?.(null);
    fetch(`/api/replay/step?index=${index}`, { method: "POST", signal: controller.signal })
      .then(async (r) => {
        if (!r.ok) {
          const details = await r.json().catch(() => ({}));
          throw new Error(details.detail || `Replay HTTP ${r.status}`);
        }
        return r.json();
      })
      .then((data) => { setForecast(data); onReplay?.(data); })
      .catch((e) => { if (e.name !== "AbortError") { setError(e.message); setForecast(null); onReplay?.(null); } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [index, enabled]);

  const family = forecast?.family_eta;
  const horizons = forecast?.forecast;
  const matchIndex = forecast?.index === index;
  const canDisplay = enabled && !!forecast && matchIndex;
  const displayFamily = family?.family_if_onset?.replaceAll("_", " / ") ?? "Unavailable";

  return (
    <section className="model-replay-panel" aria-label="NetGuard frozen model predictions">
      <div className="model-panel-top">
        <div>
          <span className="model-panel-kicker">MODEL INFERENCE</span>
          <h3>Attack forecast</h3>
        </div>
        {backendStatus !== "connected" && (
          <span className="model-panel-status">{backendStatus === "checking" ? "CONNECTING" : "BACKEND OFFLINE"}</span>
        )}
      </div>
      {error && <p className="model-panel-error" role="alert">{error}</p>}
      {!replayEnabled && <p className="model-panel-note">Replay is paused. Enable it in Settings.</p>}
      {replayEnabled && backendStatus !== "connected" && <p className="model-panel-note">Start the backend to view forecasts.</p>}
      {loading && <p className="model-panel-note">Running model inference…</p>}
      {canDisplay && (
        <>
          <div className="model-panel-horizons">
            {[['5 minutes', horizons.h5], ['10 minutes', horizons.h10], ['15 minutes', horizons.h15]].map(([label, prob]) => (
              <div className="model-panel-metric" key={label}>
                <span>Onset within {label}</span><strong>{pct(prob)}</strong>
              </div>
            ))}
          </div>
          <div className="model-panel-details">
            <div>
              <span>Likely family, if attack occurs</span>
              <strong>{displayFamily}</strong>
              <small>{pct(family.family_probability_if_onset)} family confidence</small>
            </div>
            <div>
              <span>Estimated onset, if within 15 min</span>
              <strong>{family.conditional_eta_minutes == null ? "—" : `~${family.conditional_eta_minutes.toFixed(1)} min`}</strong>
            </div>
          </div>
          <p className="model-panel-note">Replay #{forecast.index} · Episode minute {forecast.episode_minute} · Inference #{forecast.history?.id ?? "—"}</p>
          <RagAnalysis key={`monitor-${forecast.history?.id ?? forecast.index}`} eventId={forecast.history?.id} label="Explain Prediction" />
        </>
      )}
      <div className="model-panel-controls">
        <button disabled={!enabled || loading || index === 0} onClick={() => setIndex(i => Math.max(0, i - 1))}>Previous window</button>
        <button disabled={!enabled || loading || index >= 18838} onClick={() => setIndex(i => Math.min(18838, i + 1))}>Next window</button>
        <button disabled={!enabled || loading} onClick={() => setIndex(i => (i + 1039) % 18839)}>Jump ahead</button>
        <span>Replay index: {index}</span>
      </div>
    </section>
  );
}
