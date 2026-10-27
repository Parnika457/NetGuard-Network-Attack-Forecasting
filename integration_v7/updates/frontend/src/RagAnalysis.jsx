import { useEffect, useRef, useState } from "react";
import "./ragAnalysis.css";

function Reference({ source }) {
  return (
    <div className="ngr-reference">
      <span className="ngr-source-id">{source.source_id}</span>
      <div>
        <strong>{source.title}</strong>
        {source.source_url ? (
          <a href={source.source_url} target="_blank" rel="noopener noreferrer">View source ↗</a>
        ) : <small>{source.source_type === "project_guide" ? "NetGuard knowledge base" : "Project documentation"}</small>}
      </div>
    </div>
  );
}

export default function RagAnalysis({ eventId, label = "Explain Prediction" }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
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
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : `Analysis unavailable (HTTP ${response.status})`);
      if (data.inference_id !== eventId || !data.analysis) throw new Error("Unexpected analysis response");
      setResult(data.analysis);
    } catch (cause) {
      if (cause.name !== "AbortError") setError(cause.message || "Unable to analyze this prediction");
    } finally {
      if (!request.signal.aborted) setLoading(false);
    }
  };

  // The key supplied by each parent resets this component between saved inferences.
  const cited = result?.sources?.filter(s => result.cited_source_ids?.includes(s.source_id)) || [];
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
          {loading && <p className="ngr-status" role="status">Retrieving sources and preparing analysis…</p>}
          {error && <div className="ngr-error" role="alert">{error} <button type="button" onClick={() => { setOpen(false); setError(""); }}>Close</button></div>}
          {result && (
            <>
              <div className="ngr-heading"><h4>Prediction analysis</h4><span>AI-assisted</span></div>
              <p className="ngr-summary">{result.summary}</p>
              {result.explanation && <p className="ngr-explanation">{result.explanation}</p>}
              {!!result.investigation_steps?.length && <div className="ngr-section">
                <h5>Recommended investigation</h5>
                <ol>{result.investigation_steps.map((step, i) => <li key={i}>{step}</li>)}</ol>
              </div>}
              {!!cited.length && <div className="ngr-section">
                <h5>References</h5>
                <div className="ngr-references">{cited.map(source => <Reference key={source.source_id} source={source} />)}</div>
              </div>}
              {!cited.length && <p className="ngr-status">No source citations were provided for this explanation.</p>}
            </>
          )}
        </section>
      )}
    </div>
  );
}
