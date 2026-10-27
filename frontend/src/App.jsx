import { useEffect, useRef, useState } from "react";
import { attackDictionary } from "./data/mockData";

import "./index.css";
import ModelReplayPanel from "./ModelReplayPanel.jsx";
import ReplayTelemetry from "./ReplayTelemetry.jsx";
import LiveTrafficPanel from "./LiveTrafficPanel.jsx";
import "./liveTrafficPanel.css"; // LIVE HOST TELEMETRY MODE (V3)
import { HistoryView, HistoryReport } from "./HistoryView.jsx";
import "./replayTelemetry.css";
import "./settingsNotifications.css"; // NETGUARD_SETTINGS_V4
import "./monitorPolish.css";



const alertLevel = probability => probability >= 0.85 ? "CRITICAL"
  : probability >= 0.60 ? "HIGH" : probability >= 0.30 ? "MEDIUM" : "LOW";
const alertMatches = (probability, sensitivity) => {
  if (!Number.isFinite(probability)) return false;
  return sensitivity === "all" ||
    (sensitivity === "medium" && probability >= 0.30) ||
    (sensitivity === "high" && probability >= 0.60) ||
    (sensitivity === "critical" && probability >= 0.85);
};
const alertPercent = probability => {
  const value = probability * 100;
  if (value > 0 && value < 0.001) return "<0.001%";
  if (value < 0.1) return `${value.toFixed(3)}%`;
  if (value < 1) return `${value.toFixed(2)}%`;
  return `${value.toFixed(1)}%`;
};
const preference = (key, fallback) => {
  try { const saved = window.localStorage.getItem(`netguard:${key}`); return saved == null ? fallback : JSON.parse(saved); }
  catch { return fallback; }
};

function App() {
  const [activePage, setActivePage] = useState("monitor");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [authMode, setAuthMode] = useState("login");
  const [replayEnabled, setReplayEnabled] = useState(() => preference("replayEnabled", true));
  const [liveSampling, setLiveSampling] = useState(false);
  const [trafficMode, setTrafficMode] = useState("replay");
  const [notificationsEnabled, setNotificationsEnabled] = useState(() => preference("notifications", false));
  const [desktopNotifications, setDesktopNotifications] = useState(() => preference("desktopNotifications", false));
  const [notificationPermission, setNotificationPermission] = useState(() =>
    typeof window.Notification === "undefined" ? "unsupported" : window.Notification.permission);
  const [lastAlert, setLastAlert] = useState(null);
  const [alertsShown, setAlertsShown] = useState(0);
  const seenReplayRef = useRef(new Set());
  const [backendStatus, setBackendStatus] = useState("checking");
  const [darkMode, setDarkMode] = useState(true);
  const [sensitivity, setSensitivity] = useState(() => preference("sensitivity", "medium"));
  const monitoring = trafficMode === "replay" ? replayEnabled : liveSampling;
  const [selectedAttack, setSelectedAttack] = useState(null);
  const [replayData, setReplayData] = useState(null);
  const [selectedDictionaryAttack, setSelectedDictionaryAttack] =
    useState(null);

  useEffect(() => {
    try {
      window.localStorage.setItem("netguard:replayEnabled", JSON.stringify(replayEnabled));
      window.localStorage.setItem("netguard:notifications", JSON.stringify(notificationsEnabled));
      window.localStorage.setItem("netguard:desktopNotifications", JSON.stringify(desktopNotifications));
      window.localStorage.setItem("netguard:sensitivity", JSON.stringify(sensitivity));
    } catch { /* Storage is optional. */ }
  }, [replayEnabled, notificationsEnabled, desktopNotifications, sensitivity]);

  // Poll the REAL FastAPI model-health endpoint even while the Settings page is open.
  // A running Vite frontend by itself MUST report DISCONNECTED.
  useEffect(() => {
    let active = true;
    let current = null;
    const poll = async () => {
      if (current) return; // Avoid overlapping health requests.
      const controller = new AbortController();
      current = controller;
      const timeout = setTimeout(() => controller.abort(), 2800);
      try {
        const response = await fetch("/api/health", { cache: "no-store", signal: controller.signal });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const payload = await response.json();
        if (payload.status !== "ok" || payload.models_loaded !== true) throw new Error("Models unavailable");
        if (active) setBackendStatus("connected");
      } catch {
        if (active) setBackendStatus("disconnected");
      } finally {
        clearTimeout(timeout);
        if (current === controller) current = null;
      }
    };
    poll();
    const interval = setInterval(poll, 5000);
    return () => { active = false; clearInterval(interval); current?.abort(); };
  }, []);

  useEffect(() => {
    if (backendStatus !== "connected") setReplayData(null);
  }, [backendStatus]);

  const handleReplayResult = (payload) => {
    setReplayData(payload);
    if (!payload || !notificationsEnabled || !replayEnabled || trafficMode !== "replay") return;
    const h10 = payload.forecast?.h10;
    if (!alertMatches(h10, sensitivity)) return;
    const key = String(payload.history?.id ?? `window-${payload.index}`);
    if (seenReplayRef.current.has(key)) return;
    seenReplayRef.current.add(key);
    if (seenReplayRef.current.size > 500) seenReplayRef.current.clear();
    const level = alertLevel(h10);
    const score = alertPercent(h10);
    const family = payload.family_eta?.family_if_onset?.replaceAll("_", " / ") || "Unknown family";
    setLastAlert({ id: key, level, score, family, index: payload.index });
    setAlertsShown(n => n + 1);
    if (desktopNotifications && typeof window.Notification !== "undefined" && window.Notification.permission === "granted") {
      try {
        new window.Notification(`NetGuard · ${level} forecast`, {
          body: `H10 ${score} · ${family} if onset · Replay window ${payload.index + 1}`,
          tag: `netguard-replay-${key}`,
        });
      } catch { /* The in-app notification remains available. */ }
    }
  };

  useEffect(() => {
    if (!lastAlert) return;
    const timer = setTimeout(() => {
      setLastAlert(current => current?.id === lastAlert.id ? null : current);
    }, 7000);
    return () => clearTimeout(timer);
  }, [lastAlert]);

  const enableDesktopAlerts = async () => {
    if (typeof window.Notification === "undefined") { setNotificationPermission("unsupported"); return; }
    const permission = await window.Notification.requestPermission();
    setNotificationPermission(permission);
    setDesktopNotifications(permission === "granted");
  };

  const themeClass = darkMode ? "dark-theme" : "light-theme";


  return (
    <div className={`app ${themeClass} ${sidebarOpen ? "sidebar-is-open" : "sidebar-is-closed"}`}>

      {/* ================= HEADER ================= */}

      <header className="header">

        <div className="header-left">

          <button
            className="menu-toggle"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-label="Toggle navigation"
          >
            ☰
          </button>

          <div className="brand">

            <div className="brand-icon">
              ◉
            </div>

            <div>
              <h1>NetGuard</h1>

              <span>
                Network Attack Forecasting
              </span>
            </div>

          </div>

        </div>


        <button
          className={`status ${
            monitoring ? "active" : "inactive"
          }`}
          onClick={() => {
            if (trafficMode === "replay") setReplayEnabled(v => !v);
            else setLiveSampling(v => !v);
          }}
        >

          <span className="status-dot"></span>

          {trafficMode === "live" ? (liveSampling ? "LIVE COUNTERS ON" : "LIVE PAUSED") : (replayEnabled ? "REPLAY ON" : "REPLAY OFF")}

        </button>

      </header>

      {notificationsEnabled && lastAlert && (
        <div className={`ng-forecast-toast ng-level-${lastAlert.level.toLowerCase()}`} role="status" aria-live="polite">
          <span className="ng-toast-icon" aria-hidden="true">◉</span>
          <div className="ng-toast-content">
            <div className="ng-toast-heading">
              <strong>{lastAlert.level === "LOW" ? "Low forecast score" : `${lastAlert.level} forecast risk`}</strong>
              <span>Replay #{lastAlert.index + 1}</span>
            </div>
            <p>H10 <strong>{lastAlert.score}</strong> · {lastAlert.family} if onset</p>
          </div>
          <button type="button" onClick={() => setLastAlert(null)} aria-label="Dismiss notification">×</button>
        </div>
      )}

      {/* =====================================================
            SIDEBAR NAVIGATION
        ===================================================== */}

        <aside className={`sidebar ${sidebarOpen ? "open" : ""}`}>

          <div className="sidebar-top">

            <button
              className={`sidebar-item ${
                activePage === "monitor" ? "selected" : ""
              }`}
              onClick={() => {
                setActivePage("monitor");
              }}
            >
              <span>◉</span>
              <label>Monitor</label>
            </button>


            <button
              className={`sidebar-item ${
                activePage === "history" ||
                activePage === "report"
                  ? "selected"
                  : ""
              }`}
              onClick={() => {
                setActivePage("history");
              }}
            >
              <span>◷</span>
              <label>History</label>
            </button>


            <button
              className={`sidebar-item ${
                activePage === "dictionary" ||
                activePage === "dictionary-detail"
                  ? "selected"
                  : ""
              }`}
              onClick={() => {
                setActivePage("dictionary");
              }}
            >
              <span>▣</span>
              <label>Attack Dictionary</label>
            </button>


            <button
              className={`sidebar-item ${
                activePage === "system"
                  ? "selected"
                  : ""
              }`}
              onClick={() => {
                setActivePage("system");
              }}
            >
              <span>⚙</span>
              <label>Settings</label>
            </button>

          </div>


          <div className="sidebar-bottom">

            <button
              className={`sidebar-item login-item ${
                activePage === "login" ? "selected" : ""
              }`}
              onClick={() => {
                setActivePage("login");
              }}
            >
              <span>♙</span>
              <label>Login</label>
            </button>

          </div>

        </aside>

                    


      {/* ================= CONTENT ================= */}

      <main className="content">


        {/* =====================================================
            MONITOR
        ===================================================== */}

        {activePage === "monitor" && (

          <div>

            <div className="page-heading">

              <h2>Network Monitor</h2>

              {trafficMode === "live" && <p>Host network traffic</p>}

            </div>

            <div className="ng-mode-selector" role="group" aria-label="Traffic source">
              <button type="button" aria-pressed={trafficMode === "replay"} disabled={!replayEnabled}
                onClick={() => { setTrafficMode("replay"); setLiveSampling(false); }}>Synthetic model replay</button>
              <button type="button" aria-pressed={trafficMode === "live"}
                onClick={() => { setTrafficMode("live"); setLiveSampling(false); }}>Live Mac traffic</button>
              {!replayEnabled && <p role="status">Replay is disabled in Settings. Re-enable it before making replay requests.</p>}
            </div>

            {trafficMode === "replay" ? <>
              <ModelReplayPanel enabled={replayEnabled && backendStatus === "connected"}
                backendStatus={backendStatus} replayEnabled={replayEnabled} onReplay={handleReplayResult} />
              <ReplayTelemetry telemetry={replayEnabled && backendStatus === "connected" ? replayData?.telemetry : null} />
            </> : <LiveTrafficPanel enabled={liveSampling && backendStatus === "connected"} />}

          </div>

        )}


        {/* =====================================================
            HISTORY
        ===================================================== */}

        {activePage === "history" && (
          <HistoryView onSelect={(event) => {
            setSelectedAttack(event);
            setActivePage("report");
          }} />
        )}

        {activePage === "report" && selectedAttack && (
          <HistoryReport event={selectedAttack} onBack={() => {
            setSelectedAttack(null);
            setActivePage("history");
          }} />
        )}

        {/* =====================================================
            DICTIONARY
        ===================================================== */}

        {activePage === "dictionary" && (

          <div>

            <div className="page-heading">

              <div className="dictionary-heading">

                <div className="book-icon">
                  ▣
                </div>

                <div>

                  <h2>
                    Attack Dictionary
                  </h2>

                  <p>
                    Understand common network threats
                  </p>

                </div>

              </div>

            </div>


            <div className="dictionary-grid">

              {attackDictionary.map((attack) => (

                <button
                  className="dictionary-card"
                  key={attack.type}
                  onClick={() => {
                    setSelectedDictionaryAttack(attack);
                    setActivePage("dictionary-detail");
                  }}
                >

                  <div className="dictionary-icon">
                    {attack.icon}
                  </div>

                  <span className="dictionary-category">
                    {attack.category}
                  </span>

                  <h3>
                    {attack.type}
                  </h3>

                  <p>
                    {attack.description}
                  </p>

                  <span className="view-details">
                    View details →
                  </span>

                </button>

              ))}

            </div>

          </div>

        )}


        {/* =====================================================
            DICTIONARY DETAIL
        ===================================================== */}

        {activePage === "dictionary-detail" &&
          selectedDictionaryAttack && (

            <div>

              <button
                className="back-button"
                onClick={() => {
                  setSelectedDictionaryAttack(null);
                  setActivePage("dictionary");
                }}
              >
                ← Back to Dictionary
              </button>


              <div className="page-heading">

                <span className="dictionary-category">
                  {selectedDictionaryAttack.category}
                </span>

                <h2>
                  {selectedDictionaryAttack.type}
                </h2>

                <p>
                  {selectedDictionaryAttack.description}
                </p>

              </div>


              <section className="card dictionary-detail">

                <div className="detail-section">

                  <span className="subheading">
                    COMMON INDICATORS
                  </span>

                  {selectedDictionaryAttack.indicators.map(
                    (indicator) => (

                      <div
                        className="detail-row"
                        key={indicator}
                      >
                        <span>•</span>
                        {indicator}
                      </div>

                    )
                  )}

                </div>


                <div className="detail-section">

                  <span className="subheading">
                    POSSIBLE DEFENSES
                  </span>

                  {selectedDictionaryAttack.defenses.map(
                    (defense) => (

                      <div
                        className="detail-row"
                        key={defense}
                      >
                        <span>✓</span>
                        {defense}
                      </div>

                    )
                  )}

                </div>

              </section>

            </div>

          )}
          {/* =====================================================
            LOGIN
        ===================================================== */}

        
        {activePage === "login" && (

          <div className="auth-page">

            <div className="auth-card">

              <div className="auth-logo">
                ◉
              </div>

              {authMode === "login" ? (

                <>
                  <h2>Welcome back</h2>

                  <p className="auth-subtitle">
                    Sign in to access your NetGuard dashboard.
                  </p>

                  <form
                    className="auth-form"
                    onSubmit={(e) => e.preventDefault()}
                  >

                    <label>Email</label>

                    <input
                      type="email"
                      placeholder="Enter your email"
                    />

                    <label>Password</label>

                    <input
                      type="password"
                      placeholder="Enter your password"
                    />

                    <button
                      type="submit"
                      className="auth-submit"
                    >
                      Sign In
                    </button>

                  </form>

                  <div className="auth-switch">

                    <span>
                      Don't have an account?
                    </span>

                    <button
                      onClick={() => setAuthMode("signup")}
                    >
                      Create one
                    </button>

                  </div>
                </>

              ) : (

                <>
                  <h2>Create your account</h2>

                  <p className="auth-subtitle">
                    Set up your NetGuard security profile.
                  </p>

                  <form
                    className="auth-form"
                    onSubmit={(e) => e.preventDefault()}
                  >

                    <label>Name</label>

                    <input
                      type="text"
                      placeholder="Enter your name"
                    />

                    <label>Email</label>

                    <input
                      type="email"
                      placeholder="Enter your email"
                    />

                    <label>Password</label>

                    <input
                      type="password"
                      placeholder="Create a password"
                    />

                    <label>Confirm Password</label>

                    <input
                      type="password"
                      placeholder="Confirm your password"
                    />

                    <button
                      type="submit"
                      className="auth-submit"
                    >
                      Create Account
                    </button>

                  </form>

                  <div className="auth-switch">

                    <span>
                      Already have an account?
                    </span>

                    <button
                      onClick={() => setAuthMode("login")}
                    >
                      Sign in
                    </button>

                  </div>
                </>

              )}

              <div className="auth-demo-note">
                Authentication will be connected to FastAPI later.
              </div>

            </div>

          </div>

        )}

        {/* =====================================================
            SETTINGS
        ===================================================== */}

        {activePage === "system" && (

          <div>

            <div className="page-heading">

              <h2>
                Settings
              </h2>

              <p>
                Configure how NetGuard behaves
              </p>

            </div>


            <section className="card settings-card">

              {/* Monitoring */}

              <div className="setting">

                <div>

                  <strong>
                    Replay Controls
                  </strong>

                  <span>
                    Allow synthetic validation replay requests; turning this off blocks replay inference requests
                  </span>

                </div>

                <button
                  type="button"
                  role="switch" aria-label="Enable replay"
                  aria-checked={replayEnabled}
                  className={`toggle ${replayEnabled ? "on" : ""}`}
                  onClick={() => {
                    setReplayEnabled(v => !v);
                    setReplayData(null);
                    setLastAlert(null);
                    if (trafficMode === "replay") setLiveSampling(false);
                  }}
                >
                  <span />
                </button>

              </div>


              {/* Notifications */}

              <div className="setting">

                <div>

                  <strong>
                    Threat Notifications
                  </strong>

                  <span>
                    Display alerts when synthetic replay H10 meets your chosen sensitivity. No live-traffic alerts yet.
                  </span>

                </div>

                <button type="button" role="switch" aria-label="Enable threat notifications"
                  aria-checked={notificationsEnabled}
                  className={`toggle ${notificationsEnabled ? "on" : ""}`}
                  onClick={() => {
                    setNotificationsEnabled(v => !v);
                    setLastAlert(null);
                  }}>
                  <span />
                </button>

              </div>


              <div className="setting">
                <div><strong>Desktop Notifications</strong>
                  <span>Optional browser alert while this dashboard is open (requires permission).</span></div>
                <button type="button" className="ng-secondary-button"
                  disabled={!notificationsEnabled || (notificationPermission === "denied")}
                  onClick={() => {
                    if (desktopNotifications) setDesktopNotifications(false);
                    else enableDesktopAlerts();
                  }}>
                  {desktopNotifications && notificationPermission === "granted" ? "DESKTOP ON" : notificationPermission === "denied" ? "BLOCKED IN BROWSER" : "ENABLE DESKTOP"}
                </button>
              </div>

              {/* Theme */}

              <div className="setting">

                <div>

                  <strong>
                    Dark Mode
                  </strong>

                  <span>
                    Switch between light and dark appearance
                  </span>

                </div>

                <button
                  className={`toggle ${
                    darkMode ? "on" : ""
                  }`}
                  onClick={() =>
                    setDarkMode(!darkMode)
                  }
                >
                  <span />
                </button>

              </div>


              {/* Sensitivity */}

              <div className="sensitivity-setting">

                <div>

                  <strong>
                    Threat Sensitivity
                  </strong>

                  <span>
                    Filter replay alerts using H10 probability (unvalidated demo bands, not security thresholds).
                  </span>

                </div>


                <div className="sensitivity-options">

                  {[
                    ["critical", "Critical only"],
                    ["high", "High & Critical"],
                    ["medium", "Medium & above"],
                    ["all", "All activity"],
                  ].map(([value, label]) => (

                    <button
                      key={value}
                      className={
                        sensitivity === value
                          ? "selected"
                          : ""
                      }
                      type="button"
                      aria-pressed={sensitivity === value}
                      onClick={() => setSensitivity(value)}
                    >
                      {label}
                    </button>

                  ))}

                </div>
                <p className="ng-setting-help">
                  LOW: below 30% · MEDIUM: 30–59.99% · HIGH: 60–84.99% · CRITICAL: 85% or above.
                  "All activity" alerts on each newly processed replay window, even at very low probability.
                  These cutoffs are for demonstrating notification filtering only.
                </p>
                <p className="ng-setting-help" role="status">In-page notifications {notificationsEnabled ? "ON" : "OFF"} · {alertsShown} alert(s) this session</p>
              </div>


              {/* Defense */}

              <div className="setting">

                <div>

                  <strong>
                    Defense Mode
                  </strong>

                  <span>
                    Not implemented. No firewall or network changes will be performed.
                  </span>

                </div>

                <button type="button" className="toggle" disabled aria-label="Defense mode unavailable" aria-checked={false} role="switch">
                  <span />
                </button>

              </div>


              {/* Status */}

              <div className="setting">

                <div>

                  <strong>
                    Backend Status
                  </strong>

                  <span>
                    Health check to FastAPI /api/health every 5 seconds; reports disconnected when only React is running.
                  </span>

                </div>

                <span className={`ng-backend-badge ${backendStatus === "connected" ? "connected" : ""}`} role="status" aria-live="polite">
                  {backendStatus === "connected" ? "CONNECTED" : backendStatus === "checking" ? "CHECKING…" : "DISCONNECTED"}
                </span>

              </div>

            </section>

          </div>

        )}

      </main>

    </div>

    

  );
}


export default App;