import { ClerkProvider } from "@clerk/react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import ErrorBoundary from "./app/ErrorBoundary.jsx";
import "./index.css";

// Ensure js class for progressive enhancement
if (typeof document !== "undefined") {
  document.documentElement.classList.add("js");
}

createRoot(document.getElementById("root")!).render(<ErrorBoundary>
    <ClerkProvider afterSignOutUrl="/">
      <App />
    </ClerkProvider>
  </ErrorBoundary>);