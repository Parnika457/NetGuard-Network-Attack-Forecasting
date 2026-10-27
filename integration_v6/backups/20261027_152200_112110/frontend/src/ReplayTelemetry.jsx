import { Area, AreaChart, Line, LineChart, CartesianGrid, Cell, Pie, PieChart,
         ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const numeric = (value, digits = 1) => Number.isFinite(value)
  ? Number(value).toLocaleString(undefined, { maximumFractionDigits: digits }) : "—";

// H10 PRECISION FIX V3: preserve tiny nonzero risk values.
const riskPercent = v => {
  if (!Number.isFinite(v)) return "N/A";
  if (v === 0) return "0%";
  if (v > 0 && v < 0.001) return "<0.001%";
  return `${v < 1 ? v.toFixed(3) : v.toFixed(1)}%`;
};

export default function ReplayTelemetry({ telemetry }) {
  if (!telemetry) return (
    <section className="ng-data-shell"><h3>Network telemetry</h3>
      <p>Select a replay window above to load its corresponding network features and model risk scores.</p>
    </section>
  );
  const s = telemetry.summary;
  const fwd = telemetry.packet_direction_breakdown;
  const h10Points = telemetry.h10_risk_history || [];
  const h10Max = Math.max(0, ...h10Points.map(d => d.h10_model_score_percent || 0));
  const h10Upper = h10Max > 0 ? Math.min(100, h10Max * 1.2) : 1;
  return (
    <section className="ng-data-shell" aria-label="Network telemetry from the selected synthetic replay window">
      <div className="ng-section-header"><div><span className="subheading">SYNTHETIC VALIDATION REPLAY</span>
        <h3>Network traffic features</h3><p>Minute {telemetry.minute} · values are sourced from the selected 10×14 window, not mock data.</p>
      </div></div>
      <div className="network-metrics">
        <div className="network-metric"><span>PACKETS / SEC</span><strong>{numeric(s.packets_per_second)}</strong><small>Model input: Packets_Per_Second</small></div>
        <div className="network-metric"><span>THROUGHPUT</span><strong>{numeric(s.throughput_kib_per_second)} KiB/s</strong><small>Model input: Bytes_Per_Second</small></div>
        <div className="network-metric"><span>FLOWS / MIN</span><strong>{numeric(s.flows_per_minute, 0)}</strong><small>Model input: Flow_Count</small></div>
        <div className="network-metric"><span>PACKETS / MIN</span><strong>{numeric(s.packets_per_minute, 0)}</strong><small>Model input: Total_Packets</small></div>
      </div>
      <div className="ng-chart-card"><h4>Forward / backward byte volume</h4>
        <p>Recorded simulation aggregates in MiB per minute (not measured live inbound/outbound traffic).</p>
        <div className="ng-chart-height"><ResponsiveContainer width="100%" height="100%">
          <AreaChart data={telemetry.traffic}><CartesianGrid stroke="currentColor" opacity={0.08} vertical={false}/>
            <XAxis dataKey="minute" tick={{fontSize:10}} tickFormatter={v=>`m${v}`}/>
            <YAxis tick={{fontSize:10}} width={38}/><Tooltip formatter={v=>`${numeric(v,3)} MiB/min`}/>
            <Area type="monotone" dataKey="forward_mib_per_minute" name="Forward" stroke="#69d596" fill="#69d596" fillOpacity={0.14} strokeWidth={2}/>
            <Area type="monotone" dataKey="backward_mib_per_minute" name="Backward" stroke="#78aef5" fill="#78aef5" fillOpacity={0.12} strokeWidth={2}/>
          </AreaChart>
        </ResponsiveContainer></div>
      </div>
      <div className="network-visual-grid">
        <div className="ng-chart-card"><h4>Packet direction composition</h4>
          <p>Derived from forward and backward packet totals; protocol percentages are unavailable.</p>
          <div className="ng-chart-height ng-compact-chart"><ResponsiveContainer width="100%" height="100%">
            <PieChart><Pie data={fwd} nameKey="name" dataKey="value" innerRadius={46} outerRadius={72}>
              <Cell fill="#69d596"/><Cell fill="#78aef5"/></Pie><Tooltip formatter={v=>`${numeric(v)}%`}/>
            </PieChart>
          </ResponsiveContainer></div>
          <div className="ng-legend">{fwd.map(d=><span key={d.name}>{d.name}: <strong>{numeric(d.value)}%</strong></span>)}</div>
        </div>
        <div className="ng-chart-card"><h4>H10 forecast score history</h4>
          <p>Stacked LSTM probabilities across up to nine decision windows in the same simulated episode. The vertical axis automatically zooms when all values are tiny.</p>
          <div className="ng-chart-height ng-compact-chart"><ResponsiveContainer width="100%" height="100%">
            <LineChart data={h10Points} margin={{top:8,right:10,left:8,bottom:4}}>
              <CartesianGrid vertical={false} stroke="currentColor" opacity={0.08}/>
              <XAxis dataKey="episode_minute" tick={{fontSize:10}} tickFormatter={v=>`m${v}`} minTickGap={10}/>
              <YAxis domain={[0,h10Upper]} tick={{fontSize:10}} width={55} tickFormatter={v => Number(v).toPrecision(2)}/>
              <Tooltip formatter={v=>[riskPercent(v), "H10 model probability"]} labelFormatter={v=>`Episode minute ${v}`}/>
              <Line name="H10 model probability" dataKey="h10_model_score_percent" type="monotone"
                stroke="#e56a72" strokeWidth={2.5} dot={{r:3.5,fill:"#e56a72"}} activeDot={{r:5}} isAnimationActive={false}/>
            </LineChart>
          </ResponsiveContainer></div>
          <p className="ng-chart-summary">Latest H10: <strong>{riskPercent(h10Points.at(-1)?.h10_model_score_percent)}</strong></p>
          <p className="ng-chart-note">{h10Points.length === 1 ? "Only one same-episode decision window is available; move to later windows to see a trend. " : ""}Auto-scaled Y-axis shows small changes but does not imply high risk. Hover over points for the actual percentage.</p>
        </div>
      </div>
      <p className="ng-telemetry-footnote">These are real calculations from a <strong>synthetic</strong> validation sample. No packet sensor, protocol classification, calibrated alert threshold, or live network monitoring is connected.</p>
    </section>
  );
}
