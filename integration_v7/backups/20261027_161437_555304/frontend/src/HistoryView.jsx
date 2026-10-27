import { useEffect, useState } from "react";
import "./historyView.css";

const percentage = (value) => {
  if (!Number.isFinite(value)) return "—";
  if (value > 0 && value < 0.0005) return "<0.1%";
  return `${(value * 100).toFixed(1)}%`;
};

const dateTime = (value) => {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString(undefined, {
    day: "numeric", month: "short", year: "numeric",
    hour: "numeric", minute: "2-digit",
  });
};

const familyName = (value) => {
  const labels = {
    BRUTE_AUTH: "Brute force",
    DOS_DDOS: "DoS / DDoS",
    EXPLOIT_APP: "Application exploit",
    FUZZING: "Fuzzing",
    RECON_SCAN: "Reconnaissance",
  };
  return labels[value] || (value ? value.replaceAll("_", " ") : "Not available");
};

const isForecast = (event) => event?.event_type === "FORECAST_INFERENCE";

const recordTitle = (event) =>
  isForecast(event) && event.replay_index != null
    ? `Replay #${event.replay_index}`
    : `Record #${event.id}`;

function Metric({ label, value, featured = false }) {
  return (
    <div className={`ngh-metric${featured ? " ngh-metric-primary" : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Detail({ label, value }) {
  return (
    <div className="ngh-detail">
      <span>{label}</span>
      <strong>{value ?? "—"}</strong>
    </div>
  );
}

export function HistoryView({ onSelect }) {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [nextOffset, setNextOffset] = useState(null);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    fetch(`/api/history?limit=50&offset=${offset}`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(`History unavailable (HTTP ${response.status})`);
        return response.json();
      })
      .then((data) => {
        setItems((previous) => offset ? [...previous, ...data.items] : data.items);
        setTotal(data.total);
        setNextOffset(data.next_offset);
        setError("");
      })
      .catch((cause) => {
        if (cause.name !== "AbortError") setError(cause.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [offset]);

  return (
    <div className="ngh-root">
      <div className="page-heading ngh-heading">
        <div>
          <h2>Inference History</h2>
          <p>Saved forecasts and detection results</p>
        </div>
        <span className="ngh-count">{total} records</span>
      </div>

      {error && <div role="alert" className="ngh-error">{error}</div>}
      {!loading && items.length === 0 && !error && (
        <section className="card ngh-empty">
          <strong>No records yet</strong>
          <span>Run a replay from Monitor to save its predictions here.</span>
        </section>
      )}

      {items.length > 0 && (
        <section className="card ngh-history-list" aria-label="Saved model inferences">
          {items.map((event) => {
            const forecast = isForecast(event);
            const prediction = event.prediction || {};
            const score = forecast ? prediction.forecast?.h10 : prediction.result?.attack_probability;
            const name = forecast
              ? familyName(prediction.family_eta?.family_if_onset)
              : prediction.result?.predicted_class || "Unspecified class";
            return (
              <button
                key={event.id}
                type="button"
                className="ngh-history-row"
                onClick={() => onSelect(event)}
                aria-label={`Open ${recordTitle(event)}`}
              >
                <div className="ngh-history-left">
                  <div className="ngh-history-title">
                    <strong>{recordTitle(event)}</strong>
                    <span className="ngh-type">{forecast ? "Forecast" : "Detection"}</span>
                  </div>
                  <div className="ngh-history-sub">
                    {forecast ? `Family if onset: ${name}` : `Predicted class: ${name}`}
                    {forecast && event.episode_minute != null && ` · Minute ${event.episode_minute}`}
                  </div>
                  <time className="ngh-history-time" dateTime={event.created_utc}>{dateTime(event.created_utc)}</time>
                </div>
                <div className="ngh-history-right">
                  <span>{forecast ? "10-min risk" : "Attack score"}</span>
                  <strong>{percentage(score)}</strong>
                </div>
                <span aria-hidden="true" className="ngh-chevron">›</span>
              </button>
            );
          })}
        </section>
      )}

      <div className="ngh-footer">
        <span>{items.length} of {total} records</span>
        {nextOffset != null && (
          <button type="button" className="ngh-load" disabled={loading} onClick={() => setOffset(nextOffset)}>
            {loading ? "Loading…" : "Load more"}
          </button>
        )}
        {loading && items.length === 0 && <span>Loading…</span>}
      </div>
    </div>
  );
}

export function HistoryReport({ event, onBack }) {
  const prediction = event.prediction || {};
  const forecast = isForecast(event);
  const family = familyName(prediction.family_eta?.family_if_onset);
  const eta = prediction.family_eta?.conditional_eta_minutes;

  return (
    <div className="ngh-root ngh-report">
      <button type="button" className="back-button" onClick={onBack}>← Back to History</button>

      <div className="ngh-report-header">
        <div>
          <div className="ngh-report-eyebrow">
            <span className="ngh-type">{forecast ? "Forecast" : "Detection"}</span>
            <span>Saved model prediction</span>
          </div>
          <h2>{recordTitle(event)}</h2>
          <p>{forecast ? "Synthetic validation replay" : "Flow classification"}</p>
        </div>
        <div className="ngh-recorded">
          <span>Recorded at</span>
          <strong>{dateTime(event.created_utc)}</strong>
        </div>
      </div>

      <section className="card ngh-report-card">
        <div className="ngh-section-head"><h3>{forecast ? "Forecast probabilities" : "Detection result"}</h3></div>
        {forecast ? (
          <div className="ngh-metrics-grid">
            <Metric label="Next 5 minutes" value={percentage(prediction.forecast?.h5)} />
            <Metric label="Next 10 minutes" value={percentage(prediction.forecast?.h10)} featured />
            <Metric label="Next 15 minutes" value={percentage(prediction.forecast?.h15)} />
          </div>
        ) : (
          <div className="ngh-metrics-grid ngh-metrics-two">
            <Metric label="Predicted class" value={prediction.result?.predicted_class || "—"} />
            <Metric label="Attack score" value={percentage(prediction.result?.attack_probability)} featured />
          </div>
        )}
      </section>

      {forecast && (
        <section className="card ngh-report-card">
          <div className="ngh-section-head"><h3>Onset estimate</h3><span>Conditional on an attack occurring</span></div>
          <div className="ngh-details-grid ngh-highlight-grid">
            <Detail label="Candidate family" value={family} />
            <Detail label="Family confidence" value={percentage(prediction.family_eta?.family_probability_if_onset)} />
            <Detail label="Estimated time to onset" value={Number.isFinite(eta) ? `~${eta.toFixed(1)} minutes` : "—"} />
          </div>
        </section>
      )}

      <section className="card ngh-report-card">
        <div className="ngh-section-head"><h3>Record details</h3></div>
        <div className="ngh-details-grid">
          <Detail label="Data source" value={event.mode?.replaceAll("_", " ")} />
          <Detail label="Model release" value={event.model_release} />
          {forecast && event.episode_minute != null && <Detail label="Episode minute" value={event.episode_minute} />}
          {forecast && event.replay_index != null && <Detail label="Replay index" value={event.replay_index} />}
          {!forecast && <Detail label="Decision threshold" value={Number.isFinite(prediction.result?.threshold) ? prediction.result.threshold.toFixed(2) : "—"} />}
        </div>
      </section>
    </div>
  );
}
