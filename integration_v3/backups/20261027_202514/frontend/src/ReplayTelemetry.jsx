import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart,
         ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const numeric = (value, digits = 1) => Number.isFinite(value)
  ? Number(value).toLocaleString(undefined, { maximumFractionDigits: digits }) : "—";

export default function ReplayTelemetry({ telemetry }) {
  if (!telemetry) return (
    <section className="ng-data-shell"><h3>Network telemetry</h3>
      <p>Select a replay window above to load its corresponding network features and model risk scores.</p>
    </section>
  );
  const s = telemetry.summary;
  const fwd = telemetry.packet_direction_breakdown;
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
          <p>Stacked LSTM predictions on up to nine recent decision windows from the same episode.</p>
          <div className="ng-chart-height ng-compact-chart"><ResponsiveContainer width="100%" height="100%">
            <BarChart data={telemetry.h10_risk_history}><XAxis dataKey="episode_minute" tick={{fontSize:10}} tickFormatter={v=>`m${v}`}/>
              <YAxis domain={[0,100]} tick={{fontSize:10}} width={35}/><Tooltip formatter={v=>`${numeric(v)}%`}/>
              <Bar name="H10 model output" dataKey="h10_model_score_percent" fill="#e56a72" radius={[4,4,0,0]}/>
            </BarChart>
          </ResponsiveContainer></div>
          <p className="ng-chart-summary">Latest H10: <strong>{numeric(telemetry.h10_risk_history.at(-1)?.h10_model_score_percent)}%</strong></p>
        </div>
      </div>
      <p className="ng-telemetry-footnote">These are real calculations from a <strong>synthetic</strong> validation sample. No packet sensor, protocol classification, calibrated alert threshold, or live network monitoring is connected.</p>
    </section>
  );
}
