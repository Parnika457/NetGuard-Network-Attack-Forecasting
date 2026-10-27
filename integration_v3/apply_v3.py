"""Apply a guarded, non-destructive NetGuard V3 patch to the installed V2 project.

Run from project root: python integration_v3/apply_v3.py
Original files are backed up. Does not change CSS supplied by the UI designer.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).resolve().parents[1]
app_path = ROOT / "frontend/src/App.jsx"
chart_path = ROOT / "frontend/src/ReplayTelemetry.jsx"
api_path = ROOT / "backend/app.py"


def replace_one(content, before, after, filename):
    count = content.count(before)
    if count != 1:
        raise RuntimeError(f"{filename}: expected exactly one matching V2 code block, found {count}. No files changed. Don't overwrite locally edited files.")
    return content.replace(before, after, 1)


def build_app(content):
    name = "frontend/src/App.jsx"
    if 'LIVE HOST TELEMETRY MODE (V3)' in content:
        return content
    content = replace_one(content,
        'import ReplayTelemetry from "./ReplayTelemetry.jsx";',
        'import ReplayTelemetry from "./ReplayTelemetry.jsx";\nimport LiveTrafficPanel from "./LiveTrafficPanel.jsx";\nimport "./liveTrafficPanel.css"; // LIVE HOST TELEMETRY MODE (V3)',name)
    content = replace_one(content,
        '  const [monitoring, setMonitoring] = useState(true);',
        '  const [monitoring, setMonitoring] = useState(true);\n  const [trafficMode, setTrafficMode] = useState("replay");',name)
    content = replace_one(content,
        '{monitoring ? "REPLAY ON" : "REPLAY PAUSED"}',
        '{trafficMode === "live" ? (monitoring ? "LIVE COUNTERS ON" : "LIVE PAUSED") : (monitoring ? "REPLAY ON" : "REPLAY PAUSED")}',name)
    before = '''              <p>
                Frozen-model forecasts on synthetic validation replay
              </p>

            </div>


            {/* Frozen-model replay predictions. No hardcoded countdown. */}
            <ModelReplayPanel enabled={monitoring} onReplay={setReplayData} />

            <ReplayTelemetry telemetry={replayData?.telemetry} />'''
    after = '''              <p>
                {trafficMode === "replay" ? "Frozen-model forecasts on synthetic validation replay" : "Actual host network interface counters · no live attack inference"}
              </p>

            </div>

            <div className="ng-mode-selector" role="group" aria-label="Traffic source">
              <button type="button" aria-pressed={trafficMode === "replay"} onClick={() => {
                setTrafficMode("replay"); setMonitoring(true);
              }}>Synthetic model replay</button>
              <button type="button" aria-pressed={trafficMode === "live"} onClick={() => {
                setTrafficMode("live"); setMonitoring(false);
              }}>Live Mac traffic</button>
              <p>Replay runs frozen models on simulated data. Live reads host traffic counters only; start it with the status switch.</p>
            </div>

            {trafficMode === "replay" ? <>
              <ModelReplayPanel enabled={monitoring} onReplay={setReplayData} />
              <ReplayTelemetry telemetry={replayData?.telemetry} />
            </> : <LiveTrafficPanel enabled={monitoring} />}'''
    content = replace_one(content,before,after,name)
    content = replace_one(content,
        '''                    Replay Controls''',
        '''                    {trafficMode === "replay" ? "Replay Controls" : "Live Sampling"}''',name)
    content = replace_one(content,
        '''                    Enable replay forecast requests (not live monitoring)''',
        '''                    {trafficMode === "replay" ? "Enable synthetic replay requests" : "Sample this Mac's host interface counters (no model inference)"}''',name)
    return content


def build_chart(content):
    name = "frontend/src/ReplayTelemetry.jsx"
    if 'H10 PRECISION FIX V3' in content:
        return content
    content = replace_one(content,
        'import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart,',
        'import { Area, AreaChart, Line, LineChart, CartesianGrid, Cell, Pie, PieChart,',name)
    content = replace_one(content,
        '''const numeric = (value, digits = 1) => Number.isFinite(value)
  ? Number(value).toLocaleString(undefined, { maximumFractionDigits: digits }) : "—";''',
        '''const numeric = (value, digits = 1) => Number.isFinite(value)
  ? Number(value).toLocaleString(undefined, { maximumFractionDigits: digits }) : "—";

// H10 PRECISION FIX V3: preserve tiny nonzero risk values.
const riskPercent = v => {
  if (!Number.isFinite(v)) return "N/A";
  if (v === 0) return "0%";
  if (v > 0 && v < 0.001) return "<0.001%";
  return `${v < 1 ? v.toFixed(3) : v.toFixed(1)}%`;
};''',name)
    content = replace_one(content,
        '''  const fwd = telemetry.packet_direction_breakdown;
  return (''',
        '''  const fwd = telemetry.packet_direction_breakdown;
  const h10Points = telemetry.h10_risk_history || [];
  const h10Max = Math.max(0, ...h10Points.map(d => d.h10_model_score_percent || 0));
  const h10Upper = h10Max > 0 ? Math.min(100, h10Max * 1.2) : 1;
  return (''',name)
    before = '''        <div className="ng-chart-card"><h4>H10 forecast score history</h4>
          <p>Stacked LSTM predictions on up to nine recent decision windows from the same episode.</p>
          <div className="ng-chart-height ng-compact-chart"><ResponsiveContainer width="100%" height="100%">
            <BarChart data={telemetry.h10_risk_history}><XAxis dataKey="episode_minute" tick={{fontSize:10}} tickFormatter={v=>`m${v}`}/>
              <YAxis domain={[0,100]} tick={{fontSize:10}} width={35}/><Tooltip formatter={v=>`${numeric(v)}%`}/>
              <Bar name="H10 model output" dataKey="h10_model_score_percent" fill="#e56a72" radius={[4,4,0,0]}/>
            </BarChart>
          </ResponsiveContainer></div>
          <p className="ng-chart-summary">Latest H10: <strong>{numeric(telemetry.h10_risk_history.at(-1)?.h10_model_score_percent)}%</strong></p>
        </div>'''
    after = '''        <div className="ng-chart-card"><h4>H10 forecast score history</h4>
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
        </div>'''
    content = replace_one(content,before,after,name)
    return content


def build_api(content):
    name = "backend/app.py"
    if 'LIVE HOST TELEMETRY MODE (V3)' in content:
        return content
    content = replace_one(content,
        'from replay_telemetry import extract_telemetry, build_risk_history',
        'from replay_telemetry import extract_telemetry, build_risk_history\nfrom live_telemetry import available_interfaces, read_interface  # LIVE HOST TELEMETRY MODE (V3)',name)
    return content + '''

@api.get("/api/live/interfaces")
def live_interfaces():
    """List active host interfaces; no packet capture or model inference."""
    return available_interfaces()


@api.get("/api/live/metrics")
def live_metrics(interface: str | None = Query(default=None)):
    """Read the OS network interface counters from the API host."""
    try:
        return read_interface(interface)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
'''


def main():
    for path in (app_path,chart_path,api_path):
        if not path.is_file():
            raise RuntimeError(f"Missing {path}. Apply the Monitor + History V2 kit before V3.")
    if not (ROOT / 'frontend/src/LiveTrafficPanel.jsx').is_file() or not (ROOT / 'backend/live_telemetry.py').is_file():
        raise RuntimeError("Extract entire V3 kit into the project root first")

    originals={app_path:app_path.read_text(), chart_path:chart_path.read_text(), api_path:api_path.read_text()}
    updated={app_path:build_app(originals[app_path]), chart_path:build_chart(originals[chart_path]), api_path:build_api(originals[api_path])}
    changed=[p for p in updated if updated[p]!=originals[p]]
    if not changed:
        print("[PASS] V3 integration already applied; no files changed")
        return
    backup_dir=ROOT/'integration_v3/backups'/datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir.mkdir(parents=True,exist_ok=True)
    for path in changed:
        rel=path.relative_to(ROOT)
        dest=backup_dir/rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,dest)
    for path in changed:
        path.write_text(updated[path])
        print(f"[UPDATED] {path.relative_to(ROOT)}")
    print(f"[BACKUP] {backup_dir.relative_to(ROOT)}")
    print("[INFO] Existing index.css, page styles, model checkpoints, validation files and SQLite history were NOT modified")
    print("[NEXT] Install psutil, restart FastAPI and Vite, choose a mode on the Monitor page")


if __name__ == '__main__':
    main()
