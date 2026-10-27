import { useState } from "react";
import { attackDictionary } from "./data/mockData";

import "./index.css";
import ModelReplayPanel from "./ModelReplayPanel.jsx";
import ReplayTelemetry from "./ReplayTelemetry.jsx";
import { HistoryView, HistoryReport } from "./HistoryView.jsx";
import "./replayTelemetry.css";



function App() {
  const [activePage, setActivePage] = useState("monitor");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [authMode, setAuthMode] = useState("login");
  const [monitoring, setMonitoring] = useState(true);
  const [defenseMode, setDefenseMode] = useState(false);
  const [darkMode, setDarkMode] = useState(true);
  const [sensitivity, setSensitivity] = useState("medium");
  const [selectedAttack, setSelectedAttack] = useState(null);
  const [replayData, setReplayData] = useState(null);
  const [selectedDictionaryAttack, setSelectedDictionaryAttack] =
    useState(null);



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
          onClick={() => setMonitoring(!monitoring)}
        >

          <span className="status-dot"></span>

          {monitoring ? "REPLAY ON" : "REPLAY PAUSED"}

        </button>

      </header>

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

              <p>
                Frozen-model forecasts on synthetic validation replay
              </p>

            </div>


            {/* Frozen-model replay predictions. No hardcoded countdown. */}
            <ModelReplayPanel enabled={monitoring} onReplay={setReplayData} />

            <ReplayTelemetry telemetry={replayData?.telemetry} />

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
                    Enable replay forecast requests (not live monitoring)
                  </span>

                </div>

                <button
                  className={`toggle ${
                    monitoring ? "on" : ""
                  }`}
                  onClick={() =>
                    setMonitoring(!monitoring)
                  }
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
                    Receive alerts for relevant forecasts
                  </span>

                </div>

                <button className="toggle on">
                  <span />
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
                    Choose which threat levels should
                    trigger attention
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
                      onClick={() =>
                        setSensitivity(value)
                      }
                    >
                      {label}
                    </button>

                  ))}

                </div>

              </div>


              {/* Defense */}

              <div className="setting">

                <div>

                  <strong>
                    Defense Mode
                  </strong>

                  <span>
                    Future automatic response capability
                  </span>

                </div>

                <button
                  className={`toggle ${
                    defenseMode ? "on" : ""
                  }`}
                  onClick={() =>
                    setDefenseMode(!defenseMode)
                  }
                >
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
                    Connection status is displayed on the Monitor page
                  </span>

                </div>

                <span className="connected">
                  SEE MONITOR
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