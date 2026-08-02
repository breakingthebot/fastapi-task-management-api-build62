# src/task_api/cli.py
# Command Line Interface (CLI) entry point for task-api.
# Connects to: src/task_api/__init__.py, src/task_api/main.py
# Created: 2026-08-02

import sys
import argparse
import uvicorn
from task_api import __version__


def main():
    parser = argparse.ArgumentParser(
        prog="task-api",
        description="Task Management API CLI — run dev server or check version."
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    run_parser = subparsers.add_parser("run", help="Run the FastAPI application server")
    run_parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    run_parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    run_parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")

    args = parser.parse_args()

    if args.command == "run":
        uvicorn.run("task_api.main:app", host=args.host, port=args.port, reload=args.reload)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
