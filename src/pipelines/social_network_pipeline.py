import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.ingestion.network_data_extractor import (
    get_creator_spreader,
    create_user_df,
    create_network_df,
)
from src.network.follower_followee import get_follower_followee_network
from src.network.graphs import get_network_graph
from src.network.centrality import get_prominent_communities_stat

from src.communities.louvain import (
    get_louvain_community,
    detect_prominent_communities,
    get_prominent_communities,
)
from src.communities.messages import (
    build_community_message_index,
    get_community_messages,
    get_overall_community_messages_stat,
)
from src.communities.interactions import build_prominent_community_interactions
from src.communities.similarity import find_matching_communities

logger = logging.getLogger(__name__)


def save_parquet_to_directory(
    base_dir: str, subfolder: str, filename: str, data: pd.DataFrame
):
    """Persist a generated pipeline dataframe as Parquet."""
    if data is None:
        return

    path = Path(base_dir) / subfolder
    path.mkdir(parents=True, exist_ok=True)

    if Path(filename).suffix.lower() != ".parquet":
        raise ValueError(f"Generated pipeline artifact must be Parquet: {filename}")
    parquet_path = path / filename
    data.to_parquet(parquet_path, index=False)
    logger.info("artifact_saved path=%s rows=%d", parquet_path.resolve(), len(data))
    return parquet_path


def _dashboard_graph_sample(frame: pd.DataFrame, *, max_edges: int) -> pd.DataFrame:
    """Return a deterministic, weight-ranked graph sample for dashboard reads.

    The complete community graph remains the authoritative thesis artifact. This
    additive sample prevents the global dashboard graph endpoint from scanning and
    sorting millions of edges for every request.
    """
    if frame is None:
        return pd.DataFrame(
            columns=["source", "target", "community_number", "direction", "weight"]
        )
    if max_edges <= 0 or frame.empty:
        return frame.head(0).copy()

    sampled = frame.copy()
    sampled["weight"] = pd.to_numeric(sampled["weight"], errors="coerce").fillna(0.0)
    sampled["source"] = sampled["source"].astype(str)
    sampled["target"] = sampled["target"].astype(str)
    sampled["community_number"] = sampled["community_number"].astype(str)
    return (
        sampled.sort_values(
            ["weight", "community_number", "source", "target"],
            ascending=[False, True, True, True],
            kind="stable",
        )
        .head(int(max_edges))
        .reset_index(drop=True)
    )


def _community_summary(
    frame: pd.DataFrame, interactions: pd.DataFrame | None = None
) -> pd.DataFrame:
    columns = ["community_id", "node_count", "edge_count", "total_weight"]
    if interactions is not None:
        columns.extend(["x", "y"])

    if frame is None or frame.empty:
        return pd.DataFrame(columns=columns)

    normalized = frame[["community_number", "source", "target", "weight"]].copy()
    normalized["weight"] = pd.to_numeric(normalized["weight"], errors="coerce").fillna(
        0.0
    )
    aggregate = (
        normalized.groupby("community_number", sort=True, observed=True)
        .agg(edge_count=("source", "size"), total_weight=("weight", "sum"))
        .reset_index()
    )
    nodes = pd.concat(
        [
            normalized[["community_number", "source"]].rename(
                columns={"source": "node"}
            ),
            normalized[["community_number", "target"]].rename(
                columns={"target": "node"}
            ),
        ],
        ignore_index=True,
    )
    node_counts = (
        nodes.assign(node=nodes["node"].astype(str))
        .drop_duplicates(["community_number", "node"])
        .groupby("community_number", sort=True, observed=True)
        .size()
        .rename("node_count")
        .reset_index()
    )
    summary = aggregate.merge(node_counts, on="community_number", how="left")
    summary = summary.rename(columns={"community_number": "community_id"})
    summary["community_id"] = summary["community_id"].astype(str)
    summary["node_count"] = summary["node_count"].fillna(0).astype(int)
    summary["edge_count"] = summary["edge_count"].astype(int)
    summary["total_weight"] = summary["total_weight"].astype(float)

    if interactions is not None:
        if not interactions.empty:
            import networkx as nx

            G = nx.from_pandas_edgelist(
                interactions,
                source="source_community_id",
                target="target_community_id",
                edge_attr=["total_weight"],
                create_using=nx.Graph(),
            )
            G.add_nodes_from(summary["community_id"])
            layout = nx.spring_layout(G, seed=42)

            coords = [
                (
                    (
                        str(node),
                        float(layout[node][0] * 1000),
                        float(layout[node][1] * 1000),
                    )
                    if node in layout
                    else (str(node), 0.0, 0.0)
                )
                for node in summary["community_id"]
            ]

            coords_df = pd.DataFrame(coords, columns=["community_id", "x", "y"])
            summary = summary.merge(coords_df, on="community_id", how="left")
        else:
            summary["x"] = 0.0
            summary["y"] = 0.0

    return summary[columns]


def _community_node_index(frame: pd.DataFrame) -> pd.DataFrame:
    """Return unique graph node IDs and their pre-calculated layout coordinates."""
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["node_id", "x", "y"])

    # Extract unique nodes
    nodes = (
        pd.concat(
            [frame["source"], frame["target"]],
            ignore_index=True,
        )
        .dropna()
        .astype(str)
        .drop_duplicates()
        .sort_values()
        .reset_index(drop=True)
    )

    # Calculate layout using networkx
    import networkx as nx

    G = nx.from_pandas_edgelist(
        frame, "source", "target", ["weight"], create_using=nx.Graph()
    )
    # Ensure all nodes are present in G
    G.add_nodes_from(nodes)

    # spring_layout provides good results for force-directed graphs
    # We use a fixed seed for reproducibility
    layout = nx.spring_layout(G, seed=42)

    # Default coordinates to 0.0 if missing (shouldn't happen, but safe)
    # We scale coordinates up slightly to match the expected ForceGraph space
    coords = [
        (
            (str(node), float(layout[node][0] * 1000), float(layout[node][1] * 1000))
            if node in layout
            else (str(node), 0.0, 0.0)
        )
        for node in nodes
    ]

    df = pd.DataFrame(coords, columns=["node_id", "x", "y"])
    return df


def run_network_phase(
    df_data: pd.DataFrame,
    content_type: str,
    creator_relation: str,
    spreader_relation: str,
    creator_node_column: str,
    spreader_node_column: str,
    text_node_column_creator_df: str,
    data_type: str,
    month: str,
    year: str,
    output_dir: str,
    min_total_post: int = 10,
    min_shared_post: int = 5,
):
    phase_started = time.perf_counter()
    logger.info(
        "network_extraction_started data_type=%s content_type=%s rows=%d",
        data_type,
        content_type,
        len(df_data),
    )

    if data_type == "telegram":
        from src.pipelines.ingestion_pipeline import normalize_network_input

        df_network = normalize_network_input(
            df_data,
            {
                "data_type": data_type,
                "content_type": content_type,
                "creator_relation": creator_relation,
                "spreader_relation": spreader_relation,
                "creator_node_column": creator_node_column,
                "spreader_node_column": spreader_node_column,
                "text_node_column": text_node_column_creator_df,
            },
        ).copy()
        # Create synthetic df_user for telegram from from_id and forwarder_id
        unique_users = set(df_network["from_id"].dropna().unique()).union(
            set(df_network["forwarder_id"].dropna().unique())
        )
        df_user = pd.DataFrame({"user_id": list(unique_users)})
        df_user["username"] = "anonymous" + df_user["user_id"].astype(str)
    else:
        df_creator, df_spreader = get_creator_spreader(
            df_data, creator_relation, spreader_relation
        )
        df_user = create_user_df(
            df_spreader, df_creator, creator_node_column, spreader_node_column
        )
        df_network = create_network_df(df_creator, text_node_column_creator_df)

    followee_follower_df = get_follower_followee_network(df_network)

    # Save network data
    save_parquet_to_directory(
        os.path.join(output_dir, data_type, "network_data"),
        content_type,
        f"{month}{year}.parquet",
        df_network,
    )

    logger.info(
        "network_extraction_completed network_rows=%d users=%d " "elapsed_seconds=%.2f",
        len(df_network),
        len(df_user),
        time.perf_counter() - phase_started,
    )
    graph_started = time.perf_counter()
    logger.info(
        "graph_construction_started interaction_rows=%d", len(followee_follower_df)
    )
    G_absolute, G_percentage = get_network_graph(
        followee_follower_df,
        min_total_post=min_total_post,
        min_shared_post=min_shared_post,
    )

    logger.info(
        "graph_construction_completed absolute_nodes=%d absolute_edges=%d "
        "weighted_nodes=%d weighted_edges=%d elapsed_seconds=%.2f",
        G_absolute.number_of_nodes(),
        G_absolute.number_of_edges(),
        G_percentage.number_of_nodes(),
        G_percentage.number_of_edges(),
        time.perf_counter() - graph_started,
    )
    return G_absolute, G_percentage, df_network, df_user


def run_community_phase(
    G_absolute,
    G_percentage,
    df_network: pd.DataFrame,
    df_user: pd.DataFrame,
    min_members: int,
    date_column: str,
    month: str,
    data_type: str,
    content_type: str,
    output_dir: str,
    dashboard_graph_sample_max_edges: int = 50_000,
    louvain_resolution: float = 1.0,
    louvain_seed: int = 123,
):
    logger.info(
        "louvain_started resolution=%s seed=%s", louvain_resolution, louvain_seed
    )
    abs_com, abs_part = get_louvain_community(
        G_absolute,
        "shared_post",
        resolution=louvain_resolution,
        seed=louvain_seed,
    )
    per_com, per_part = get_louvain_community(
        G_percentage,
        "weighted_post",
        resolution=louvain_resolution,
        seed=louvain_seed,
    )

    logger.info(
        "louvain_completed absolute_communities=%d weighted_communities=%d",
        len(abs_com),
        len(per_com),
    )
    logger.info("prominent_community_filter_started min_members=%d", min_members)
    prominent_communities_abs = detect_prominent_communities(abs_com, min_members)
    prominent_communities_per = detect_prominent_communities(per_com, min_members)

    abs_community = get_prominent_communities(
        prominent_communities_abs, G_absolute, "shared_post"
    )
    per_community = get_prominent_communities(
        prominent_communities_per, G_percentage, "weighted_post"
    )

    # Additive dashboard read models preserve the metric-local Louvain
    # memberships while aggregating only genuine cross-community user
    # interactions from the already-filtered monthly graph.
    abs_community_interactions = build_prominent_community_interactions(
        G_absolute,
        prominent_communities_abs,
        weight_attribute="shared_post",
    )
    per_community_interactions = build_prominent_community_interactions(
        G_percentage,
        prominent_communities_per,
        weight_attribute="weighted_post",
        interaction_graph=G_absolute,
    )

    message_index_started = time.perf_counter()
    logger.info(
        "community_message_index_started network_rows=%d absolute_communities=%d weighted_communities=%d",
        len(df_network),
        len(prominent_communities_abs),
        len(prominent_communities_per),
    )
    message_index = build_community_message_index(
        df_network, df_user, date_columns=(date_column,)
    )
    logger.info(
        "community_message_index_completed indexed_edges=%d elapsed_seconds=%.2f",
        len(message_index.edge_positions),
        time.perf_counter() - message_index_started,
    )
    abs_community_messages = get_community_messages(
        prominent_communities_abs,
        abs_community,
        df_network,
        df_user,
        message_index=message_index,
        progress_label="absolute_community_messages",
    )
    per_community_messages = get_community_messages(
        prominent_communities_per,
        per_community,
        df_network,
        df_user,
        message_index=message_index,
        progress_label="weighted_community_messages",
    )

    logger.info(
        "community_message_extraction_completed absolute_messages=%d "
        "weighted_messages=%d",
        (
            int(abs_community_messages["total_messages"].sum())
            if not abs_community_messages.empty
            else 0
        ),
        (
            int(per_community_messages["total_messages"].sum())
            if not per_community_messages.empty
            else 0
        ),
    )
    logger.info("centrality_started")
    abs_degree = get_prominent_communities_stat(
        prominent_communities_abs, G_absolute, df_user
    )
    per_degree = get_prominent_communities_stat(
        prominent_communities_per, G_percentage, df_user
    )

    df_user_centrality = pd.DataFrame(
        {
            "month": [month],
            "absolute": [json.dumps(abs_degree)],
            "weighted": [json.dumps(per_degree)],
        }
    )
    save_parquet_to_directory(
        os.path.join(output_dir, data_type, "user_centrality"),
        content_type,
        f"{month}.parquet",
        df_user_centrality,
    )

    logger.info("dashboard_community_artifacts_started")
    if not abs_community.empty:
        save_parquet_to_directory(
            os.path.join(output_dir, data_type, "communities", "graphs", "absolute"),
            content_type,
            f"{month}.parquet",
            abs_community,
        )
    if not per_community.empty:
        save_parquet_to_directory(
            os.path.join(output_dir, data_type, "communities", "graphs", "weighted"),
            content_type,
            f"{month}.parquet",
            per_community,
        )

    # Additive, deterministic samples make the global dashboard graph bounded.
    # Community detail requests continue to use the complete graph artifact.
    save_parquet_to_directory(
        os.path.join(output_dir, data_type, "communities", "graph_samples", "absolute"),
        content_type,
        f"{month}.parquet",
        _dashboard_graph_sample(
            abs_community, max_edges=dashboard_graph_sample_max_edges
        ),
    )
    save_parquet_to_directory(
        os.path.join(output_dir, data_type, "communities", "graph_samples", "weighted"),
        content_type,
        f"{month}.parquet",
        _dashboard_graph_sample(
            per_community, max_edges=dashboard_graph_sample_max_edges
        ),
    )

    # Small dashboard-ready summaries avoid grouping every graph edge for each
    # communities API request.  They are additive and do not replace thesis
    # graph outputs.
    save_parquet_to_directory(
        os.path.join(output_dir, data_type, "communities", "summary", "absolute"),
        content_type,
        f"{month}.parquet",
        _community_summary(abs_community, abs_community_interactions),
    )
    save_parquet_to_directory(
        os.path.join(output_dir, data_type, "communities", "summary", "weighted"),
        content_type,
        f"{month}.parquet",
        _community_summary(per_community, per_community_interactions),
    )
    save_parquet_to_directory(
        os.path.join(output_dir, data_type, "communities", "interactions", "absolute"),
        content_type,
        f"{month}.parquet",
        abs_community_interactions,
    )
    save_parquet_to_directory(
        os.path.join(output_dir, data_type, "communities", "interactions", "weighted"),
        content_type,
        f"{month}.parquet",
        per_community_interactions,
    )
    # Compact one-column indexes let the API calculate exact cross-month node
    # counts without loading every authoritative graph edge.
    save_parquet_to_directory(
        os.path.join(output_dir, data_type, "communities", "node_index", "absolute"),
        content_type,
        f"{month}.parquet",
        _community_node_index(abs_community),
    )
    save_parquet_to_directory(
        os.path.join(output_dir, data_type, "communities", "node_index", "weighted"),
        content_type,
        f"{month}.parquet",
        _community_node_index(per_community),
    )

    logger.info("community_counts_started")
    total_abs_users = (
        len(set(abs_community["source"].to_list() + abs_community["target"].to_list()))
        if not abs_community.empty
        else 0
    )
    total_per_users = (
        len(set(per_community["source"].to_list() + per_community["target"].to_list()))
        if not per_community.empty
        else 0
    )

    df_user_messages_count = pd.DataFrame(
        {
            "month": [month],
            "user": [
                json.dumps({"absolute": total_abs_users, "weighted": total_per_users})
            ],
            "messages": [
                json.dumps(
                    {
                        "absolute": int(
                            abs_community_messages["total_messages"].sum()
                            if not abs_community_messages.empty
                            else 0
                        ),
                        "weighted": int(
                            per_community_messages["total_messages"].sum()
                            if not per_community_messages.empty
                            else 0
                        ),
                    }
                )
            ],
        }
    )
    save_parquet_to_directory(
        os.path.join(output_dir, data_type, "count_user_messages"),
        content_type,
        f"{month}.parquet",
        df_user_messages_count,
    )

    logger.info("daily_message_stats_started")
    abs_msg_stat = get_overall_community_messages_stat(
        date_column,
        prominent_communities_abs,
        abs_community,
        df_network,
        message_index=message_index,
    )
    per_msg_stat = get_overall_community_messages_stat(
        date_column,
        prominent_communities_per,
        per_community,
        df_network,
        message_index=message_index,
    )

    def _json_default(obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return str(obj)

    df_daily_messages_stat = pd.DataFrame(
        {
            "month": [month],
            "absolute": [json.dumps(abs_msg_stat, default=_json_default)],
            "weighted": [json.dumps(per_msg_stat, default=_json_default)],
        }
    )
    save_parquet_to_directory(
        os.path.join(output_dir, data_type, "daily_messages_stat"),
        content_type,
        f"{month}.parquet",
        df_daily_messages_stat,
    )

    logger.info("community_matching_started")
    matched_df, partial_matched, unmatched_abs, unmatched_per = (
        find_matching_communities(abs_community, per_community)
    )

    df_number_of_community = pd.DataFrame(
        {
            "month": [month],
            "total_matched": [len(matched_df)],
            "total_absolute": [len(prominent_communities_abs)],
            "total_weighted": [len(prominent_communities_per)],
        }
    )
    save_parquet_to_directory(
        os.path.join(output_dir, data_type, "communities", "matched"),
        content_type,
        f"{month}.parquet",
        df_number_of_community,
    )

    partial_matched_community = partial_matched.copy()
    if not partial_matched_community.empty:
        partial_matched_community.rename(
            columns={"abs_community": "absolute", "per_community": "weighted"},
            inplace=True,
        )
        partial_matched_community["month"] = month
        df_partial_matched_community = partial_matched_community[
            ["month", "absolute", "weighted", "jaccard_score"]
        ]
        save_parquet_to_directory(
            os.path.join(output_dir, data_type, "communities", "partially_matched"),
            content_type,
            f"{month}.parquet",
            df_partial_matched_community,
        )

    return abs_community_messages, per_community_messages, matched_df, partial_matched


def run_topic_phase(
    abs_community_messages: pd.DataFrame,
    per_community_messages: pd.DataFrame,
    matched_df: pd.DataFrame,
    partial_matched: pd.DataFrame,
    month: str,
    year: str,
    data_type: str,
    content_type: str,
    output_dir: str,
    lda_config: dict[str, Any] | None = None,
    translation_config: dict[str, Any] | None = None,
):
    from src.topics.lda import get_bigram_lda, get_unigram_lda
    from src.topics.text_preprocessor import message_preprocess
    from src.topics.topic_matching import get_matched_topic_df

    phase_started = time.perf_counter()
    logger.info(
        "topic_phase_started month=%s absolute_communities=%d "
        "weighted_communities=%d",
        month,
        len(abs_community_messages),
        len(per_community_messages),
    )

    translation_settings = dict(translation_config or {})
    if bool(translation_settings.get("enabled", False)):
        from src.text.translation import prepare_translated_topic_messages

        translation_result = prepare_translated_topic_messages(
            abs_community_messages,
            per_community_messages,
            translation_config=translation_settings,
            output_dir=output_dir,
            data_type=data_type,
            content_type=content_type,
            year=year,
            month=month,
        )
        abs_community_messages = translation_result.absolute_community_messages
        per_community_messages = translation_result.weighted_community_messages

    preprocessing_started = time.perf_counter()
    if not abs_community_messages.empty:
        abs_community_messages = abs_community_messages.copy()
        abs_community_messages["messages_processed"] = message_preprocess(
            abs_community_messages
        )
    if not per_community_messages.empty:
        per_community_messages = per_community_messages.copy()
        per_community_messages["messages_processed"] = message_preprocess(
            per_community_messages
        )
    logger.info(
        "topic_preprocessing_completed elapsed_seconds=%.2f",
        time.perf_counter() - preprocessing_started,
    )

    def _run_lda_model(label: str, function, frame: pd.DataFrame):
        if frame.empty:
            logger.info("lda_model_skipped model=%s reason=empty_input", label)
            return pd.DataFrame(), None, 0.0, 0.0

        started = time.perf_counter()
        logger.info(
            "lda_model_started model=%s communities=%d",
            label,
            len(frame),
        )
        result = function(frame, lda_config=lda_config)
        document_topics, model, perplexity, coherence = result
        logger.info(
            "lda_model_completed model=%s documents=%d perplexity=%.6f "
            "coherence=%.6f elapsed_seconds=%.2f",
            label,
            len(document_topics),
            float(perplexity),
            float(coherence),
            time.perf_counter() - started,
        )
        return document_topics, model, perplexity, coherence

    uni_doc_topics_abs, lda_abs, perplexity_abs, coherence_abs = _run_lda_model(
        "unigram_absolute", get_unigram_lda, abs_community_messages
    )
    uni_doc_topics_per, lda_per, perplexity_per, coherence_per = _run_lda_model(
        "unigram_weighted", get_unigram_lda, per_community_messages
    )
    bi_doc_topics_abs, bi_lda_abs, perplexity_bi_abs, coherence_bi_abs = _run_lda_model(
        "bigram_absolute", get_bigram_lda, abs_community_messages
    )
    bi_doc_topics_per, bi_lda_per, perplexity_bi_per, coherence_bi_per = _run_lda_model(
        "bigram_weighted", get_bigram_lda, per_community_messages
    )

    df_lda_scores = pd.DataFrame(
        {
            "month": [month],
            "unigram_absolute": [[perplexity_abs, coherence_abs]],
            "unigram_weighted": [[perplexity_per, coherence_per]],
            "bigram_absolute": [[perplexity_bi_abs, coherence_bi_abs]],
            "bigram_weighted": [[perplexity_bi_per, coherence_bi_per]],
        }
    )
    save_parquet_to_directory(
        os.path.join(output_dir, data_type, "LDA", "scores"),
        content_type,
        f"{month}.parquet",
        df_lda_scores,
    )

    matched_communities = [
        (row.abs_community, row.per_community)
        for row in matched_df.itertuples(index=False)
    ]
    logger.info(
        "matched_topic_extraction_started matched_pairs=%d",
        len(matched_communities),
    )
    if matched_communities and lda_abs is not None and lda_per is not None:
        matched_topic_df = get_matched_topic_df(
            lda_models=[lda_abs, lda_per, bi_lda_abs, bi_lda_per],
            dfs=[
                uni_doc_topics_abs,
                uni_doc_topics_per,
                bi_doc_topics_abs,
                bi_doc_topics_per,
            ],
            community_id_pairs=matched_communities,
        )
        merged_match = pd.merge(
            matched_topic_df,
            matched_df[["abs_community", "members", "per_community"]],
            left_on=["absolute_community", "weighted_community"],
            right_on=["abs_community", "per_community"],
            how="inner",
        ).drop(["abs_community", "per_community"], axis=1)

        if not merged_match.empty:
            matched_parquet = save_parquet_to_directory(
                os.path.join(output_dir, data_type, "LDA", "matched"),
                content_type,
                f"{month}_{year}.parquet",
                merged_match,
            )
            save_pipeline_theme_inputs(
                matched_lda_csv=matched_parquet,
                month=month,
                year=year,
                data_type=data_type,
                content_type=content_type,
                output_dir=output_dir,
            )

    partial_communities = [
        (row.abs_community, row.per_community)
        for row in partial_matched.itertuples(index=False)
    ]
    logger.info(
        "partial_topic_extraction_started partial_pairs=%d",
        len(partial_communities),
    )
    if partial_communities and lda_abs is not None and lda_per is not None:
        partial_matched_topic_df = get_matched_topic_df(
            lda_models=[lda_abs, lda_per, bi_lda_abs, bi_lda_per],
            dfs=[
                uni_doc_topics_abs,
                uni_doc_topics_per,
                bi_doc_topics_abs,
                bi_doc_topics_per,
            ],
            community_id_pairs=partial_communities,
        )
        merge_partial = pd.merge(
            partial_matched_topic_df,
            partial_matched[
                [
                    "abs_community",
                    "absolute_members",
                    "weighted_members",
                    "jaccard_score",
                    "common_members",
                    "uncommon_members",
                    "per_community",
                ]
            ],
            left_on=["absolute_community", "weighted_community"],
            right_on=["abs_community", "per_community"],
            how="inner",
        ).drop(["abs_community", "per_community"], axis=1)

        if not merge_partial.empty:
            save_parquet_to_directory(
                os.path.join(output_dir, data_type, "LDA", "partial_matched"),
                content_type,
                f"{month}_{year}.parquet",
                merge_partial,
            )

    logger.info(
        "topic_phase_completed month=%s elapsed_seconds=%.2f",
        month,
        time.perf_counter() - phase_started,
    )
    return df_lda_scores


def save_pipeline_topic_inputs(
    abs_community_messages: pd.DataFrame,
    per_community_messages: pd.DataFrame,
    matched_df: pd.DataFrame,
    partial_matched: pd.DataFrame,
    month: str,
    year: str,
    data_type: str,
    content_type: str,
    output_dir: str,
):
    from src.topics.topic_inputs import save_topic_inputs

    topic_input_dir = save_topic_inputs(
        absolute_community_messages=abs_community_messages,
        weighted_community_messages=per_community_messages,
        matched_communities=matched_df,
        partial_matched_communities=partial_matched,
        output_base_path=output_dir,
        data_type=data_type,
        content_type=content_type,
        month=month,
        year=year,
    )
    logger.info("topic_inputs_saved path=%s", topic_input_dir.resolve())
    return topic_input_dir


def save_pipeline_theme_inputs(
    matched_lda_csv: str | Path,
    month: str,
    year: str,
    data_type: str,
    content_type: str,
    output_dir: str,
):
    from src.themes.theme_inputs import save_theme_inputs

    theme_input_dir = save_theme_inputs(
        matched_lda_csv=matched_lda_csv,
        output_base_path=output_dir,
        data_type=data_type,
        content_type=content_type,
        month=month,
        year=year,
    )
    logger.info("theme_inputs_saved path=%s", theme_input_dir.resolve())
    return theme_input_dir


def run_topic_phase_from_saved_inputs(
    output_dir: str,
    data_type: str,
    content_type: str,
    month: str,
    year: str,
    lda_config: dict[str, Any] | None = None,
    translation_config: dict[str, Any] | None = None,
):
    from src.topics.topic_inputs import load_topic_inputs

    bundle = load_topic_inputs(
        output_base_path=output_dir,
        data_type=data_type,
        content_type=content_type,
        month=month,
        year=year,
    )
    return run_topic_phase(
        abs_community_messages=bundle.absolute_community_messages,
        per_community_messages=bundle.weighted_community_messages,
        matched_df=bundle.matched_communities,
        partial_matched=bundle.partial_matched_communities,
        month=month,
        year=year,
        data_type=data_type,
        content_type=content_type,
        output_dir=output_dir,
        lda_config=lda_config,
        translation_config=translation_config,
    )


def run_full_pipeline(
    df: pd.DataFrame,
    content_type: str = "reply",
    data_type: str = "twitter",
    month: str = "march",
    year: str = "2017",
    date_column: str = "created_at",
    creator_relation: str = "REPLIED_TO",
    spreader_relation: str = "REPLIED_BY",
    creator_node_column: str = "target",
    spreader_node_column: str = "target",
    text_node_column_creator_df: str = "source",
    min_total_post: int = 10,
    min_shared_post: int = 5,
    min_members: int = 3,
    output_dir: str = "results",
    include_topics: bool = True,
    dashboard_graph_sample_max_edges: int = 50_000,
    louvain_resolution: float = 1.0,
    louvain_seed: int = 123,
    lda_config: dict[str, Any] | None = None,
    translation_config: dict[str, Any] | None = None,
):
    """Orchestrates the entire thesis pipeline."""
    # 1. Network
    G_absolute, G_percentage, df_network, df_user = run_network_phase(
        df_data=df,
        content_type=content_type,
        creator_relation=creator_relation,
        spreader_relation=spreader_relation,
        creator_node_column=creator_node_column,
        spreader_node_column=spreader_node_column,
        text_node_column_creator_df=text_node_column_creator_df,
        data_type=data_type,
        month=month,
        year=year,
        output_dir=output_dir,
        min_total_post=min_total_post,
        min_shared_post=min_shared_post,
    )

    # 2. Community
    abs_msgs, per_msgs, matched_df, partial_matched = run_community_phase(
        G_absolute=G_absolute,
        G_percentage=G_percentage,
        df_network=df_network,
        df_user=df_user,
        min_members=min_members,
        date_column=date_column,
        month=month,
        data_type=data_type,
        content_type=content_type,
        output_dir=output_dir,
        dashboard_graph_sample_max_edges=dashboard_graph_sample_max_edges,
        louvain_resolution=louvain_resolution,
        louvain_seed=louvain_seed,
    )

    save_pipeline_topic_inputs(
        abs_community_messages=abs_msgs,
        per_community_messages=per_msgs,
        matched_df=matched_df,
        partial_matched=partial_matched,
        month=month,
        year=year,
        data_type=data_type,
        content_type=content_type,
        output_dir=output_dir,
    )

    if include_topics:
        run_topic_phase_from_saved_inputs(
            output_dir=output_dir,
            data_type=data_type,
            content_type=content_type,
            month=month,
            year=year,
            lda_config=lda_config,
            translation_config=translation_config,
        )

    logger.info("full_pipeline_completed")
    return True


def run_network_community_pipeline(
    df: pd.DataFrame,
    content_type: str = "reply",
    data_type: str = "twitter",
    month: str = "march",
    year: str = "2017",
    date_column: str = "created_at",
    creator_relation: str = "REPLIED_TO",
    spreader_relation: str = "REPLIED_BY",
    creator_node_column: str = "target",
    spreader_node_column: str = "target",
    text_node_column_creator_df: str = "source",
    min_total_post: int = 10,
    min_shared_post: int = 5,
    min_members: int = 3,
    output_dir: str = "results",
    dashboard_graph_sample_max_edges: int = 50_000,
    louvain_resolution: float = 1.0,
    louvain_seed: int = 123,
):
    """Run network and community stages without LDA/topic modeling."""
    return run_full_pipeline(
        df=df,
        content_type=content_type,
        data_type=data_type,
        month=month,
        year=year,
        date_column=date_column,
        creator_relation=creator_relation,
        spreader_relation=spreader_relation,
        creator_node_column=creator_node_column,
        spreader_node_column=spreader_node_column,
        text_node_column_creator_df=text_node_column_creator_df,
        min_total_post=min_total_post,
        min_shared_post=min_shared_post,
        min_members=min_members,
        output_dir=output_dir,
        include_topics=False,
        dashboard_graph_sample_max_edges=dashboard_graph_sample_max_edges,
        louvain_resolution=louvain_resolution,
        louvain_seed=louvain_seed,
    )
