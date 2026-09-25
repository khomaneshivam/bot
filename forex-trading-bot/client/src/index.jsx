/**
 * QuantAI Autonomous Forex & Crypto Terminal
 * DOM Mounting Point - React 18 & Tailwind CSS
 */

import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";
import "../public/css/style.css";

const rootElement = document.getElementById("root");
if (rootElement) {
  const root = ReactDOM.createRoot(rootElement);
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
}
