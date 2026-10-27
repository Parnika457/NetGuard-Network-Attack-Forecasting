import { useEffect, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import "./liveTrafficPanel.css";

const fmt = (v, digits = 1) => Number.isFinite(v)
  ? Number(v).toLocaleString(undefined, { maximumFractionDigits: digits }) : "—";
const mib = v => Number.isFinite(v) ? v / (1024 * 1024) : null;

export default function LiveTrafficPanel({ enabled }) {
  const [interfaces, setInterfaces] = useState([]);
  const [selected, setSelected] = useState("");
  const [last, setLast] = useState(null);
  const [series, setSeries] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/live/interfaces", { signal: controller.signal })
      .then(async r => { if (!r.ok) throw new Error(`Live interface API HTTP ${r.status}`); return r.json(); })
      .then(data => { setInterfaces(data.interfaces || []); setSelected(data.default_interface || ""); })
      .catch(e => { if (e.name !== "AbortError") setError(e.message); });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    setSeries([]);
    setLast(null);
  }, [selected]);

  useEffect(() => {
    if (!enabled || !selected) return;
    let active = true;
    let busy = false;
    let tick = 0;
    const poll = async () => {
      if (busy) return;
      busy = true;
      try {
        const response = await fetch(`/api/live/metrics?interface=${encodeURIComponent(selected)}`, { cache: "no-store" });
        if (!response.ok) {
          const details = await response.json().catch(() => ({}));
          throw new Error(details.detail || `Live metrics HTTP ${response.status}`);
        }
        const payload = await response.json();
        if (!active) return;
        setError("");
        setLast(payload);
        if (payload.sampling_ready && payload.rates) {
          tick += 1;
          const timeLabel = new Date(payload.timestamp_utc).toLocaleTimeString();
          setSeries(old => [...old, {
            key: tick, time: timeLabel,
            received: mib(payload.rates.inbound_bytes_per_second),
            sent: mib(payload.rates.outbound_bytes_per_second),
          }].slice(-30));
        }
      } catch (e) { if (active) setError(e.message); }
      finally { busy = false; }
    };
    poll();
    const id = setInterval(poll, 1500);
    return () => { active = false; clearInterval(id); };
  }, [enabled, selected]);

  const rates = last?.rates;
  return <section className="ng-data-shell" aria-label="Live host network telemetry">
    <div className="ng-section-header">
      <div>
        <span className="subheading">LIVE TRAFFIC · COUNTERS ONLY</span>
        <h3>Mac network activity</h3>
      </div>
      <span className={`ng-live-status ${enabled ? "active" : ""}`}>{enabled ? "SAMPLING ON" : "PAUSED"}</span>
    </div>
    <label className="ng-interface-select">Network interface
      <select value={selected} onChange={e=>setSelected(e.target.value)} disabled={enabled}>
        {!selected && <option value="">No active interface found</option>}
        {interfaces.map(name=><option key={name} value={name}>{name}</option>)}
      </select>
    </label>
    {error && <p className="ng-live-error" role="alert">{error}</p>}
    {enabled && !rates && <p>Collecting baseline counters. Rates appear after the next sample.</p>}
    <div className="network-metrics">
      <div className="network-metric"><span>DOWNLOAD</span><strong>{fmt(mib(rates?.inbound_bytes_per_second), 3)} MiB/s</strong></div>
      <div className="network-metric"><span>UPLOAD</span><strong>{fmt(mib(rates?.outbound_bytes_per_second), 3)} MiB/s</strong></div>
      <div className="network-metric"><span>RECEIVE PACKETS / SEC</span><strong>{fmt(rates?.inbound_packets_per_second)}</strong></div>
      <div className="network-metric"><span>SEND PACKETS / SEC</span><strong>{fmt(rates?.outbound_packets_per_second)}</strong></div>
    </div>
    <div className="ng-chart-card">
      <h4>Network throughput (MiB/s)</h4>
      <div className="ng-chart-height">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={series}>
            <CartesianGrid vertical={false} stroke="currentColor" opacity={0.08}/>
            <XAxis dataKey="time" tick={{fontSize:10}} minTickGap={24}/>
            <YAxis tick={{fontSize:10}} width={48}/>
            <Tooltip formatter={(v)=>`${fmt(v, 4)} MiB/s`}/>
            <Area dataKey="received" name="Download" type="monotone" stroke="#69d596" fill="#69d596" fillOpacity={0.12} strokeWidth={2} isAnimationActive={false}/>
            <Area dataKey="sent" name="Upload" type="monotone" stroke="#78aef5" fill="#78aef5" fillOpacity={0.12} strokeWidth={2} isAnimationActive={false}/>
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  </section>;
}
