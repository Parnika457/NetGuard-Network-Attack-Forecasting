import { useEffect, useRef, useState } from "react";
import "./ragAnalysis.css";

// Display probabilities from the recorded inference, never reconstructed by the LLM.
function percent(probability) {
  if (typeof probability !== "number" || !Number.isFinite(probability) || probability < 0 || probability > 1) return "—";
  const pct = probability * 100;
  if (pct === 0) return "0%";
  if (pct < 0.001) return "<0.001%";
  if (pct < 0.1) return `${pct.toFixed(3)}%`;
  if (pct < 1) return `${pct.toFixed(2)}%`;
  return `${pct.toFixed(1)}%`;
}

const FAMILY_NAMES = {
  BRUTE_AUTH: "Brute force / authentication",
  DOS_DDOS: "DoS / DDoS",
  EXPLOIT_APP: "Application exploitation",
  FUZZING: "Fuzzing",
  RECON_SCAN: "Reconnaissance / scanning",
};
const familyLabel = value => FAMILY_NAMES[value] || value?.replaceAll("_", " ") || "Unspecified";

// Title is linked once; the research-summary label itself is plain text.
function Reference({ source }) {
  const title = String(source.title || "Reference").replace(/\s*\(NetGuard research summary\)$/i, "");
  const url = typeof source.source_url === "string" && /^https:\/\//i.test(source.source_url)
    ? source.source_url : null;
  const summary = source.source_type === "curated_reference_summary";
  const origin = title.includes("MITRE ATT&CK") ? "MITRE ATT&CK"
    : title.includes("NIST") ? "NIST" : "NetGuard knowledge base";
  const subtitle = summary ? `Research summary · ${origin}`
    : source.source_type === "project_documentation" ? "Project documentation" : "Knowledge base";
  return (
    <div className="ngr-reference">
      <div className="ngr-source-copy">
        {url ? (
          <a className="ngr-single-link" href={url} target="_blank" rel="noopener noreferrer">
            {title}<span aria-hidden="true"> ↗</span>
          </a>
        ) : <strong className="ngr-single-title">{title}</strong>}
        <span className="ngr-source-subtitle">{subtitle}</span>
      </div>
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
              ? ` · ${percent(context.family_probability_if_onset)} if onset` : ""}
            {Number.isFinite(context.conditional_eta_minutes)
              ? ` · ETA ~${context.conditional_eta_minutes.toFixed(1)} min if onset` : ""}</p>}
        </>
      ) : (
        <p><strong>Saved detection</strong> · {context.attack_class} · {percent(context.confidence)} model confidence</p>
      )}
    </div>
  );
}

function RiskAssessment({ context, result }) {
  if (context?.kind === "forecast" && Number.isFinite(context.h10) && Number.isFinite(context.h15)) {
    return (
      <div className="ngr-section ngr-assessment">
        <h5>Risk assessment</h5>
        <p className="ngr-summary">
          The model estimates an attack-onset score of <strong>{percent(context.h10)}</strong> within 10 minutes
          and <strong>{percent(context.h15)}</strong> within 15 minutes.
          {context.family_if_onset && Number.isFinite(context.family_probability_if_onset) && (
            <> If an attack begins within 15 minutes, <strong>{familyLabel(context.family_if_onset)}</strong> is the leading predicted family
              (<strong>{percent(context.family_probability_if_onset)}</strong> conditional confidence).</>
          )}
          {Number.isFinite(context.conditional_eta_minutes) && (
            <> The estimated time to onset is about <strong>{context.conditional_eta_minutes.toFixed(1)} minutes</strong>, conditional on onset within that horizon.</>
          )}
        </p>
        <p className="ngr-note">Synthetic replay prediction, not a confirmed attack.</p>
      </div>
    );
  }
  if (context?.kind === "detection" && Number.isFinite(context.confidence)) {
    return (
      <div className="ngr-section ngr-assessment">
        <h5>Risk assessment</h5>
        <p className="ngr-summary">The model classified this saved flow as <strong>{context.attack_class}</strong> with
          <strong> {percent(context.confidence)}</strong> model confidence.</p>
        <p className="ngr-note">A model classification is not independent confirmation of an incident.</p>
      </div>
    );
  }
  return <div className="ngr-section ngr-assessment">
    <h5>Risk assessment</h5>
    <p className="ngr-summary">{result.summary}</p>
    {result.explanation && <p className="ngr-explanation">{result.explanation}</p>}
  </div>;
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

  const unique = new Set();
  const references = (result?.sources ?? []).filter(source => {
    if (!result?.cited_source_ids?.includes(source.source_id)) return false;
    const identity = (source.source_url || source.title || "").trim().toLowerCase();
    if (!identity || unique.has(identity)) return false;
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
              <RiskAssessment context={context} result={result} />
              {!!result.investigation_steps?.length && <div className="ngr-section">
                <h5>Recommended investigation</h5>
                <ol>{result.investigation_steps.slice(0, 3).map((step, i) => <li key={i}>{step}</li>)}</ol>
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
