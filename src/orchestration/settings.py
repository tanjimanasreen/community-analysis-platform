import os
from pathlib import Path


def get_project_root() -> str:
    """Resolve the absolute path to the project root."""
    return str(Path(__file__).resolve().parent.parent.parent)


def configure_prefect_results_dir() -> None:
    """
    Configure Prefect result storage to use the project-local directory.
    Uses an explicit project root rather than the current working directory.
    """
    project_root = get_project_root()
    results_dir = os.path.join(project_root, ".prefect_results")
    os.environ.setdefault("PREFECT_RESULTS_LOCAL_STORAGE_PATH", results_dir)
