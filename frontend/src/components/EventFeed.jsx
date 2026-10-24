// The scrolling list of recent key events, newest first.
import EventRow from "./EventRow.jsx";
import { eventKey } from "../lib/keyboard.js";

export default function EventFeed({ events }) {
  return (
    <section className="panel">
      <h2>Live key events</h2>
      <div className="feed">
        {events.length === 0 ? (
          <div className="empty">Waiting for keyboard events…</div>
        ) : (
          events.map((log) => <EventRow key={eventKey(log)} log={log} />)
        )}
      </div>
    </section>
  );
}
