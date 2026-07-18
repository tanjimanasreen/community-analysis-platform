import os
import sys
from pathlib import Path

# Add the project root to sys.path so we can import from tests
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from tests.unit.test_backend_api import _build_run

artifacts_dir = Path("./artifacts")

# Build a couple of mock runs
_build_run(artifacts_dir, run_id="run-03", month="03")
_build_run(artifacts_dir, run_id="run-04", month="04")

print(f"Successfully generated mock run data in {artifacts_dir.absolute()}/runs")
