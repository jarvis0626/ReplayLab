import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import "@xyflow/react/dist/style.css";
import "./styles.css";
import "./digital.css";

const CodeLabDemo = React.lazy(() =>
  import("./pages/CodeLabDemo").then((module) => ({
    default: module.CodeLabDemo,
  })),
);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {new URLSearchParams(window.location.search).get("digital-demo") === "1" ? (
      <React.Suspense
        fallback={<div className="loading-panel">Loading CodeLab sandbox…</div>}
      >
        <CodeLabDemo />
      </React.Suspense>
    ) : (
      <App />
    )}
  </React.StrictMode>,
);
