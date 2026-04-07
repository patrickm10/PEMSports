import React from "react";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("V3 Workspace Error Trace:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-fallback">
          <h2>Something went wrong in the Analysis Grid.</h2>
          <p>{this.state.error?.message || "Unknown rendering failure"}</p>
          <button 
            onClick={() => {
              window.location.hash = ""; // Clear hash which often contains the malformed filter
              window.location.reload();
            }}
            className="reset-btn"
          >
            Reset Workspace & Reload
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
