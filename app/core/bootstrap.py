"""Early process bootstrap steps."""

from pathlib import Path

from dotenv import load_dotenv

# Ensure local .env overrides host/env settings before importing modules that read env.
repo_root = Path(__file__).resolve().parents[2]
dotenv_path = repo_root / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path, override=True)
else:
    load_dotenv(override=True)
