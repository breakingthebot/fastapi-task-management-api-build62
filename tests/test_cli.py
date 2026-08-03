# tests/test_cli.py
# Tests for CLI entry point task-api execution and version flag.
# Connects to: src/task_api/cli.py
# Created: 2026-08-02

import subprocess
import sys


def test_cli_version_flag():
    """Verify executing task-api with --version outputs current package version."""
    result = subprocess.run(
        [sys.executable, "-m", "task_api.cli", "--version"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "task-api 0.11.0" in result.stdout.strip()
