import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
from pathlib import Path
import threading
import time
from . import VERSION
from .engine import replay
from .feed import download, download_bist_daily, calendar_aggregate
from .model import ROOT, config, fingerprint, aggregate, read_csv, symbol_name
from .store import Store

LOG = logging.getLogger("priceaction")


def analyze(store, cfg, symbol, bars, setups, contexts, metadata):
    if not bars:
        raise ValueError("No closed candles available")
    engine = replay(cfg, bars, setups, contexts)
    cfg_id = fingerprint({**cfg, "engine_version": VERSION})
    data_hash = hashlib.sha256(json.dumps([[asdict(b) for b in series] for series in (bars, setups, contexts)]).encode()).hexdigest()[:16]
    run_id = f"{cfg['market']}-{symbol}-{cfg_id}-{data_hash}"
    last = engine.events[-1] if engine.events else {}
    payload = {"market": cfg["market"], "symbol": symbol, "profile": cfg["profile"],
        "frames": [cfg["context"], cfg["setup"], cfg["base"]], "config_id": cfg_id,
        "run_id": run_id, "mode": "historical_replay_live_data", "updated_at": int(time.time()),
        "first_bar": bars[0].start, "last_bar": bars[-1].end, "bar_count": len(bars),
        "summary": engine.summary(), "latest": last, "metadata": metadata,
        "config": cfg, "bars": [asdict(b) for b in bars[-180:]],
        "zones": [asdict(z) for z in engine.setup.zones if z.active][-12:],
        "events": [e for e in engine.events if e["action"] != "WATCH"][-150:],
        "decisions": engine.events[-30:], "trades": engine.trades[-100:],
        "equity": engine.equity[::max(1, len(engine.equity)//300)],
        "model_results": [{"model": m, "trades": sum(t["model"] == m for t in engine.trades),
            "net_pnl": sum(t["pnl"] for t in engine.trades if t["model"] == m)}
            for m in ("demand_continuation", "demand_sweep", "breaker")]}
    store.publish(run_id, cfg, symbol, engine, payload)
    directory = ROOT / "reports" / cfg["market"]
    directory.mkdir(parents=True, exist_ok=True)
    # Runtime output, not source/config editing.
    destination = directory / f"{symbol}.json"
    temp = destination.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(destination)
    return payload


def refresh_crypto(store, symbol, days):
    cfg = config("crypto")
    cached = store.load_bars("crypto", symbol, "15m")
    requested_start = (int(time.time()) - days * 86400) // 14400 * 14400
    if cached and cached[0].start <= requested_start:
        new = download(symbol, cached[-1].start)
        merged = {b.start: b for b in cached}
        merged.update({b.start: b for b in new})
        bars = sorted(merged.values(), key=lambda b: b.start)
    else:
        bars = download(symbol, requested_start)
    store.save_bars("crypto", symbol, "15m", bars)
    return analyze(store, cfg, symbol, bars, aggregate(bars, 3600), aggregate(bars, 14400),
                   {"source": "Binance public spot", "delay": "Yalnız kapanmış 15dk mumlar", "currency": "USDT"})


def refresh_bist(store, symbol):
    cfg = config("bist")
    bars, metadata = download_bist_daily(symbol)
    store.save_bars("bist", symbol, "1d", bars)
    # All completed calendar buckets are included; replay reveals each only at known_at.
    return analyze(store, cfg, symbol, bars, calendar_aggregate(bars, "1w"), calendar_aggregate(bars, "1mo"),
                   {**metadata, "currency": "TRY", "performance_validated": False})


class Service:
    def __init__(self, store, symbols, bist, days):
        self.store, self.symbols, self.bist, self.days = store, symbols, bist, days
        self.lock = threading.Lock()
        self.errors = {}
        self.busy = False
        self.last_attempt = 0
        self.started_at = int(time.time())
        self.stop = threading.Event()

    def refresh(self, include_bist=True):
        with self.lock:
            if self.busy:
                return
            self.busy = True
            self.last_attempt = int(time.time())
        jobs = [("crypto", s, refresh_crypto, (self.store, s, self.days)) for s in self.symbols]
        if include_bist:
            jobs += [("bist", s, refresh_bist, (self.store, s)) for s in self.bist]
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = {pool.submit(fn, *args): (market, symbol) for market, symbol, fn, args in jobs}
                for future in as_completed(futures):
                    market, symbol = futures[future]
                    key = market + ":" + symbol
                    try:
                        result = future.result()
                        with self.lock:
                            self.errors.pop(key, None)
                        LOG.info("%s: %s bars; %s closed hypothetical trades", key,
                                 result["bar_count"], result["summary"]["closed_trades"])
                    except Exception as exc:
                        LOG.exception("Refresh failed: %s", key)
                        with self.lock:
                            self.errors[key] = str(exc)
        finally:
            with self.lock:
                self.busy = False

    def worker(self):
        count = 0
        while not self.stop.is_set():
            self.refresh(include_bist=count % 30 == 0)
            count += 1
            self.stop.wait(60)

    def state(self):
        with self.lock:
            status = {"busy": self.busy, "errors": dict(self.errors), "last_attempt": self.last_attempt}
        allowed = {("crypto", s) for s in self.symbols} | {("bist", s) for s in self.bist}
        items = [p for p in self.store.snapshots() if (p["market"], p["symbol"]) in allowed]
        now = int(time.time())
        for item in items:
            item["feed_error"] = status["errors"].get(item["market"] + ":" + item["symbol"])
            item["fetch_stale"] = now - item["updated_at"] > (180 if item["market"] == "crypto" else 3600)
            item["data_stale"] = now - item["last_bar"] > (1800 if item["market"] == "crypto" else 4 * 86400)
        return {"version": VERSION, "server_time": now, "started_at": self.started_at,
                "execution": "DISABLED", **status, "items": items}


def serve(service, port):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path in {"/", "/index.html"}:
                content = (ROOT / "web" / "index.html").read_bytes()
                mime = "text/html; charset=utf-8"
            elif self.path == "/api/state":
                content = json.dumps(service.state(), ensure_ascii=False, allow_nan=False).encode()
                mime = "application/json; charset=utf-8"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=service.worker, daemon=True)
    thread.start()
    LOG.info("Dashboard http://127.0.0.1:%s — external order submission disabled", port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        service.stop.set()
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description="Price Action Research — no real orders")
    sub = parser.add_subparsers(dest="command", required=True)
    from .plan_replay import register_parser, main as run_plan_replay
    register_parser(sub)
    for command in ("serve", "scan"):
        p = sub.add_parser(command)
        p.add_argument("--symbols", nargs="*", default=["BTCUSDT", "ETHUSDT"])
        p.add_argument("--bist", nargs="*", default=["THYAO.IS", "GARAN.IS", "EREGL.IS"])
        p.add_argument("--days", type=int, default=60)
        if command == "serve":
            p.add_argument("--port", type=int, default=8765)
    p = sub.add_parser("import-bist")
    p.add_argument("--symbol", required=True)
    for name in ("base", "setup", "context"):
        p.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'plan-replay':
        run_plan_replay(args)
        return
    store = Store()
    if args.command == "import-bist":
        cfg = config("bist")
        frames = [read_csv(getattr(args, name)) for name in ("base", "setup", "context")]
        now = time.time()
        if any(b.end > now for series in frames for b in series):
            raise ValueError("CSV contains unclosed/future candles")
        result = analyze(store, cfg, symbol_name(args.symbol), *frames,
                         {"source": "CSV / kullanıcı verisi", "currency": "TRY", "performance_validated": False})
        print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    else:
        if not 7 <= args.days <= 365:
            parser.error("--days must be between 7 and 365")
        service = Service(store, [symbol_name(s) for s in args.symbols], [symbol_name(s) for s in args.bist], args.days)
        if args.command == "serve":
            serve(service, args.port)
        else:
            service.refresh()
            print(json.dumps({"errors": service.errors, "results": [{"symbol": x["symbol"],
                "market": x["market"], "summary": x["summary"]} for x in service.state()["items"]]}, ensure_ascii=False, indent=2))
            if service.errors:
                raise SystemExit(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
