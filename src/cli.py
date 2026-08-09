import argparse
import subprocess
import sys
from pathlib import Path

from src.config.loader import (
    get_database_config,
    load_config,
    normalize_month,
    validate_run_config,
)


def validate_config(config_path, dataset_id=None):
    print(f"Validating config: {config_path}")
    try:
        config = load_config(config_path)
        if dataset_id:
            datasets = config.get("datasets", []) + config.get(
                "longitudinal_datasets", []
            )
            ds = next(
                (
                    d
                    for d in datasets
                    if d.get("id") == dataset_id or d.get("month") == dataset_id
                ),
                None,
            )
            if ds:
                config.update(ds)
            else:
                print(f"Warning: dataset id '{dataset_id}' not found in {config_path}")
        validate_run_config(config)
        print("Config is valid.")
        return config
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Community Analysis Intelligence Platform"
    )
    from src.logging_config import setup_logging

    setup_logging()
    subparsers = parser.add_subparsers(dest="command", required=True)

    # validate-config command
    parser_validate = subparsers.add_parser(
        "validate-config", help="Validate a configuration file"
    )
    parser_validate.add_argument("--config", required=True, help="Path to config file")
    parser_validate.add_argument(
        "--dataset-id",
        required=False,
        help="Optional dataset ID to execute within the config",
    )

    # export-graph command
    parser_export = subparsers.add_parser(
        "export-graph", help="Export graph relationships"
    )
    parser_export.add_argument("--config", required=True, help="Path to config file")
    parser_export.add_argument(
        "--dataset-id",
        required=False,
        help="Optional dataset ID to execute within the config",
    )
    parser_export.add_argument("--output", required=False, help="Output CSV path")
    parser_export.add_argument(
        "--query-name", required=False, help="Exporter query name override"
    )

    parser_db_check = subparsers.add_parser(
        "db-check", help="Check Memgraph connectivity"
    )
    parser_db_check.add_argument("--config", required=False, help="Path to config file")
    parser_db_check.add_argument(
        "--dataset-id",
        required=False,
        help="Optional dataset ID to execute within the config",
    )

    subparsers.add_parser("db-up", help="Start local Memgraph using Docker Compose")

    parser_import_graph = subparsers.add_parser(
        "import-graph", help="Import legacy source,target,relation CSV into Memgraph"
    )
    parser_import_graph.add_argument(
        "--file", nargs="+", required=True, help="Path to one or more legacy CSV files"
    )
    parser_import_graph.add_argument(
        "--platform",
        required=True,
        choices=["telegram", "twitter"],
        help="Platform of the data",
    )
    parser_import_graph.add_argument(
        "--config", required=False, help="Path to config file"
    )
    parser_import_graph.add_argument(
        "--dataset-id",
        required=False,
        help="Optional dataset ID to execute within the config",
    )

    parser_ingest_interactions = subparsers.add_parser(
        "ingest-interactions", help="Build/import monthly interaction CSV into Memgraph"
    )
    parser_ingest_interactions.add_argument(
        "--file",
        required=True,
        help="Path to raw legacy CSV or derived interaction CSV",
    )
    parser_ingest_interactions.add_argument(
        "--config", required=True, help="Path to config file"
    )
    parser_ingest_interactions.add_argument(
        "--dataset-id",
        required=False,
        help="Optional dataset ID to execute within the config",
    )
    parser_ingest_interactions.add_argument(
        "--out",
        required=False,
        help="Derived interaction CSV output path when --file is raw",
    )
    parser_ingest_interactions.add_argument(
        "--no-db",
        action="store_true",
        help="Build derived CSV without importing into Memgraph",
    )

    # run-social-network command
    parser_social = subparsers.add_parser(
        "run-social-network", help="Run social network analysis"
    )
    parser_social.add_argument("--config", required=True, help="Path to config file")
    parser_social.add_argument(
        "--dataset-id",
        required=False,
        help="Optional dataset ID to execute within the config",
    )
    parser_social.add_argument("--debug", action="store_true")

    # run-topics command
    parser_topics = subparsers.add_parser("run-topics", help="Run topic modeling")
    parser_topics.add_argument("--config", required=True, help="Path to config file")
    parser_topics.add_argument(
        "--dataset-id",
        required=False,
        help="Optional dataset ID to execute within the config",
    )

    # run-theme-analysis command
    parser_theme = subparsers.add_parser(
        "run-theme-analysis", help="Run theme generation and transition analysis"
    )
    parser_theme.add_argument("--config", required=True, help="Path to config file")
    parser_theme.add_argument(
        "--dataset-id",
        required=False,
        help="Optional dataset ID to execute within the config",
    )

    # run-all command
    parser_all = subparsers.add_parser("run-all", help="Run the full pipeline")
    parser_all.add_argument("--config", required=True, help="Path to config file")
    parser_all.add_argument(
        "--dataset-id",
        required=False,
        help="Optional dataset ID to execute within the config",
    )
    parser_all.add_argument("--debug", action="store_true")
    parser_all.add_argument(
        "--theme-provider",
        required=False,
        help="Override theme_provider.primary for this run",
    )

    parser_evolution = subparsers.add_parser(
        "run-evolution-pipeline",
        help="Run the multi-month evolution pipeline",
    )
    parser_evolution.add_argument("--config", required=True, help="Path to config file")
    parser_evolution.add_argument(
        "--dataset-id",
        required=False,
        help="Optional dataset ID to execute within the config",
    )
    parser_evolution.add_argument(
        "--theme-provider",
        required=False,
        help="Override theme_provider.primary for this run",
    )

    parser_preflight = subparsers.add_parser(
        "pipeline-preflight",
        help="Validate dependencies, inputs, providers, and required embedding services",
    )
    parser_preflight.add_argument("--config", required=True, help="Path to config file")
    parser_preflight.add_argument(
        "--theme-provider",
        required=False,
        help="Override theme_provider.primary for the planned run",
    )
    parser_preflight.add_argument(
        "--skip-services",
        action="store_true",
        help="Skip live TEI requests (useful only for offline configuration checks)",
    )

    parser_report = subparsers.add_parser(
        "build-report", help="Build a markdown artifact index"
    )
    parser_report.add_argument("--config", required=True, help="Path to config file")
    parser_report.add_argument(
        "--dataset-id",
        required=False,
        help="Optional dataset ID to execute within the config",
    )
    parser_report.add_argument(
        "--out",
        required=False,
        default="/tmp/community-analysis-artifact-index.md",
        help="Report output path",
    )

    parser_verify = subparsers.add_parser(
        "verify-output-contract", help="Validate generated output artifact schemas"
    )
    parser_verify.add_argument("--config", required=True, help="Path to config file")
    parser_verify.add_argument(
        "--dataset-id",
        required=False,
        help="Optional dataset ID to execute within the config",
    )
    parser_verify.add_argument(
        "--longitudinal",
        action="store_true",
        help="Validate all months listed in the theme-input manifest",
    )

    parser_benchmark = subparsers.add_parser(
        "theme-benchmark", help="Run theme-generation benchmark tools"
    )
    benchmark_subparsers = parser_benchmark.add_subparsers(
        dest="benchmark_command", required=True
    )

    parser_benchmark_dataset = benchmark_subparsers.add_parser(
        "build-dataset", help="Build a frozen offline benchmark dataset"
    )
    parser_benchmark_dataset.add_argument(
        "--config", required=True, help="Path to config file"
    )
    parser_benchmark_dataset.add_argument(
        "--dataset-id",
        required=False,
        help="Optional dataset ID to execute within the config",
    )
    parser_benchmark_dataset.add_argument(
        "--run-id", required=True, help="Benchmark run identifier"
    )
    parser_benchmark_dataset.add_argument(
        "--limit",
        type=int,
        required=False,
        help="Maximum number of valid examples to include",
    )
    parser_benchmark_dataset.add_argument(
        "--gpt-5-nano-outputs",
        required=False,
        help="Optional local JSONL file of prior GPT-5-nano outputs to copy as reference data",
    )

    parser_benchmark_inventory = benchmark_subparsers.add_parser(
        "inventory-artifacts",
        help="Inventory saved theme-input artifacts for benchmark readiness",
    )
    parser_benchmark_inventory.add_argument(
        "--config", required=True, help="Path to config file"
    )
    parser_benchmark_inventory.add_argument(
        "--dataset-id",
        required=False,
        help="Optional dataset ID to execute within the config",
    )
    parser_benchmark_inventory.add_argument(
        "--source-configs",
        required=False,
        help="Comma-separated configs whose saved theme-input artifacts should be inventoried",
    )

    parser_benchmark_freeze = benchmark_subparsers.add_parser(
        "freeze-dataset",
        help="Freeze a deterministic benchmark dataset with development/pilot/heldout splits",
    )
    parser_benchmark_freeze.add_argument(
        "--config", required=True, help="Path to config file"
    )
    parser_benchmark_freeze.add_argument(
        "--dataset-id",
        required=False,
        help="Optional dataset ID to execute within the config",
    )
    parser_benchmark_freeze.add_argument(
        "--run-id", required=True, help="Benchmark run identifier"
    )
    parser_benchmark_freeze.add_argument(
        "--source-configs",
        required=False,
        help="Comma-separated configs whose saved theme-input artifacts should be frozen",
    )
    parser_benchmark_freeze.add_argument("--target-examples", type=int, default=100)
    parser_benchmark_freeze.add_argument("--min-examples", type=int, default=40)
    parser_benchmark_freeze.add_argument("--max-examples", type=int, default=120)
    parser_benchmark_freeze.add_argument("--seed", type=int, default=16016)
    parser_benchmark_freeze.add_argument(
        "--overwrite-existing-frozen-run",
        action="store_true",
        help="Allow replacing an existing frozen run when manifest hashes or settings differ",
    )

    parser_benchmark_validate = benchmark_subparsers.add_parser(
        "validate-dataset",
        help="Validate frozen benchmark dataset integrity and write split distribution report",
    )
    parser_benchmark_validate.add_argument(
        "--config", required=True, help="Path to config file"
    )
    parser_benchmark_validate.add_argument(
        "--dataset-id",
        required=False,
        help="Optional dataset ID to execute within the config",
    )
    parser_benchmark_validate.add_argument(
        "--run-id", required=True, help="Benchmark run identifier"
    )
    parser_benchmark_validate.add_argument("--expected-dataset-hash", required=False)
    parser_benchmark_validate.add_argument("--expected-split-hash", required=False)

    parser_benchmark_run = benchmark_subparsers.add_parser(
        "run", help="Run benchmark providers"
    )
    parser_benchmark_run.add_argument(
        "--config", required=True, help="Path to config file"
    )
    parser_benchmark_run.add_argument(
        "--dataset-id",
        required=False,
        help="Optional dataset ID to execute within the config",
    )
    parser_benchmark_run.add_argument(
        "--run-id", required=True, help="Benchmark run identifier"
    )
    parser_benchmark_run.add_argument(
        "--providers",
        default="keyword_baseline,mock",
        help="Comma-separated provider specs. Offline: keyword_baseline,mock. Live: gemini:<exact_model_id>,llm7:<exact_model_id>",
    )
    parser_benchmark_run.add_argument(
        "--allow-live", action="store_true", help="Allow live benchmark provider calls"
    )
    parser_benchmark_run.add_argument(
        "--split",
        choices=["development", "pilot", "heldout"],
        required=False,
        help="Frozen dataset split to execute",
    )
    parser_benchmark_run.add_argument(
        "--max-examples",
        type=int,
        required=False,
        help="Maximum dataset examples to run",
    )
    parser_benchmark_run.add_argument(
        "--resume-unresolved",
        action="store_true",
        help="Run only requests that do not have successful cache entries for the selected provider/settings",
    )
    parser_benchmark_run.add_argument(
        "--max-unresolved-examples",
        type=int,
        required=False,
        help="Maximum unresolved examples to attempt in this invocation",
    )
    parser_benchmark_run.add_argument(
        "--example-ids-file",
        required=False,
        help="JSON file containing example_ids to run, such as a Phase 3 stability subset",
    )
    parser_benchmark_run.add_argument(
        "--repetition-index",
        type=int,
        required=False,
        help="Optional repetition index included in benchmark cache identity",
    )
    parser_benchmark_run.add_argument(
        "--keyword-modes",
        default=None,
        help="Comma-separated keyword modes to run. Defaults to all modes for offline providers and general for live providers.",
    )
    parser_benchmark_run.add_argument(
        "--max-concurrency",
        type=int,
        default=1,
        help="Maximum live provider concurrency",
    )
    parser_benchmark_run.add_argument(
        "--max-retries", type=int, default=2, help="Maximum retries for live providers"
    )
    parser_benchmark_run.add_argument(
        "--timeout", type=float, required=False, help="Live provider timeout in seconds"
    )
    parser_benchmark_run.add_argument(
        "--max-outbound-requests",
        type=int,
        default=50,
        help="Maximum outbound live requests including retries",
    )

    parser_benchmark_discover = benchmark_subparsers.add_parser(
        "discover-models", help="Discover live benchmark provider models"
    )
    parser_benchmark_discover.add_argument(
        "--provider",
        required=True,
        choices=["gemini", "llm7"],
        help="Provider to discover",
    )
    parser_benchmark_discover.add_argument(
        "--config", required=True, help="Path to config file"
    )
    parser_benchmark_discover.add_argument(
        "--dataset-id",
        required=False,
        help="Optional dataset ID to execute within the config",
    )
    parser_benchmark_discover.add_argument(
        "--run-id", required=True, help="Benchmark run identifier"
    )
    parser_benchmark_discover.add_argument(
        "--allow-live", action="store_true", help="Allow live provider discovery calls"
    )

    parser_benchmark_review = benchmark_subparsers.add_parser(
        "export-review", help="Export blinded benchmark review CSV"
    )
    parser_benchmark_review.add_argument(
        "--config", required=True, help="Path to config file"
    )
    parser_benchmark_review.add_argument(
        "--dataset-id",
        required=False,
        help="Optional dataset ID to execute within the config",
    )
    parser_benchmark_review.add_argument(
        "--run-id", required=True, help="Benchmark run identifier"
    )

    parser_benchmark_summarize = benchmark_subparsers.add_parser(
        "summarize",
        help="Write development/pilot benchmark scorecard and evaluation report",
    )
    parser_benchmark_summarize.add_argument(
        "--config", required=True, help="Path to config file"
    )
    parser_benchmark_summarize.add_argument(
        "--dataset-id",
        required=False,
        help="Optional dataset ID to execute within the config",
    )
    parser_benchmark_summarize.add_argument(
        "--run-id", required=True, help="Benchmark run identifier"
    )

    parser_benchmark_deepeval = benchmark_subparsers.add_parser(
        "evaluate-deepeval", help="Evaluate benchmark results using DeepEval LLM judge"
    )
    parser_benchmark_deepeval.add_argument(
        "--config", required=True, help="Path to config file"
    )
    parser_benchmark_deepeval.add_argument(
        "--dataset-id",
        required=False,
        help="Optional dataset ID to execute within the config",
    )
    parser_benchmark_deepeval.add_argument(
        "--run-id", required=True, help="Benchmark run identifier"
    )

    # import-csv command
    parser_import = subparsers.add_parser(
        "import-csv", help="Backward-compatible alias for import-graph"
    )
    parser_import.add_argument(
        "--file", nargs="+", required=True, help="Path to one or more CSV files"
    )
    parser_import.add_argument(
        "--platform",
        required=True,
        choices=["telegram", "twitter"],
        help="Platform of the data",
    )
    parser_import.add_argument("--config", required=False, help="Path to config file")
    parser_import.add_argument(
        "--dataset-id",
        required=False,
        help="Optional dataset ID to execute within the config",
    )

    args = parser.parse_args()

    if (
        hasattr(args, "config")
        and args.config
        and hasattr(args, "dataset_id")
        and not args.dataset_id
    ):
        config_data = load_config(args.config)
        datasets = config_data.get("datasets", [])
        if datasets:
            for ds in datasets:
                ds_id = ds.get("id")
                print(f"\n--- Running dataset {ds_id} ---")
                cmd = sys.argv.copy()
                if not cmd[0].endswith("python") and not cmd[0].endswith("python3"):
                    cmd.insert(0, sys.executable)
                cmd.extend(["--dataset-id", ds_id])
                import os

                env = os.environ.copy()
                env["PYTHONPATH"] = str(Path(__file__).parent.parent)
                subprocess.run(cmd, check=True, env=env)
            return

    if args.command == "validate-config":
        validate_config(args.config, getattr(args, "dataset_id", None))

    elif args.command == "db-check":
        from src.graph_store.memgraph_repository import MemgraphRepository

        config = load_config(args.config) if args.config else {}
        db_config = get_database_config(config)
        repo = MemgraphRepository(
            uri=db_config["uri"],
            user=db_config["user"],
            password=db_config["password"],
        )
        repo.client.execute_query("RETURN 1 AS ok")
        print("Database connection OK.")

    elif args.command == "db-up":
        subprocess.run(["docker", "compose", "up", "-d", "memgraph"], check=True)
        print("Memgraph startup requested via Docker Compose.")

    elif args.command == "import-csv":
        _import_raw_graph(args.file, args.platform, args.config)

    elif args.command == "import-graph":
        _import_raw_graph(args.file, args.platform, args.config)

    elif args.command == "ingest-interactions":
        config = validate_config(args.config, getattr(args, "dataset_id", None))
        snapshot_meta = {
            "data_type": config["data_type"],
            "content_type": config["content_type"],
            "month": normalize_month(config["month"]),
            "year": int(config["year"]),
        }
        if _csv_has_relation_column(args.file):
            from src.pipelines.ingestion_pipeline import run_ingestion_pipeline

            result = run_ingestion_pipeline(
                config,
                repository=None,
                raw_csv_path=args.file,
                output_csv_path=args.out,
                import_to_repository=False,
            )
            print(f"Derived interaction CSV written to: {result.output_path}")
            if args.no_db:
                print("Skipping database import because --no-db was provided.")
                return
        if args.no_db:
            print("No database import requested.")
            return

        from src.graph_store.memgraph_repository import MemgraphRepository

        db_config = get_database_config(config)
        repo = MemgraphRepository(
            uri=db_config["uri"],
            user=db_config["user"],
            password=db_config["password"],
        )
        repo.create_indexes()
        if _csv_has_relation_column(args.file):
            repo.import_interactions(result.output_path, snapshot_meta)
            print("Raw-to-derived interaction ingest complete.")
        else:
            repo.import_interactions(args.file, snapshot_meta)
            print("Interaction ingest complete.")

    elif args.command == "export-graph":
        from src.graph_store.neo4j_exporter import Neo4jExporter

        config = validate_config(args.config, getattr(args, "dataset_id", None))
        neo4j_config = config.get("neo4j", {})
        output_file = args.output or config.get("export_path") or config["input_path"]
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        query_name = args.query_name or _default_export_query_name(config)
        exporter = Neo4jExporter(
            uri=neo4j_config.get("uri"),
            user=neo4j_config.get("user"),
            password=neo4j_config.get("password"),
            database=neo4j_config.get("database", "neo4j"),
        )
        exporter.export(
            query_name=query_name,
            year=int(config["year"]),
            month=normalize_month(config["month"]),
            output_file=output_file,
        )
        print(f"Exported graph relationships to {output_file}")

    elif args.command in ["run-social-network", "run-topics", "run-all"]:
        _run_social_pipeline_command(
            args.command,
            args.config,
            dataset_id=getattr(args, "dataset_id", None),
            debug=getattr(args, "debug", False),
            theme_provider=getattr(args, "theme_provider", None),
        )

    elif args.command == "run-evolution-pipeline":
        _run_evolution_pipeline_command(
            args.config,
            dataset_id=getattr(args, "dataset_id", None),
            theme_provider=args.theme_provider,
        )

    elif args.command == "pipeline-preflight":
        from src.preflight import PipelinePreflightError, run_pipeline_preflight

        config = validate_config(args.config)
        if args.theme_provider:
            provider_cfg = config.setdefault("theme_provider", {})
            provider_cfg["primary"] = args.theme_provider
        try:
            checks = run_pipeline_preflight(
                config,
                project_root=Path.cwd(),
                check_services=not args.skip_services,
            )
        except PipelinePreflightError as exc:
            for check in exc.checks:
                status = "OK" if check.ok else "FAIL"
                print(f"[{status}] {check.name}: {check.detail}")
            print(str(exc), file=sys.stderr)
            sys.exit(1)
        for check in checks:
            print(f"[OK] {check.name}: {check.detail}")
        print("Pipeline preflight passed.")

    elif args.command == "run-theme-analysis":
        _run_theme_analysis_command(
            args.config, dataset_id=getattr(args, "dataset_id", None)
        )

    elif args.command == "build-report":
        from src.reporting.artifact_index import build_artifact_index

        config = validate_config(args.config, getattr(args, "dataset_id", None))
        report_path = build_artifact_index(config, args.out)
        print(f"Artifact index written to {report_path}")

    elif args.command == "verify-output-contract":
        from src.reporting.output_contract import (
            OutputContractError,
            verify_output_contract,
        )

        config = validate_config(args.config, getattr(args, "dataset_id", None))
        try:
            result = verify_output_contract(config, longitudinal=args.longitudinal)
        except OutputContractError as exc:
            print(f"Output contract verification failed: {exc}", file=sys.stderr)
            sys.exit(1)
        print(f"Output contract verified. Checked {result.checked_count} artifacts.")
        if result.skipped_optional:
            print(
                f"Skipped {len(result.skipped_optional)} optional artifacts that were not present."
            )

    elif args.command == "theme-benchmark":
        _run_theme_benchmark_command(args)


def _import_raw_graph(file_paths, platform, config_path):
    from src.graph_store.memgraph_repository import MemgraphRepository

    config = load_config(config_path) if config_path else {}
    db_config = get_database_config(config)
    repo = MemgraphRepository(
        uri=db_config["uri"],
        user=db_config["user"],
        password=db_config["password"],
    )
    repo.create_indexes()
    for file_path in file_paths:
        print(f"Importing raw graph CSV: {file_path}")
        repo.import_raw_data(file_path, platform)
    print("Raw graph import complete.")


def _run_social_pipeline_command(
    command, config_path, dataset_id=None, debug=False, theme_provider=None
):
    config = validate_config(config_path, dataset_id)
    if theme_provider:
        if "theme_provider" not in config:
            config["theme_provider"] = {}
        config["theme_provider"]["primary"] = theme_provider
    graph_thresholds = config.get("graph_thresholds", {})
    params = _social_pipeline_params(config, graph_thresholds)

    if command == "run-topics":
        from src.pipelines.social_network_pipeline import (
            run_topic_phase_from_saved_inputs,
        )
        from src.topics.topic_inputs import TopicInputError

        print("Running topic pipeline from saved topic inputs...")
        try:
            run_topic_phase_from_saved_inputs(
                output_dir=params["output_dir"],
                data_type=params["data_type"],
                content_type=params["content_type"],
                month=params["month"],
                year=params["year"],
                lda_config=config.get("lda", {}),
            )
        except TopicInputError as exc:
            print(f"Error loading topic inputs: {exc}", file=sys.stderr)
            sys.exit(1)
        print("Pipeline finished successfully!")
        return

    input_path = config.get("input_path", "data/telegram/03_2024.csv")

    # The canonical dashboard path is orchestrated and reads the dataset inside
    # the network task.  Do not load the full CSV here as well: that doubled
    # peak memory and I/O for large Twitter exports.
    if command == "run-all" and not debug:
        from src.orchestration.composition_flow import run_monthly_analysis_flow

        ds_id = dataset_id or config.get("id", "default")
        print(f"Running {command} via Prefect orchestrator...")
        result = run_monthly_analysis_flow(
            config=config,
            dataset_path=input_path,
            dataset_id=ds_id,
            run_topics=True,
            run_themes=True,
        )
        run_id = result.context.pipeline_run_id
        artifact_root = Path(config.get("output_base_path", "results/")).resolve()
        print("Prefect flow finished successfully!")
        print(f"Dashboard run ID: {run_id}")
        print(f"Dashboard artifact root: {artifact_root}")
        print(
            "Start the API with "
            f"COMMUNITY_ANALYSIS_ARTIFACT_ROOT={artifact_root} "
            "uvicorn src.api.app:app --host 0.0.0.0 --port 8000"
        )
        return

    import pandas as pd

    try:
        df = pd.read_csv(input_path, low_memory=False)
    except Exception as exc:
        print(f"Error loading sample data from {input_path}: {exc}", file=sys.stderr)
        sys.exit(1)

    if command == "run-social-network":
        from src.pipelines.social_network_pipeline import (
            run_network_community_pipeline,
        )

        run_network_community_pipeline(df, **params)
        print("Social network analysis finished successfully!")
        print(
            "Note: this stage command writes legacy analytical outputs. "
            "Use run-all to publish a run manifest consumed by the dashboard API."
        )
        return

    print(f"Running {command} in local DEBUG mode (no Prefect)...")
    from src.pipelines.social_network_pipeline import run_full_pipeline

    print("Running full network/community/topic pipeline...")
    runner = run_full_pipeline

    runner(
        df=df,
        lda_config=config.get("lda", {}),
        **params,
    )
    print("Pipeline finished successfully!")


def _run_theme_analysis_command(config_path, dataset_id=None):
    config = validate_config(config_path, dataset_id)
    print("Running run-theme-analysis via Prefect orchestrator...")
    from prefect import flow

    @flow(name="run-theme-analysis")
    def run_theme_wrapper():
        from src.pipelines.theme_pipeline import (
            run_theme_pipeline,
            run_theme_pipeline_from_bundle,
        )
        from src.themes.theme_inputs import ThemeInputError, load_theme_inputs

        theme_config = config.get("theme", {})
        explicit_input_dir = theme_config.get("input_dir") or config.get(
            "theme_input_dir"
        )
        year = str(theme_config.get("year") or config.get("year", "2017"))
        content_type = str(
            theme_config.get("content_type")
            if explicit_input_dir and theme_config.get("content_type")
            else config.get("content_type", "mixed")
        )
        from pathlib import Path

        output_dir = str(
            theme_config.get("output_dir")
            or Path(config.get("output_base_path", "results/"))
            / config.get("data_type", "twitter")
            / "theme_analysis"
            / content_type
        )
        render_visuals = bool(theme_config.get("render_visuals", True))
        similarity_model = theme_config.get(
            "similarity_model", "paraphrase-MiniLM-L6-v2"
        )
        max_theme_workers = max(
            1,
            int(
                theme_config.get(
                    "max_workers", config.get("orchestration", {}).get("max_workers", 4)
                )
            ),
        )

        if explicit_input_dir:
            print(
                f"Running full theme analysis on {explicit_input_dir} for year {year}..."
            )
            if (Path(explicit_input_dir) / "manifest.json").exists():
                import sys

                try:
                    bundle = load_theme_inputs(
                        input_dir=explicit_input_dir,
                        data_type=config.get("data_type", "twitter"),
                        content_type=content_type,
                        year=year,
                        require_manifest=False,
                    )
                except ThemeInputError as exc:
                    print(f"Error loading theme inputs: {exc}", file=sys.stderr)
                    sys.exit(1)
                run_theme_pipeline_from_bundle(
                    bundle,
                    year=year,
                    content_type=content_type,
                    output_dir=output_dir,
                    config=config,
                    render_visuals=render_visuals,
                    similarity_model_name=similarity_model,
                    max_theme_workers=max_theme_workers,
                )
            else:
                run_theme_pipeline(
                    input_dir=str(explicit_input_dir),
                    year=year,
                    content_type=content_type,
                    output_dir=output_dir,
                    config=config,
                    render_visuals=render_visuals,
                    similarity_model_name=similarity_model,
                    max_theme_workers=max_theme_workers,
                )
        else:
            print("Running theme analysis from saved theme inputs...")
            import sys

            try:
                bundle = load_theme_inputs(
                    output_base_path=config.get("output_base_path", "results/"),
                    data_type=config.get("data_type", "twitter"),
                    content_type=config.get("content_type", "mixed"),
                    year=year,
                    require_manifest=True,
                )
            except ThemeInputError as exc:
                print(
                    f"Error loading theme inputs: {exc} "
                    "Run make run-topic-sample first, or use make run-pipeline-sample.",
                    file=sys.stderr,
                )
                sys.exit(1)
            run_theme_pipeline_from_bundle(
                bundle,
                year=year,
                content_type=content_type,
                output_dir=output_dir,
                config=config,
                render_visuals=render_visuals,
                similarity_model_name=similarity_model,
                max_theme_workers=max_theme_workers,
            )

    run_theme_wrapper()
    print("Prefect flow finished successfully!")


def _social_pipeline_params(config, graph_thresholds):
    return {
        "content_type": config.get("content_type", "reply"),
        "data_type": config.get("data_type", "twitter"),
        "month": config.get("month", "march"),
        "year": config.get("year", "2017"),
        "date_column": config.get("date_column", "created_at"),
        "creator_relation": config.get("creator_relation", "REPLIED_TO"),
        "spreader_relation": config.get("spreader_relation", "REPLIED_BY"),
        "creator_node_column": config.get("creator_node_column", "target"),
        "spreader_node_column": config.get("spreader_node_column", "target"),
        "text_node_column_creator_df": config.get("text_node_column", "source"),
        "min_total_post": graph_thresholds.get("min_total_post", 10),
        "min_shared_post": graph_thresholds.get("min_shared_post", 5),
        "min_members": graph_thresholds.get("min_members", 3),
        "output_dir": config.get("output_base_path", "results/"),
        "dashboard_graph_sample_max_edges": max(
            0, int(config.get("dashboard", {}).get("graph_sample_max_edges", 50_000))
        ),
        "louvain_resolution": float(config.get("louvain", {}).get("resolution", 1.0)),
        "louvain_seed": int(config.get("louvain", {}).get("seed", 123)),
    }


def _csv_has_relation_column(file_path):
    import csv

    with open(file_path, "r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration:
            return False
    return "relation" in header


def _default_export_query_name(config):
    data_type = str(config["data_type"])
    content_type = str(config["content_type"])
    if data_type == "telegram":
        return "telegram"
    if data_type == "twitter" and content_type == "reply":
        return "twitter_reply"
    if data_type == "twitter" and content_type in {"retweet", "quote", "retweet_quote"}:
        return "twitter_retweet"
    raise ValueError(
        "Cannot infer Neo4j export query name for "
        f"data_type={data_type!r}, content_type={content_type!r}"
    )


def _run_theme_benchmark_command(args):
    from src.themes.benchmark.contracts import ThemeBenchmarkError
    from src.logging_config import setup_logging

    setup_logging()
    config = validate_config(args.config, getattr(args, "dataset_id", None))
    try:
        if args.benchmark_command == "build-dataset":
            from src.themes.benchmark.dataset import build_dataset

            result = build_dataset(
                config,
                run_id=args.run_id,
                limit=args.limit,
                gpt4o_outputs=args.gpt4o_outputs,
            )
            manifest = result["manifest"]
            print(f"Benchmark dataset written to {result['output_dir']}")
            print(
                "Examples: "
                f"{manifest['example_count']} "
                f"(requested limit: {manifest['limit_requested']})"
            )
            print(f"Dataset hash: {manifest['dataset_hash']}")
            return

        if args.benchmark_command == "inventory-artifacts":
            from src.themes.benchmark.freeze import inventory_artifacts

            source_configs = _load_source_configs(args.source_configs)
            result = inventory_artifacts(config, source_configs=source_configs)
            inventory = result["inventory"]
            print(
                f"Benchmark artifact inventory written to {result['output_dir'] / 'inventory.json'}"
            )
            print(f"Sources: {inventory['source_count']}")
            print(f"Rows: {inventory['row_count']}")
            print(f"Valid examples: {inventory['valid_example_count']}")
            print(f"Rejected rows: {inventory['rejected_row_count']}")
            print(f"Inventory hash: {inventory['inventory_hash']}")
            return

        if args.benchmark_command == "freeze-dataset":
            from src.themes.benchmark.freeze import freeze_dataset

            source_configs = _load_source_configs(args.source_configs)
            result = freeze_dataset(
                config,
                run_id=args.run_id,
                source_configs=source_configs,
                target_examples=args.target_examples,
                min_examples=args.min_examples,
                max_examples=args.max_examples,
                seed=args.seed,
                overwrite=args.overwrite_existing_frozen_run,
            )
            manifest = result["manifest"]
            print(f"Frozen benchmark dataset written to {result['output_dir']}")
            print(f"Available valid examples: {manifest['available_valid_examples']}")
            print(f"Frozen examples: {manifest['example_count']}")
            print(f"Requests: {manifest['request_count']}")
            print(f"Split counts: {manifest['split_counts']}")
            print(f"Dataset hash: {manifest['dataset_hash']}")
            print(f"Split hash: {manifest['split_hash']}")
            return

        if args.benchmark_command == "validate-dataset":
            from src.themes.benchmark.integrity import validate_frozen_dataset

            report = validate_frozen_dataset(
                config.get("output_base_path", "results/"),
                args.run_id,
                expected_dataset_hash=args.expected_dataset_hash,
                expected_split_hash=args.expected_split_hash,
                write_report=True,
            )
            print("Frozen benchmark dataset integrity verified.")
            print(f"Examples: {report['example_count']}")
            print(f"Split counts: {report['split_counts']}")
            print(f"Dataset hash: {report['dataset_hash']}")
            print(f"Split hash: {report['split_hash']}")
            print(
                "Limited source scope: "
                f"data_type={report['limited_to_single_data_type']}, "
                f"content_type={report['limited_to_single_content_type']}, "
                f"year={report['limited_to_single_year']}"
            )
            return

        if args.benchmark_command == "run":
            from src.themes.benchmark.runner import run_benchmark

            provider_ids = [
                provider.strip()
                for provider in args.providers.split(",")
                if provider.strip()
            ]

            benchmark_config = config.get("benchmark", {})
            if "fallback_chain" in benchmark_config:
                chain = benchmark_config["fallback_chain"]
                if isinstance(chain, list) and chain:
                    provider_ids = [f"routing:{','.join(chain)}"]
            keyword_modes = (
                [mode.strip() for mode in args.keyword_modes.split(",") if mode.strip()]
                if args.keyword_modes
                else None
            )
            if args.max_concurrency != 1:
                raise ThemeBenchmarkError(
                    "Only max concurrency 1 is supported for Plan 016B."
                )
            example_ids = _load_example_ids(args.example_ids_file)
            _print_live_benchmark_preflight(
                config=config,
                run_id=args.run_id,
                provider_ids=provider_ids,
                keyword_modes=keyword_modes,
                max_examples=args.max_examples,
                allow_live=args.allow_live,
                split=args.split,
                example_ids=example_ids,
                repetition_index=args.repetition_index,
                max_outbound_requests=args.max_outbound_requests,
                max_retries=args.max_retries,
                timeout=args.timeout,
                max_concurrency=args.max_concurrency,
            )
            report = run_benchmark(
                config,
                run_id=args.run_id,
                provider_ids=provider_ids,
                allow_live=args.allow_live,
                max_examples=args.max_examples,
                keyword_modes=keyword_modes,
                max_retries=args.max_retries,
                timeout=args.timeout,
                max_outbound_requests=args.max_outbound_requests,
                split=args.split,
                resume_unresolved=args.resume_unresolved,
                max_unresolved_examples=args.max_unresolved_examples,
                example_ids=example_ids,
                repetition_index=args.repetition_index,
            )
            print(
                f"Benchmark providers completed: {', '.join(report.providers.keys())}"
            )
            print(f"Requests: {report.request_count}")
            print(f"Results: {report.result_count}")
            print(f"Cache hits: {report.cache_hits}")
            print(f"Cache misses: {report.cache_misses}")
            print(f"Provider executions: {report.provider_executions}")
            print(f"Outbound requests: {report.outbound_requests}")
            print(f"Failures: {report.failures}")
            for provider_id, stats in report.providers.items():
                print(
                    f"Provider {provider_id}: requests={stats.request_count}, "
                    f"results={stats.result_count}, cache_hits={stats.cache_hits}, "
                    f"cache_misses={stats.cache_misses}, "
                    f"provider_executions={stats.provider_executions}, "
                    f"outbound_requests={stats.outbound_requests}, "
                    f"failures={stats.failures}"
                )
            return

        if args.benchmark_command == "discover-models":
            from src.themes.benchmark.dataset import benchmark_root

            root = benchmark_root(
                config.get("output_base_path", "results/"), args.run_id
            )
            if args.provider == "gemini":
                from src.providers.gemini import discover_gemini_models

                path = discover_gemini_models(root, allow_live=args.allow_live)
                print(f"Gemini model catalog written to {path}")
                return
            if args.provider == "llm7":
                from src.providers.llm7 import discover_llm7_models

                path = discover_llm7_models(root, allow_live=args.allow_live)
                print(f"LLM7 model catalog written to {path}")
                return
            raise ThemeBenchmarkError(
                f"Unsupported model discovery provider: {args.provider}"
            )
            return

        if args.benchmark_command == "evaluate-deepeval":
            from src.themes.benchmark.deepeval_judge import evaluate_with_deepeval

            benchmark_config = config.get("benchmark", {})
            judge_provider = benchmark_config.get("evaluator_judge")
            if not judge_provider:
                raise ValueError("benchmark.evaluator_judge must be configured in yaml")

            tracking_uri = config.get("tracking", {}).get(
                "backend_store_path", ".mlflow/mlflow.db"
            )
            if not tracking_uri.startswith("sqlite:///"):
                tracking_uri = f"sqlite:///{tracking_uri}"

            evaluate_with_deepeval(
                config=config,
                dataset_id=args.dataset_id,
                run_id=args.run_id,
                output_base_path=config.get("output_base_path", "results/"),
                tracking_uri=tracking_uri,
            )
            return

        if args.benchmark_command == "export-review":
            from src.themes.benchmark.review import export_blinded_review

            path = export_blinded_review(
                config.get("output_base_path", "results/"), args.run_id
            )
            print(f"Blinded review export written to {path}")
            return

        if args.benchmark_command == "summarize":
            from src.themes.benchmark.metrics import write_phase2_reports

            result = write_phase2_reports(
                config.get("output_base_path", "results/"), args.run_id
            )
            print(f"Preliminary scorecard written to {result['scorecard_path']}")
            print(f"Phase 2 evaluation report written to {result['report_path']}")
            print(f"Completion status: {result['report']['completion_status']}")
            return

        raise ThemeBenchmarkError(
            f"Unknown theme-benchmark command: {args.benchmark_command}"
        )
    except (ThemeBenchmarkError, ValueError) as exc:
        print(f"Theme benchmark failed: {exc}", file=sys.stderr)
        sys.exit(1)


def _load_source_configs(source_configs):
    if not source_configs:
        return None
    paths = [item.strip() for item in source_configs.split(",") if item.strip()]
    return [load_config(path) for path in paths]


def _load_example_ids(path):
    if not path:
        return None
    import json

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    values = (
        data.get("example_ids") or data.get("subset_example_ids")
        if isinstance(data, dict)
        else data
    )
    if not isinstance(values, list):
        raise ValueError(
            f"Example ID file must contain a list or example_ids field: {path}"
        )
    return [str(value) for value in values]


def _print_live_benchmark_preflight(
    *,
    config,
    run_id,
    provider_ids,
    keyword_modes,
    max_examples,
    allow_live,
    max_outbound_requests,
    max_retries,
    timeout,
    max_concurrency,
    split=None,
    example_ids=None,
    repetition_index=None,
):
    live_provider_ids = [
        provider_id
        for provider_id in provider_ids
        if provider_id.startswith(("gemini:", "llm7:"))
    ]
    if not allow_live or not live_provider_ids:
        return

    from src.themes.benchmark.contracts import read_jsonl
    from src.themes.benchmark.dataset import benchmark_root, load_requests
    from src.themes.benchmark.integrity import (
        filter_examples_by_split,
        validate_frozen_dataset,
    )
    from src.themes.benchmark.runner import _filter_requests

    effective_keyword_modes = keyword_modes or ["general"]
    split_example_ids = None
    if split:
        output_base_path = config.get("output_base_path", "results/")
        validate_frozen_dataset(output_base_path, run_id, write_report=True)
        root = benchmark_root(output_base_path, run_id)
        dataset_rows = read_jsonl(root / "dataset.jsonl")
        split_example_ids = filter_examples_by_split(
            [
                str(request.example_id)
                for request in load_requests(output_base_path, run_id)
            ],
            dataset_rows,
            split,
        )
    if example_ids:
        example_set = set(example_ids)
        split_example_ids = (
            example_set
            if split_example_ids is None
            else split_example_ids.intersection(example_set)
        )
    requests = _filter_requests(
        load_requests(config.get("output_base_path", "results/"), run_id),
        max_examples=max_examples,
        keyword_modes=effective_keyword_modes,
        split_example_ids=split_example_ids,
    )
    example_count = len({request.example_id for request in requests})
    model_ids = [provider_id.split(":", 1)[1] for provider_id in live_provider_ids]
    provider_prefixes = {
        provider_id.split(":", 1)[0] for provider_id in live_provider_ids
    }

    print("Live benchmark preflight:")
    print(f"Selected model IDs: {', '.join(model_ids)}")
    print(f"Example count: {example_count}")
    if split:
        print(f"Split: {split}")
    if repetition_index is not None:
        print(f"Repetition index: {repetition_index}")
    print(f"Keyword modes: {', '.join(effective_keyword_modes)}")
    print(f"Normal request count: {len(requests) * len(live_provider_ids)}")
    print(f"Max outbound requests: {max_outbound_requests}")
    print(f"Max retries: {max_retries}")
    print(f"Timeout: {timeout}")
    print(f"Concurrency: {max_concurrency}")
    if "gemini" in provider_prefixes:
        print("Gemini store=False")


def _run_evolution_pipeline_command(
    config_path, dataset_id=None, debug=False, theme_provider=None
):
    config = validate_config(config_path, dataset_id)
    if theme_provider:
        if "theme_provider" not in config:
            config["theme_provider"] = {}
        config["theme_provider"]["primary"] = theme_provider

    from src.orchestration.composition_flow import run_evolution_analysis_flow

    print("Running run-evolution-pipeline via Prefect orchestrator...")
    run_evolution_analysis_flow(config=config)
    print("Prefect flow finished successfully!")


if __name__ == "__main__":
    main()
