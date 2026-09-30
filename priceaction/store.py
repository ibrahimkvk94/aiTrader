import json
import sqlite3
import time
import hashlib
from contextlib import contextmanager
from .model import ROOT, Bar


def digest(items):
    return hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()


class Store:
    def __init__(self, path=None):
        self.path = path or ROOT / "data" / "research.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS candles (
                  market TEXT, symbol TEXT, frame TEXT, start INTEGER, end INTEGER,
                  open REAL, high REAL, low REAL, close REAL, volume REAL,
                  PRIMARY KEY(market,symbol,frame,start));
                CREATE TABLE IF NOT EXISTS runs (
                  id TEXT PRIMARY KEY, created_at INTEGER, market TEXT, symbol TEXT,
                  config_json TEXT, summary_json TEXT);
                CREATE TABLE IF NOT EXISTS decisions (
                  run_id TEXT, seq INTEGER, event_json TEXT, PRIMARY KEY(run_id,seq));
                CREATE TABLE IF NOT EXISTS trades (
                  run_id TEXT, seq INTEGER, trade_json TEXT, PRIMARY KEY(run_id,seq));
                CREATE TABLE IF NOT EXISTS snapshots (
                  market TEXT, symbol TEXT, updated_at INTEGER, payload TEXT,
                  PRIMARY KEY(market,symbol));
                CREATE TABLE IF NOT EXISTS observations (
                  market TEXT, symbol TEXT, observed_at INTEGER, candle_end INTEGER,
                  config_id TEXT, decision_json TEXT,
                  PRIMARY KEY(market,symbol,candle_end,config_id));
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        try:
            db.execute("PRAGMA journal_mode=WAL")
            with db:
                yield db
        finally:
            db.close()

    def save_bars(self, market, symbol, frame, bars):
        with self.connect() as db:
            db.executemany("INSERT OR REPLACE INTO candles VALUES (?,?,?,?,?,?,?,?,?,?)",
                [(market, symbol, frame, b.start, b.end, b.open, b.high, b.low, b.close, b.volume) for b in bars])

    def load_bars(self, market, symbol, frame):
        with self.connect() as db:
            rows = db.execute("SELECT start,end,open,high,low,close,volume FROM candles WHERE market=? AND symbol=? AND frame=? ORDER BY start",
                              (market, symbol, frame)).fetchall()
        return [Bar(*r) for r in rows]

    def publish(self, run_id, cfg, symbol, engine, payload):
        market = cfg["market"]
        now = int(time.time())
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM runs WHERE id=?", (run_id,)).fetchone():
                previous = db.execute("SELECT payload FROM snapshots WHERE market=? AND symbol=?", (market, symbol)).fetchone()
                previous = json.loads(previous[0]) if previous else {}
                audit = previous.get("audit", {})
                event_start = trade_start = 0
                parent = None
                if previous.get("config_id") == payload["config_id"] and audit:
                    ne, nt = audit["event_count"], audit["trade_count"]
                    if (len(engine.events) >= ne and len(engine.trades) >= nt
                            and digest(engine.events[:ne]) == audit["event_digest"]
                            and digest(engine.trades[:nt]) == audit["trade_digest"]):
                        parent = previous["run_id"]
                        event_start, trade_start = ne, nt
                payload["audit"] = {"parent_run_id": parent, "event_count": len(engine.events),
                    "trade_count": len(engine.trades), "event_digest": digest(engine.events), "trade_digest": digest(engine.trades)}
                db.execute("INSERT INTO runs VALUES (?,?,?,?,?,?)", (run_id, now, market, symbol,
                    json.dumps(cfg), json.dumps({**engine.summary(), "audit": payload["audit"]})))
                db.executemany("INSERT INTO decisions VALUES (?,?,?)",
                    [(run_id, i, json.dumps(e, ensure_ascii=False)) for i, e in enumerate(engine.events[event_start:], start=event_start)])
                db.executemany("INSERT INTO trades VALUES (?,?,?)",
                    [(run_id, i, json.dumps(t, ensure_ascii=False)) for i, t in enumerate(engine.trades[trade_start:], start=trade_start)])
            else:
                summary = json.loads(db.execute("SELECT summary_json FROM runs WHERE id=?", (run_id,)).fetchone()[0])
                payload["audit"] = summary.get("audit", {"parent_run_id": None, "event_count": len(engine.events),
                    "trade_count": len(engine.trades), "event_digest": digest(engine.events), "trade_digest": digest(engine.trades)})
            db.execute("INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?)",
                       (market, symbol, now, json.dumps(payload, ensure_ascii=False)))
            if engine.events:
                # This is an observed scanner state, NOT a forward-trade execution.
                db.execute("INSERT OR IGNORE INTO observations VALUES (?,?,?,?,?,?)", (market, symbol, now,
                    payload["last_bar"], payload["config_id"], json.dumps(engine.events[-1], ensure_ascii=False)))

    def snapshots(self):
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT payload FROM snapshots ORDER BY market,symbol")]

    def run_records(self, run_id, kind="decisions"):
        """Reconstruct an immutable run from parent + append-only deltas."""
        if kind not in {"decisions", "trades"}:
            raise ValueError("Unknown audit table")
        column = "event_json" if kind == "decisions" else "trade_json"
        records, seen = {}, set()
        with self.connect() as db:
            while run_id:
                if run_id in seen:
                    raise ValueError("Audit lineage cycle")
                seen.add(run_id)
                row = db.execute("SELECT summary_json FROM runs WHERE id=?", (run_id,)).fetchone()
                if row is None:
                    raise ValueError("Missing parent run")
                for seq, value in db.execute(f"SELECT seq,{column} FROM {kind} WHERE run_id=?", (run_id,)):
                    records.setdefault(seq, json.loads(value))
                run_id = json.loads(row[0]).get("audit", {}).get("parent_run_id")
        return [records[i] for i in sorted(records)]
