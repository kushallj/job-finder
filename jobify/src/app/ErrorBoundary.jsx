import { Component } from "react";

/** Catches render errors so one broken page does not blank the whole app. */
export default class ErrorBoundary extends Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(error, info) {
    // Hook for Sentry: Sentry.captureException(error, { extra: info })
    if (!import.meta.env.PROD) console.error(error, info);
  }
  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div role="alert" className="min-h-screen flex flex-col items-center justify-center gap-3 p-6 text-center">
        <h1 className="text-xl font-semibold">Something went wrong</h1>
        <p className="text-sm text-neutral-600">Please reload the page. If it keeps happening, contact support.</p>
        <button className="rounded-full bg-black px-4 py-2 text-sm text-white" onClick={() => location.reload()}>Reload</button>
      </div>
    );
  }
}
