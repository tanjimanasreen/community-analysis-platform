import sys
import pandas as pd
from pathlib import Path
from src.api.services.run_catalog import RunCatalog
from src.api.services.artifact_reader import ArtifactReader
from src.api.services.periods import discover_periods, record_period, default_year
from src.pipelines.social_network_pipeline import _community_node_index

def patch_run(run_id: str, catalog: RunCatalog, reader: ArtifactReader):
    manifest = catalog.get_manifest(run_id)
    config = reader.read_safe_config(run_id)
    periods = discover_periods(manifest, config)
    fallback_year = default_year(config, manifest)

    if not periods:
        return

    print(f"Patching run: {run_id}")
    root = catalog.get_run_root(run_id)

    for period in periods:
        try:
            # Find communities absolute to calculate layout from
            abs_comm_records = [
                r for r in manifest.artifacts
                if r.key.startswith("communities_absolute") and record_period(r, fallback_year=fallback_year) == period
            ]
            if not abs_comm_records:
                print(f"  No communities_absolute for {period}")
                continue

            # Read communities frame
            comm_frame = pd.read_parquet(root / abs_comm_records[0].path)

            # Calculate new layout using pipeline logic
            node_index_df = _community_node_index(comm_frame)

            # Update community node index absolute
            abs_records = [
                r for r in manifest.artifacts
                if r.key.startswith("community_node_index_absolute") and record_period(r, fallback_year=fallback_year) == period
            ]
            if abs_records:
                abs_rec = abs_records[0]
                abs_path = root / abs_rec.path
                if abs_path.exists():
                    df = pd.read_parquet(abs_path)
                    if "x" not in df.columns:
                        df = df.merge(node_index_df, on="node_id", how="left")
                        df["x"] = df["x"].fillna(0.0)
                        df["y"] = df["y"].fillna(0.0)
                        df.to_parquet(abs_path)
                        print(f"  Updated {abs_path.name} (absolute) for {period}")
                    else:
                        print(f"  {abs_path.name} already patched (absolute) for {period}")

            # Find communities weighted to calculate layout from
            w_comm_records = [
                r for r in manifest.artifacts
                if r.key.startswith("communities_weighted") and record_period(r, fallback_year=fallback_year) == period
            ]
            if w_comm_records:
                w_comm_frame = pd.read_parquet(root / w_comm_records[0].path)
                w_node_index_df = _community_node_index(w_comm_frame)
            else:
                w_node_index_df = node_index_df

            # Update community node index weighted
            w_records = [
                r for r in manifest.artifacts
                if r.key.startswith("community_node_index_weighted") and record_period(r, fallback_year=fallback_year) == period
            ]
            if w_records:
                w_rec = w_records[0]
                w_path = root / w_rec.path
                if w_path.exists():
                    df = pd.read_parquet(w_path)
                    if "x" not in df.columns:
                        df = df.merge(w_node_index_df, on="node_id", how="left")
                        df["x"] = df["x"].fillna(0.0)
                        df["y"] = df["y"].fillna(0.0)
                        df.to_parquet(w_path)
                        print(f"  Updated {w_path.name} (weighted) for {period}")
                    else:
                        print(f"  {w_path.name} already patched (weighted) for {period}")
        except Exception as e:
            print(f"  Failed for period {period}: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/patch_network_layouts.py <API_ARTIFACT_ROOT>")
        sys.exit(1)

    api_root = Path(sys.argv[1])
    catalog = RunCatalog(api_root)
    reader = ArtifactReader(catalog)

    try:
        manifests = catalog.list_manifests()
    except Exception as e:
        print(f"Failed to list manifests: {e}")
        sys.exit(1)

    for m in manifests:
        patch_run(m.run_id, catalog, reader)

if __name__ == "__main__":
    main()
