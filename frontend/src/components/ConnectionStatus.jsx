// A coloured pill showing whether the backend is reachable. The dot colour is
// driven by CSS classes defined in theme.css.
export default function ConnectionStatus({ status, demo }) {
  // In demo mode we show a distinct label so nobody mistakes fake data for a
  // real backend connection.
  if (demo) {
    return (
      <span className="status demo" role="status">
        <span className="dot" />
        Demo mode (no backend)
      </span>
    );
  }

  const labels = {
    connected: "Connected",
    connecting: "Connecting…",
    disconnected: "Disconnected",
  };

  return (
    <span className={`status ${status}`} role="status">
      <span className="dot" />
      {labels[status] || status}
    </span>
  );
}
