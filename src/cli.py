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

def validate_config(config_path):
    print(f"Validating config: {config_path}")
    try:
        config = load_config(config_path)
        validate_run_config(config)
        print("Config is valid.")
        return config
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Community Analysis Intelligence Platform")
    subparsers = parser.add_subparsers(dest='command', required=True)

    # validate-config command
    parser_validate = subparsers.add_parser('validate-config', help='Validate a configuration file')
    parser_validate.add_argument('--config', required=True, help='Path to config file')

    # export-graph command
    parser_export = subparsers.add_parser('export-graph', help='Export graph relationships')
    parser_export.add_argument('--config', required=True, help='Path to config file')
    parser_export.add_argument('--output', required=False, help='Output CSV path')
    parser_export.add_argument('--query-name', required=False, help='Exporter query name override')

    parser_db_check = subparsers.add_parser('db-check', help='Check Memgraph connectivity')
    parser_db_check.add_argument('--config', required=False, help='Path to config file')

    subparsers.add_parser('db-up', help='Start local Memgraph using Docker Compose')

    parser_import_graph = subparsers.add_parser('import-graph', help='Import legacy source,target,relation CSV into Memgraph')
    parser_import_graph.add_argument('--file', nargs='+', required=True, help='Path to one or more legacy CSV files')
    parser_import_graph.add_argument('--platform', required=True, choices=['telegram', 'twitter'], help='Platform of the data')
    parser_import_graph.add_argument('--config', required=False, help='Path to config file')

    parser_ingest_interactions = subparsers.add_parser('ingest-interactions', help='Build/import monthly interaction CSV into Memgraph')
    parser_ingest_interactions.add_argument('--file', required=True, help='Path to raw legacy CSV or derived interaction CSV')
    parser_ingest_interactions.add_argument('--config', required=True, help='Path to config file')
    parser_ingest_interactions.add_argument('--out', required=False, help='Derived interaction CSV output path when --file is raw')
    parser_ingest_interactions.add_argument('--no-db', action='store_true', help='Build derived CSV without importing into Memgraph')

    # run-social-network command
    parser_social = subparsers.add_parser('run-social-network', help='Run social network analysis')
    parser_social.add_argument('--config', required=True, help='Path to config file')

    # run-topics command
    parser_topics = subparsers.add_parser('run-topics', help='Run topic modeling')
    parser_topics.add_argument('--config', required=True, help='Path to config file')

    # run-theme-analysis command
    parser_theme = subparsers.add_parser('run-theme-analysis', help='Run theme generation and transition analysis')
    parser_theme.add_argument('--config', required=True, help='Path to config file')

    # run-all command
    parser_all = subparsers.add_parser('run-all', help='Run the full pipeline')
    parser_all.add_argument('--config', required=True, help='Path to config file')

    parser_report = subparsers.add_parser('build-report', help='Build a markdown artifact index')
    parser_report.add_argument('--config', required=True, help='Path to config file')
    parser_report.add_argument('--out', required=False, default='/tmp/community-analysis-artifact-index.md', help='Report output path')

    # import-csv command
    parser_import = subparsers.add_parser('import-csv', help='Backward-compatible alias for import-graph')
    parser_import.add_argument('--file', nargs='+', required=True, help='Path to one or more CSV files')
    parser_import.add_argument('--platform', required=True, choices=['telegram', 'twitter'], help='Platform of the data')
    parser_import.add_argument('--config', required=False, help='Path to config file')

    args = parser.parse_args()

    if args.command == 'validate-config':
        validate_config(args.config)

    elif args.command == 'db-check':
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

    elif args.command == 'db-up':
        subprocess.run(["docker", "compose", "up", "-d", "memgraph"], check=True)
        print("Memgraph startup requested via Docker Compose.")
        
    elif args.command == 'import-csv':
        _import_raw_graph(args.file, args.platform, args.config)

    elif args.command == 'import-graph':
        _import_raw_graph(args.file, args.platform, args.config)

    elif args.command == 'ingest-interactions':
        config = validate_config(args.config)
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
        
    elif args.command == 'export-graph':
        from src.graph_store.neo4j_exporter import Neo4jExporter

        config = validate_config(args.config)
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
        
    elif args.command in ['run-social-network', 'run-topics', 'run-all']:
        _run_social_pipeline_command(args.command, args.config)
        
    elif args.command == 'run-theme-analysis':
        _run_theme_analysis_command(args.config)

    elif args.command == 'build-report':
        from src.reporting.artifact_index import build_artifact_index

        config = validate_config(args.config)
        report_path = build_artifact_index(config, args.out)
        print(f"Artifact index written to {report_path}")


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


def _run_social_pipeline_command(command, config_path):
    config = validate_config(config_path)
    graph_thresholds = config.get('graph_thresholds', {})
    params = _social_pipeline_params(config, graph_thresholds)

    if command == 'run-topics':
        from src.pipelines.social_network_pipeline import run_topic_phase_from_saved_inputs
        from src.topics.topic_inputs import TopicInputError

        print("Running topic pipeline from saved topic inputs...")
        try:
            run_topic_phase_from_saved_inputs(
                output_dir=params["output_dir"],
                data_type=params["data_type"],
                content_type=params["content_type"],
                month=params["month"],
                year=params["year"],
            )
        except TopicInputError as exc:
            print(f"Error loading topic inputs: {exc}", file=sys.stderr)
            sys.exit(1)
        print("Pipeline finished successfully!")
        return

    import pandas as pd

    input_path = config.get('input_path', 'data/telegram/03_2024.csv')
    try:
        df = pd.read_csv(input_path, low_memory=False)
    except Exception as e:
        print(f"Error loading sample data from {input_path}: {e}")
        return

    if command == 'run-social-network':
        from src.pipelines.social_network_pipeline import run_network_community_pipeline

        print("Running network/community pipeline...")
        runner = run_network_community_pipeline
    else:
        from src.pipelines.social_network_pipeline import run_full_pipeline

        print("Running full network/community/topic pipeline...")
        runner = run_full_pipeline

    runner(
        df=df,
        **params,
    )
    print("Pipeline finished successfully!")


def _run_theme_analysis_command(config_path):
    from src.pipelines.theme_pipeline import run_theme_pipeline, run_theme_pipeline_from_bundle
    from src.themes.theme_inputs import ThemeInputError, load_theme_inputs

    config = validate_config(config_path)
    theme_config = config.get("theme", {})
    explicit_input_dir = theme_config.get("input_dir") or config.get("theme_input_dir")
    year = str(theme_config.get("year") or config.get("year", "2017"))
    content_type = str(
        theme_config.get("content_type")
        if explicit_input_dir and theme_config.get("content_type")
        else config.get("content_type", "mixed")
    )
    output_dir = str(
        theme_config.get("output_dir")
        or Path(config.get("output_base_path", "results/"))
        / config.get("data_type", "twitter")
        / "theme_analysis"
        / content_type
    )
    render_visuals = bool(theme_config.get("render_visuals", True))
    similarity_model = theme_config.get("similarity_model", "paraphrase-MiniLM-L6-v2")

    if explicit_input_dir:
        print(f"Running full theme analysis on {explicit_input_dir} for year {year}...")
        if (Path(explicit_input_dir) / "manifest.json").exists():
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
                render_visuals=render_visuals,
                similarity_model_name=similarity_model,
            )
        else:
            run_theme_pipeline(
                input_dir=str(explicit_input_dir),
                year=year,
                content_type=content_type,
                output_dir=output_dir,
                render_visuals=render_visuals,
                similarity_model_name=similarity_model,
            )
    else:
        print("Running theme analysis from saved theme inputs...")
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
            render_visuals=render_visuals,
            similarity_model_name=similarity_model,
        )
    print("Theme analysis finished successfully!")


def _social_pipeline_params(config, graph_thresholds):
    return {
        "content_type": config.get('content_type', 'reply'),
        "data_type": config.get('data_type', 'twitter'),
        "month": config.get('month', 'march'),
        "year": config.get('year', '2017'),
        "date_column": config.get('date_column', 'created_at'),
        "creator_relation": config.get('creator_relation', 'REPLIED_TO'),
        "spreader_relation": config.get('spreader_relation', 'REPLIED_BY'),
        "creator_node_column": config.get('creator_node_column', 'target'),
        "spreader_node_column": config.get('spreader_node_column', 'target'),
        "text_node_column_creator_df": config.get('text_node_column', 'source'),
        "min_total_post": graph_thresholds.get('min_total_post', 10),
        "min_shared_post": graph_thresholds.get('min_shared_post', 5),
        "min_members": graph_thresholds.get('min_members', 3),
        "output_dir": config.get('output_base_path', 'results/'),
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


if __name__ == '__main__':
    main()
