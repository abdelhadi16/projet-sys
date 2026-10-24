"""
=============================================================================
  flusher.py (The Pipe)
=============================================================================

RÔLE EXACT
----------
Le callback (hook) tourne dans le chemin critique du clavier de Windows.
Il n'a droit qu'à des opérations ultra-rapides en mémoire.
Tout ce qui est lent (réseau, disque, attente) DOIT sortir du callback.

Lina est responsable de ce "tuyau de sortie" :

  1. Une queue thread-safe où le callback pousse les LogEntry (en dict)
  2. Un thread de fond (flusher) qui lit la queue et envoie à FastAPI
  3. Un fallback fichier si l'API est down ou absente
  4. Un arrêt propre qui vide la queue avant de quitter

INTÉGRATION AVEC LES AUTRES
---------------------------
  Kenza  (task2pt1)  → fournit LogEntry + .to_dict()
  Melissa (decode)   → fournit DecodedEvent + Context
  Mehdi  (hook)      → crée RawEvent, appelle decode + rules, puis push_event
  Lina               → transporte le résultat final hors du callback

API PUBLIQUE (ce que les autres appellent)
------------------------------------------
  from transport import event_queue, push_event, start_flusher, stop_flusher

  start_flusher(event_queue, api_url="http://127.0.0.1:8000/events")
  push_event(event_queue, log_entry.to_dict())   # dans le callback
  stop_flusher(event_queue)                      # dans le finally de main
=============================================================================
"""

from __future__ import annotations

import json
import queue
import threading
import time
from pathlib import Path
from typing import Any, Optional, Union

# ---------------------------------------------------------------------------
# 1. La file d'attente (Queue)
# ---------------------------------------------------------------------------
# queue.Queue est déjà thread-safe (plusieurs threads peuvent put/get
# en même temps sans Lock supplémentaire).
#
# maxsize=10000 : si le flusher est trop lent (API lente), on limite
# la consommation mémoire. Au-delà, push_event jette le plus ancien.

event_queue: queue.Queue = queue.Queue(maxsize=10000)

# Contrôle du thread flusher
_stop_event: Optional[threading.Event] = None
_flusher_thread: Optional[threading.Thread] = None

# Fichier de secours : une ligne = un événement JSON (format .jsonl)
FALLBACK_FILE = Path("events_fallback.jsonl")


# ---------------------------------------------------------------------------
# 2. push_event — appelée DEPUIS LE CALLBACK (doit rester < 1 ms)
# ---------------------------------------------------------------------------

def push_event(q: queue.Queue, event: Union[dict[str, Any], Any]) -> None:
    """
    Met un événement dans la queue, sans jamais bloquer.

    Accepte :
      - un dict déjà prêt (LogEntry.to_dict())
      - un objet LogEntry (on appelle .to_dict() automatiquement)

    Stratégie si la queue est pleine :
      - on retire le plus ancien événement
      - on remet le nouveau
    → on préfère perdre un vieux log plutôt que de figer le clavier.
    """
    # Si on reçoit un objet LogEntry (ou tout objet avec to_dict), on convertit
    if not isinstance(event, dict):
        if hasattr(event, "to_dict"):
            event = event.to_dict()
        else:
            return  # on ignore silencieusement un type inconnu

    try:
        q.put_nowait(event)
    except queue.Full:
        try:
            q.get_nowait()       # jette le plus ancien
            q.put_nowait(event)  # place le nouveau
        except queue.Empty:
            pass


# ---------------------------------------------------------------------------
# 3. Envoi vers l'API + fallback fichier
# ---------------------------------------------------------------------------

def _send_to_api(api_url: str, event: dict[str, Any]) -> bool:
    """
    POST JSON vers l'endpoint FastAPI de Kenza.
    Retourne True si HTTP 2xx, False en cas d'erreur ou timeout.

    On utilise urllib (stdlib) pour ne pas forcer l'installation de requests.
    """
    if not api_url:
        return False
    try:
        import urllib.request

        data = json.dumps(event, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            api_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return 200 <= getattr(resp, "status", 200) < 300
    except Exception:
        return False


def _write_fallback(event: dict[str, Any]) -> None:
    """
    Écrit une ligne JSON dans events_fallback.jsonl.
    Appelé uniquement quand l'API a échoué (ou n'existe pas encore).
    """
    try:
        with open(FALLBACK_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as exc:
        # On ne doit JAMAIS faire planter le flusher.
        print(f"[flusher] fallback write failed: {exc}")


# ---------------------------------------------------------------------------
# 4. Le worker (tourne dans son propre thread)
# ---------------------------------------------------------------------------

def _flusher_worker(
    q: queue.Queue,
    api_url: str,
    stop_event: threading.Event,
) -> None:
    """
    Boucle principale du thread flusher.

    - Attend un événement (timeout 0.5 s pour pouvoir regarder stop_event)
    - Essaie l'API
    - Si échec → écrit dans le fichier fallback
    - Marque l'élément comme traité (task_done)
    """
    while not stop_event.is_set():
        try:
            event = q.get(timeout=0.5)
        except queue.Empty:
            continue

        success = _send_to_api(api_url, event)
        if not success:
            _write_fallback(event)

        q.task_done()


# ---------------------------------------------------------------------------
# 5. start_flusher / stop_flusher
# ---------------------------------------------------------------------------

def start_flusher(
    q: queue.Queue,
    api_url: str = "http://127.0.0.1:8000/events",
) -> None:
    """
    Lance le thread flusher. À appeler UNE SEULE FOIS au démarrage (dans main).

    Paramètres
    ----------
    q : la queue partagée (event_queue)
    api_url : URL de l'endpoint FastAPI de Kenza.
              Mettre "" ou None si pas encore d'API → tout ira en fallback.
    """
    global _stop_event, _flusher_thread

    if _flusher_thread is not None and _flusher_thread.is_alive():
        print("[flusher] already running")
        return

    _stop_event = threading.Event()
    _flusher_thread = threading.Thread(
        target=_flusher_worker,
        args=(q, api_url or "", _stop_event),
        daemon=True,          # meurt automatiquement si le process principal meurt
        name="EventFlusher",
    )
    _flusher_thread.start()
    print(f"[flusher] started | api={api_url or '(none)'} | fallback={FALLBACK_FILE}")


def stop_flusher(q: queue.Queue, timeout: float = 5.0) -> None:
    """
    Arrêt propre :
      1. signale au worker de s'arrêter
      2. attend un peu que la queue se vide
      3. join le thread

    À appeler dans le `finally` de main() avant de quitter.
    """
    global _stop_event, _flusher_thread

    if _stop_event is None:
        return

    print("[flusher] stopping…")
    _stop_event.set()

    # Laisse un peu de temps pour vider la queue
    deadline = time.time() + timeout
    while not q.empty() and time.time() < deadline:
        time.sleep(0.05)

    if _flusher_thread is not None:
        _flusher_thread.join(timeout=2.0)

    print("[flusher] stopped")
    _stop_event = None
    _flusher_thread = None


# ---------------------------------------------------------------------------
# 6. Test autonome (python -m transport.flusher  ou  python transport/flusher.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== Test Lina / flusher ===")
    start_flusher(event_queue, api_url="")   # pas d'API → fallback fichier

    for i in range(5):
        fake = {
            "enriched_event": {
                "decoded": {
                    "raw": {
                        "key_code": 65 + i,
                        "scan_code": 30,
                        "event_type": "PRESS",
                        "timestamp": time.time(),
                        "is_injected": False,
                    },
                    "key_name": chr(65 + i),
                    "character": chr(97 + i),
                    "modifiers": [],
                },
                "context": {
                    "window_title": "Test",
                    "process_name": "test.exe",
                    "process_id": 1,
                },
            },
            "verdict": {"action": "PASS", "rule_id": None, "replacement_key": None},
            "logged_at": time.time(),
        }
        push_event(event_queue, fake)
        print(f"  pushed event {i + 1}")
        time.sleep(0.05)

    time.sleep(1.0)
    stop_flusher(event_queue)

    if FALLBACK_FILE.exists():
        print(f"\nFallback file content ({FALLBACK_FILE}):")
        print(FALLBACK_FILE.read_text(encoding="utf-8")[:800])
    else:
        print("No fallback file created.")
