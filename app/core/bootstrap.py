"""Early process bootstrap steps."""

from dotenv import load_dotenv

# Ensure local .env overrides host/env settings before importing modules that read env.
load_dotenv(override=True)
