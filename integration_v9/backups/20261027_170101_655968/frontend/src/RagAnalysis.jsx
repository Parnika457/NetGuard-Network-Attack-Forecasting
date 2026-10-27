import { useEffect, useRef, useState } from "react";
import "./ragAnalysis.css";

function percent(probability) {
  if (!Number.isFinite(probability)) return "—";
  const pct = probability * 100;
  if (pct === 0) return "0%";
  if (pct < 0.001) return "<0.001%";
  if (pct < 0.1) return `${pct.toFixed(3)}%`;
  if (pct < 1) return `${pct.toFixed(2)}%`;
  return `${pct.toFixed(1)}%`;
}

const familyLabel = (family) => family?.replaceAll("_", " / ") ?? null;

function Reference({ source }) {
  const content = (
    <>
      <strong>{source.title}</strong>
      <small>{source.source_type === "curated_reference_summary"
        ? "Research summary · Primary reference"
        : source.source_type === "project_documentation"
          ? "Project documentation" : "Knowledge base"}</small>
    </>
  );
  return (
    <div className="ngr-reference">
      {source.source_url ? (
        <a href={source.source_url} target="_blank" rel="noopener noreferrer" className="ngr-source-link">
          <div className="ngr-source-copy">{content}</div><span aria-hidden="true">↗</span>
        </a>
      ) : <div className="ngr-source-title"><div className="ngr-source-copy">{content}</div></div>}
    </div>
  );
}

function PredictionContext({ context }) {
  if (!context) return null;
  return (
    <div className="ngr-context">
      {context.kind === "forecast" ? (
        <>
          <p><strong>Saved forecast</strong> · H5 {percent(context.h5)} · H10 {percent(context.h10)} · H15 {percent(context.h15)}</p>
          {context.family_if_onset && <p>Conditional family: <strong>{familyLabel(context.family_if_onset)}</strong>
            {Number.isFinite(context.family_probability_if_onset)
              ? ` (${percent(context.family_probability_if_onset)} if onset)` : ""}
            {Number.isFinite(context.conditional_eta_minutes)
              ? ` · ETA ~${context.conditional_eta_minutes.toFixed(1)} min if onset` : ""}</p>}
        </>
      ) : (
        <p><strong>Saved detection</strong> · {context.attack_class} · {percent(context.confidence)} model confidence</p>
      )}
    </div>
  );
}

export default function RagAnalysis({ eventId, label = "Explain Prediction" }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [context, setContext] = useState(null);
  const [error, setError] = useState("");
  const controller = useRef(null);

  useEffect(() => () => controller.current?.abort(), []);

  const toggle = async () => {
    if (open) { setOpen(false); return; }
    setOpen(true);
    if (result || loading || !Number.isInteger(eventId)) return;
    controller.current?.abort();
    const request = new AbortController();
    controller.current = request;
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`/api/rag/explain/history/${eventId}`, {
        method: "POST", signal: request.signal,
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof data.detail === "string"
        ? data.detail : `Analysis unavailable (HTTP ${response.status})`);
      if (data.inference_id !== eventId || !data.analysis) throw new Error("Unexpected analysis response");
      setResult(data.analysis);
      setContext(data.prediction_context ?? null);
    } catch (cause) {
      if (cause.name !== "AbortError") setError(cause.message || "Unable to analyze this prediction");
    } finally {
      if (!request.signal.aborted) setLoading(false);
    }
  };

  // Keep only sources cited by this response; never display duplicate documents.
  const unique = new Set();
  const references = (result?.sources ?? []).filter(source => {
    if (!result?.cited_source_ids?.includes(source.source_id)) return false;
    const identity = source.source_url || source.title;
    if (unique.has(identity)) return false;
    unique.add(identity);
    return true;
  });

  return (
    <div className="ngr-root">
      <button type="button" className="ngr-trigger" onClick={toggle}
        disabled={!Number.isInteger(eventId)} aria-expanded={open}>
        <span className="ngr-sparkle" aria-hidden="true">✦</span>
        {label}{loading ? " · Analyzing…" : ""}
        <span className="ngr-caret" aria-hidden="true">{open ? "−" : "+"}</span>
      </button>
      {open && (
        <section className="ngr-panel" aria-label="RAG prediction analysis">
          {loading && <p className="ngr-status" role="status">Analyzing saved prediction…</p>}
          {error && <div className="ngr-error" role="alert">{error} <button type="button" onClick={() => { setOpen(false); setError(""); }}>Close</button></div>}
          {result && (
            <>
              <div className="ngr-heading"><h4>Prediction analysis</h4><span>AI-assisted</span></div>
              <PredictionContext context={context} />
              <div className="ngr-section ngr-assessment">
                <h5>Risk assessment</h5>
                <p className="ngr-summary">{result.summary}</p>
                {result.explanation && <p className="ngr-explanation">{result.explanation}</p>}
              </div>
              {!!result.investigation_steps?.length && <div className="ngr-section">
                <h5>Recommended investigation</h5>
                <ol>{result.investigation_steps.map((step, i) => <li key={i}>{step}</li>)}</ol>
              </div>}
              {!!references.length && <details className="ngr-section ngr-sources">
                <summary>Supporting references ({references.length})</summary>
                <div className="ngr-references">{references.map(source => <Reference key={source.source_id} source={source} />)}</div>
              </details>}
            </>
          )}
        </section>
      )}
    </div>
  );
}
