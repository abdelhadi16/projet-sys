// One line in the live key-event feed: time, key name + character, modifiers,
// the focused process, and the verdict badge.
import { displayCharacter, formatModifiers, formatTime } from "../lib/keyboard.js";

export default function EventRow({ log }) {
  const decoded = log.enriched_event.decoded;
  const context = log.enriched_event.context;
  const verdict = log.verdict;

  const isPress = decoded.raw.event_type === "PRESS";
  const mods = formatModifiers(decoded.modifiers);
  const char = displayCharacter(decoded.character);

  return (
    <div className={`event-row ${isPress ? "press" : "release"}`}>
      <span className="event-meta">{formatTime(decoded.raw.timestamp)}</span>

      <span className="event-main">
        <span className="event-key">{decoded.key_name}</span>
        {char && <span className="event-char"> {char}</span>}
        {mods && <span className="event-mods"> [{mods}]</span>}
        <span className="event-meta"> — {context.process_name || "?"}</span>
      </span>

      <span className={`badge verdict-${verdict.action}`}>{verdict.action}</span>
    </div>
  );
}
