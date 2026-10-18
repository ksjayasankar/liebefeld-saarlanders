"""navigator migrate | gateway-check | fetch [--refresh] | snapshot export|import | extract | enrich | embed | report | load | check | index | eval

`check` runs the build checks on staging_<domain> and, when they pass, makes it live."""
import argparse
import asyncio
import importlib


def _call(module: str, fn: str, *args):
    return getattr(importlib.import_module(f"navigator.{module}"), fn)(*args)


def main():
    p = argparse.ArgumentParser(prog="navigator")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("migrate")
    sub.add_parser("gateway-check")
    for name in ("fetch", "extract", "enrich", "embed", "report", "load", "check", "index", "eval"):
        s = sub.add_parser(name)
        s.add_argument("--domain", required=True)
        if name == "fetch":
            s.add_argument("--refresh", action="store_true")
            s.add_argument("--hosts", nargs="*", help="host names to fetch; all when omitted")
        if name == "eval":
            s.add_argument("--split", choices=["dev", "all"], required=True)
    s = sub.add_parser("snapshot")
    s.add_argument("action", choices=["export", "import"])
    s.add_argument("path")
    a = p.parse_args()

    if a.cmd == "migrate":
        print("schema version", _call("db", "migrate"))
    elif a.cmd == "gateway-check":
        _call("apertus", "gateway_check")
    elif a.cmd == "snapshot":
        _call("snapshot", a.action.replace("import", "import_"), a.path)
    elif a.cmd == "fetch":
        from .config import load_domain
        asyncio.run(_call("fetch", "run", load_domain(a.domain), a.refresh, a.hosts))
    elif a.cmd == "eval":
        _call("eval", "run", a.domain, a.split)
    else:
        _call("build", a.cmd, a.domain)
