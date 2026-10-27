import { useEffect, useState } from "react";
import {
  Code2,
  Files,
  Package,
  Search,
  Settings,
  ShieldCheck,
  Terminal,
  X,
} from "lucide-react";
import "../codelab.css";

export function CodeLabDemo() {
  useEffect(() => {
    const previousTitle = document.title;
    document.title = "ReplayLab CodeLab";
    return () => {
      document.title = previousTitle;
    };
  }, []);
  const [view, setView] = useState<
    "welcome" | "market" | "details" | "installed" | "settings"
  >("welcome");
  const [query, setQuery] = useState("");
  const [version, setVersion] = useState("1.0");
  const [dialog, setDialog] = useState(false);
  const match = query.toLowerCase().trim() === "replay formatter";
  return (
    <div className="codelab">
      <div className="codelab-demo-strip">
        <ShieldCheck size={16} />
        <div>
          <strong>ReplayLab CodeLab</strong>
          <span>Interactive simulation · no actual software changes</span>
        </div>
        <button
          onClick={() => {
            setView("welcome");
            setQuery("");
            setDialog(false);
            setVersion("1.0");
          }}
        >
          Reset sandbox
        </button>
      </div>
      <header className="codelab-title">
        <Code2 size={18} />
        <strong>CodeLab {version}</strong>
        <span>practice-workspace</span>
        <div>
          <button
            onClick={() => setVersion((v) => (v === "1.0" ? "2.0" : "1.0"))}
          >
            Change UI version
          </button>
          <button onClick={() => setDialog(true)}>
            Show unexpected dialog
          </button>
        </div>
      </header>
      <div className="codelab-body">
        <nav aria-label="CodeLab navigation">
          <button
            onClick={() => setView("welcome")}
            className={view === "welcome" ? "selected" : ""}
          >
            <Files size={23} />
            <span>Explorer</span>
          </button>
          <button
            onClick={() => {
              setView("market");
              setQuery("");
            }}
            className={
              ["market", "details", "installed"].includes(view)
                ? "selected"
                : ""
            }
          >
            <Package size={23} />
            <span>Extensions</span>
          </button>
          <button
            onClick={() => setView("settings")}
            className={view === "settings" ? "selected" : ""}
          >
            <Settings size={23} />
            <span>Settings</span>
          </button>
        </nav>
        <main className="codelab-editor">
          {view === "welcome" && (
            <div className="codelab-welcome">
              <Code2 size={48} />
              <h1>Your next skill starts here.</h1>
              <p>A small, safe workspace for visual learning.</p>
              <div>
                <Terminal size={18} />
                <span>Open a panel from the sidebar to begin.</span>
              </div>
              <small>
                Follow the tutorial in ReplayLab. Changes here affect only this
                sandbox.
              </small>
            </div>
          )}
          {view === "market" && (
            <div>
              <div className="codelab-pane-title">
                <Package size={22} />
                <h1>{query ? "Search results" : "Extensions Marketplace"}</h1>
              </div>
              <label className="codelab-search">
                <Search size={19} />
                <input
                  aria-label="Search extensions"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Find a package by name"
                />
              </label>
              {match ? (
                <button
                  className="codelab-package"
                  onClick={() => setView("details")}
                >
                  <span className="codelab-package-logo">RF</span>
                  <div>
                    <h2>Replay Formatter</h2>
                    <p>A consistent style for your practice files.</p>
                    <small>ReplayLab · Sandbox package</small>
                  </div>
                  <span>View details →</span>
                </button>
              ) : query ? (
                <p className="codelab-no-results">
                  No matching package. Check the name in your tutorial.
                </p>
              ) : (
                <div className="codelab-market-empty">
                  <Package size={34} />
                  <h2>A space for your tools.</h2>
                  <p>Search for the package named in your tutorial.</p>
                </div>
              )}
            </div>
          )}
          {(view === "details" || view === "installed") && (
            <div>
              <div className="codelab-details-label">Extension details</div>
              <div className="codelab-package-heading">
                <span className="codelab-package-logo">RF</span>
                <div>
                  <h1>Replay Formatter</h1>
                  <p>Consistent formatting, one practice file at a time.</p>
                  <small>ReplayLab · Verified sandbox publisher</small>
                </div>
              </div>
              {view === "details" ? (
                <button
                  className="codelab-install"
                  onClick={() => setView("installed")}
                >
                  Install extension
                </button>
              ) : (
                <div className="codelab-installed">
                  <ShieldCheck size={20} />
                  <strong>Installed</strong>
                  <span>Enabled</span>
                </div>
              )}
              <div className="codelab-package-description">
                <h2>Simple tools. Clear results.</h2>
                <p>
                  This package demonstrates a visible installation workflow in a
                  controlled practice environment.
                </p>
                <p>
                  ReplayLab observes only the screen you choose to share. It
                  does not click buttons or install software for you.
                </p>
              </div>
            </div>
          )}
          {view === "settings" && (
            <div className="codelab-settings">
              <Settings size={30} />
              <h1>Settings</h1>
              <h2>Preferences</h2>
              <p>This is a different destination from the tutorial workflow.</p>
              <label>
                Editor theme
                <select>
                  <option>Midnight</option>
                  <option>Slate</option>
                </select>
              </label>
            </div>
          )}
        </main>
      </div>
      <footer className="codelab-status">
        <span>CodeLab {version}</span>
        <span>Local sandbox · Changes are simulated</span>
        <span>UTF-8</span>
      </footer>
      {dialog && (
        <div className="codelab-dialog-backdrop">
          <div role="dialog" aria-modal="true" aria-labelledby="codelab-error">
            <button
              aria-label="Close unexpected dialog"
              onClick={() => setDialog(false)}
            >
              <X size={18} />
            </button>
            <h2 id="codelab-error">Permission denied</h2>
            <p>
              This deliberately introduced dialog blocks the practice workflow.
              Dismiss it to recover.
            </p>
            <button
              className="codelab-install"
              onClick={() => setDialog(false)}
            >
              Dismiss dialog
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
