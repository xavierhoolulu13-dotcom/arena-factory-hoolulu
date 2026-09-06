from __future__ import annotations

import argparse
import json
import os


def main() -> None:
    parser = argparse.ArgumentParser(prog="factory", description="Arena Factory Hoolulu")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("tick", help="Run one pipeline cycle")
    sub.add_parser("status", help="Print factory snapshot KPIs")
    serve = sub.add_parser("serve", help="Start the command center")
    serve.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    serve.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8080")))
    args = parser.parse_args()

    if args.cmd == "serve":
        import uvicorn

        uvicorn.run("app.main:app", host=args.host, port=args.port, reload=False)
        return

    from factory.brain import FactoryBrain

    brain = FactoryBrain()
    if args.cmd == "tick":
        print(json.dumps(brain.tick(), indent=2, default=str))
    elif args.cmd == "status":
        snap = brain.snapshot()
        print(json.dumps({"kpis": snap["kpis"], "open_pings": snap["open_pings"]}, indent=2, default=str))


if __name__ == "__main__":
    main()
