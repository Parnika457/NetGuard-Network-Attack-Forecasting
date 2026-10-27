import { useEffect, useState } from "react";

const pct = v => Number.isFinite(v) ? `${(v*100).toFixed(1)}%` : "N/A";
const timestamp = v => v ? new Date(v).toLocaleString() : "—";
const familyLabel = v => v?.replaceAll("_", " ") || "Not available";

export function HistoryView({ onSelect }) {
  const [items, setItems] = useState([]);
  const [nextOffset, setNextOffset] = useState(null);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    fetch(`/api/history?limit=50&offset=${page}`, { signal:controller.signal })
      .then(async r => { if(!r.ok) throw new Error(`History API HTTP ${r.status}`); return r.json(); })
      .then(data => { setItems(old => page ? [...old, ...data.items] : data.items);
                      setTotal(data.total); setNextOffset(data.next_offset); setError(""); })
      .catch(e => { if(e.name !== "AbortError") setError(e.message); })
      .finally(() => { if(!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [page]);

  return <div><div className="page-heading"><h2>Inference History</h2>
    <p>Stored model predictions from this local NetGuard demo. These are not confirmed network attacks.</p></div>
    {error && <p role="alert" className="model-panel-error">{error}</p>}
    {!loading && items.length === 0 && <section className="card ng-empty-history">
      <h3>No saved model inferences yet</h3><p>Open Monitor and replay a window to record a prediction here.</p></section>}
    {items.length > 0 && <section className="card history-list">
      {items.map(e => { const pred=e.prediction; const isForecast=e.event_type==="FORECAST_INFERENCE";
        const h10=isForecast?pred.forecast?.h10:null;
        return <button key={e.id} className="history-item" onClick={() => onSelect(e)}>
          <div className="history-main"><div className="history-icon">◎</div><div>
            <strong>{isForecast ? `Forecast · ${familyLabel(pred.family_eta?.family_if_onset)}` : `Detection · ${pred.result?.predicted_class || "Unknown"}`}</strong>
            <span>{isForecast ? `Replay #${e.replay_index} · episode minute ${e.episode_minute}` : "Provided network-flow inference"}</span>
            <small>Recorded: {timestamp(e.created_utc)} · {e.model_release}</small></div></div>
          <div className="history-right"><span className="ng-history-prob">{isForecast ? `H10 ${pct(h10)}` : `Attack score ${pct(pred.result?.attack_probability)}`}</span>
            <span className="arrow">→</span></div></button>;
      })}
    </section>}
    {loading && <p className="model-panel-note">Loading recorded inferences…</p>}
    <div className="ng-history-footer"><span>{items.length} of {total} saved inferences</span>
      {nextOffset != null && <button className="ng-action" disabled={loading} onClick={()=>setPage(nextOffset)}>Load more</button>}
    </div>
  </div>;
}

export function HistoryReport({ event, onBack }) {
  const p = event.prediction;
  const forecast=event.event_type==="FORECAST_INFERENCE";
  return <div><button className="back-button" onClick={onBack}>← Back to History</button>
    <div className="page-heading"><h2>Recorded Inference #{event.id}</h2>
      <p>{forecast ? "Forecast replay" : "Current-attack classifier"} · Prediction record, not an observed attack incident</p></div>
    <section className="card report-card"><div className="report-title"><div>
      <span className="subheading">{event.event_type.replaceAll("_", " ")}</span>
      <h2>{forecast ? familyLabel(p.family_eta?.family_if_onset) : p.result?.predicted_class}</h2>
      </div></div>
      <div className="report-grid">
        <div><span>Recorded at</span><strong>{timestamp(event.created_utc)}</strong></div>
        <div><span>Data source</span><strong>{event.mode.replaceAll("_", " ")}</strong></div>
        <div><span>Model release</span><strong>{event.model_release}</strong></div>
        {forecast && <>
          <div><span>Forecast within 5m</span><strong>{pct(p.forecast?.h5)}</strong></div>
          <div><span>Forecast within 10m</span><strong>{pct(p.forecast?.h10)}</strong></div>
          <div><span>Forecast within 15m</span><strong>{pct(p.forecast?.h15)}</strong></div>
          <div><span>Family confidence, if onset</span><strong>{pct(p.family_eta?.family_probability_if_onset)}</strong></div>
          <div><span>Expected ETA, if onset</span><strong>{p.family_eta?.conditional_eta_minutes == null ? "N/A" : `~${p.family_eta.conditional_eta_minutes.toFixed(1)} min`}</strong></div>
          <div><span>Episode minute</span><strong>{event.episode_minute}</strong></div>
        </>}
        {!forecast && <><div><span>Attack score</span><strong>{pct(p.result?.attack_probability)}</strong></div>
          <div><span>Predicted class</span><strong>{p.result?.predicted_class}</strong></div>
          <div><span>Threshold used</span><strong>{p.result?.threshold} (exploratory)</strong></div></>}
      </div>
      <div className="report-section"><span className="subheading">INTERPRETATION</span>
        <p>These values came from the actual frozen trained model at the recorded time. They are not an attack confirmation or evidence that defensive actions were executed. Forecasting results are based on simulated precursors and not calibrated for live-network alerting.</p></div>
    </section>
  </div>;
}
