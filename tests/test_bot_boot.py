"""Boot regression: ``python app/bot.py`` must not shadow the stdlib ``logging``.

Running the entry script directly puts ``app/`` first on ``sys.path``, which
used to make stdlib ``concurrent.futures`` import ``app/logging.py`` instead of
the ``logging`` package and crash with ``ModuleNotFoundError``. ``bot.py``
rebases ``sys.path`` onto the repository root; with no Discord token the
process should now reach the fail-fast ``RuntimeError`` gate instead.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_direct_script_boot_fails_fast_on_missing_token() -> None:
    env = dict(os.environ)
    env["DISCORD_TOKEN"] = ""  # force empty; env var overrides .env in pydantic-settings
    proc = subprocess.run(
        [sys.executable, "app/bot.py"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = proc.stdout + proc.stderr
    assert "No module named 'logging.handlers'" not in output
    assert "DISCORD_TOKEN" in output
