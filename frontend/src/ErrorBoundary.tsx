import { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";
export class ErrorBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Workbench rendering failed", error, info.componentStack);
  }
  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <main className="initial-loading">
        <img src="/mark.svg" alt="" width="42" height="42" />
        <h1>This view could not be opened</h1>
        <p role="alert">
          Your changes may not have been saved. Reload the workbench, then check
          the record before repeating an action.
        </p>
        <button
          className="button primary"
          onClick={() => window.location.reload()}
        >
          Reload workbench
        </button>
      </main>
    );
  }
}
