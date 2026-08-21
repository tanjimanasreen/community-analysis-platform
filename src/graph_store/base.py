from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol, Union, runtime_checkable

SnapshotMeta = Mapping[str, Any]
PathLike = Union[str, Path]


@runtime_checkable
class GraphRepository(Protocol):
    """Database boundary for raw graph data and derived interaction edges."""

    def check_connectivity(self) -> None:
        """Raise if the configured backend cannot be reached."""

    def clear(self) -> None:
        """Remove graph data for an isolated local or test run."""

    def create_indexes(self) -> None:
        """Create backend-specific indexes needed by the thesis graph schema."""

    def import_raw_data(self, data_path: PathLike, platform: str) -> None:
        """Import legacy `source,target,relation` raw graph CSV rows."""

    def import_interactions(self, path: PathLike, snapshot_meta: SnapshotMeta) -> None:
        """Import monthly user-user interaction edges with IF/WIF metrics."""

    def export_interactions(
        self, snapshot_meta: SnapshotMeta, out_path: PathLike
    ) -> None:
        """Export generated interaction rows for a snapshot as Parquet."""

    def get_user_interactions(
        self, snapshot_meta: SnapshotMeta
    ) -> Iterable[Mapping[str, Any]]:
        """Return derived interaction edges for a snapshot."""

    def get_distinct_users(self) -> Iterable[str]:
        """Return all user IDs known by the repository."""

    def close(self) -> None:
        """Close any open backend resources."""
