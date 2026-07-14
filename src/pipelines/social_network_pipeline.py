import os
from pathlib import Path
import pandas as pd
from typing import List, Dict, Tuple, Any

from src.ingestion.network_data_extractor import get_creator_spreader, create_user_df, create_network_df
from src.network.follower_followee import get_follower_followee_network
from src.network.graphs import get_network_graph
from src.network.centrality import get_prominent_communities_stat

from src.communities.louvain import get_louvain_community, detect_prominent_communities, get_prominent_communities
from src.communities.messages import get_community_messages, get_overall_community_messages_stat
from src.communities.similarity import find_matching_communities

def save_csv_to_directory(base_dir: str, subfolder: str, filename: str, data: pd.DataFrame):
    """
    Creates a directory if not present and saves a CSV file inside it.
    """
    if data is None or data.empty:
        return

    path = Path(base_dir) / subfolder
    path.mkdir(parents=True, exist_ok=True)

    csv_path = path / filename
    data.to_csv(csv_path, index=False)
    print(f"CSV saved at: {csv_path.resolve()}")
    return csv_path

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
    print("Running network extraction...")

    if data_type == 'telegram':
        df_network = df_data.copy()
        # Create synthetic df_user for telegram from from_id and forwarder_id
        unique_users = set(df_network['from_id'].dropna().unique()).union(set(df_network['forwarder_id'].dropna().unique()))
        df_user = pd.DataFrame({'user_id': list(unique_users)})
        df_user['username'] = 'anonymous' + df_user['user_id'].astype(str)
    else:
        df_creator, df_spreader = get_creator_spreader(df_data, creator_relation, spreader_relation)
        df_user = create_user_df(df_spreader, df_creator, creator_node_column, spreader_node_column)
        df_network = create_network_df(df_creator, text_node_column_creator_df)

    followee_follower_df = get_follower_followee_network(df_network)

    # Save network data
    save_csv_to_directory(os.path.join(output_dir, data_type, 'network_data'), content_type, f"{month}{year}.csv", df_network)

    print("Creating graphs...")
    G_absolute, G_percentage = get_network_graph(
        followee_follower_df,
        min_total_post=min_total_post,
        min_shared_post=min_shared_post,
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
    output_dir: str
):
    print("Applying Louvain...")
    abs_com, abs_part = get_louvain_community(G_absolute, 'shared_post')
    per_com, per_part = get_louvain_community(G_percentage, 'weighted_post')

    print("Filtering prominent communities...")
    prominent_communities_abs = detect_prominent_communities(abs_com, min_members)
    prominent_communities_per = detect_prominent_communities(per_com, min_members)

    abs_community = get_prominent_communities(prominent_communities_abs, G_absolute)
    per_community = get_prominent_communities(prominent_communities_per, G_percentage)

    print("Extracting community messages...")
    abs_community_messages = get_community_messages(prominent_communities_abs, abs_community, df_network, df_user)
    per_community_messages = get_community_messages(prominent_communities_per, per_community, df_network, df_user)

    print("Calculating user centrality...")
    abs_degree = get_prominent_communities_stat(prominent_communities_abs, G_absolute, df_user)
    per_degree = get_prominent_communities_stat(prominent_communities_per, G_percentage, df_user)

    df_user_centrality = pd.DataFrame({
        'month': [month],
        'absolute': [abs_degree],
        'weighted': [per_degree]
    })
    save_csv_to_directory(os.path.join(output_dir, data_type, 'user_centrality'), content_type, f"{month}.csv", df_user_centrality)

    print("Saving community graphs for frontend visualization...")
    if not abs_community.empty:
        save_csv_to_directory(os.path.join(output_dir, data_type, 'communities', 'graphs', 'absolute'), content_type, f"{month}.csv", abs_community)
    if not per_community.empty:
        save_csv_to_directory(os.path.join(output_dir, data_type, 'communities', 'graphs', 'weighted'), content_type, f"{month}.csv", per_community)

    print("Calculating user message counts...")
    total_abs_users = len(set(abs_community['source'].to_list() + abs_community['target'].to_list())) if not abs_community.empty else 0
    total_per_users = len(set(per_community['source'].to_list() + per_community['target'].to_list())) if not per_community.empty else 0

    df_user_messages_count = pd.DataFrame({
        'month': [month],
        'user': [{'absolute': total_abs_users, 'weighted': total_per_users}],
        'messages': [{'absolute': abs_community_messages['total_messages'].sum() if not abs_community_messages.empty else 0,
                      'weighted': per_community_messages['total_messages'].sum() if not per_community_messages.empty else 0}]
    })
    save_csv_to_directory(os.path.join(output_dir, data_type, 'count_user_messages'), content_type, f"{month}.csv", df_user_messages_count)

    print("Calculating daily message stats...")
    abs_msg_stat = get_overall_community_messages_stat(date_column, prominent_communities_abs, abs_community, df_network)
    per_msg_stat = get_overall_community_messages_stat(date_column, prominent_communities_per, per_community, df_network)

    df_daily_messages_stat = pd.DataFrame({
        'month': [month],
        'absolute': [abs_msg_stat],
        'weighted': [per_msg_stat]
    })
    save_csv_to_directory(os.path.join(output_dir, data_type, 'daily_messages_stat'), content_type, f"{month}.csv", df_daily_messages_stat)

    print("Finding matching communities...")
    matched_df, partial_matched, unmatched_abs, unmatched_per = find_matching_communities(abs_community, per_community)

    df_number_of_community = pd.DataFrame({
        'month': [month],
        'total_matched': [len(matched_df)],
        'total_absolute': [len(prominent_communities_abs)],
        'total_weighted': [len(prominent_communities_per)]
    })
    save_csv_to_directory(os.path.join(output_dir, data_type, 'communities', 'matched'), content_type, f"{month}.csv", df_number_of_community)

    partial_matched_community = partial_matched.copy()
    if not partial_matched_community.empty:
        partial_matched_community.rename(columns={'abs_community': 'absolute', 'per_community': 'weighted'}, inplace=True)
        partial_matched_community['month'] = month
        df_partial_matched_community = partial_matched_community[['month', 'absolute', 'weighted', 'jaccard_score']]
        save_csv_to_directory(os.path.join(output_dir, data_type, 'communities', 'partially_matched'), content_type, f"{month}.csv", df_partial_matched_community)

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
    output_dir: str
):
    from src.topics.text_preprocessor import message_preprocess
    from src.topics.lda import get_unigram_lda, get_bigram_lda
    from src.topics.topic_matching import get_matched_topic_df

    print("Preprocessing messages for topic modeling...")
    if not abs_community_messages.empty:
        abs_community_messages['messages_processed'] = message_preprocess(abs_community_messages)
    if not per_community_messages.empty:
        per_community_messages['messages_processed'] = message_preprocess(per_community_messages)

    print("Running LDA models...")
    uni_doc_topics_abs, lda_abs, perplexity_abs, coherence_abs = get_unigram_lda(abs_community_messages) if not abs_community_messages.empty else (pd.DataFrame(), None, 0, 0)
    uni_doc_topics_per, lda_per, perplexity_per, coherence_per = get_unigram_lda(per_community_messages) if not per_community_messages.empty else (pd.DataFrame(), None, 0, 0)

    bi_doc_topics_abs, bi_lda_abs, perplexity_bi_abs, coherence_bi_abs = get_bigram_lda(abs_community_messages) if not abs_community_messages.empty else (pd.DataFrame(), None, 0, 0)
    bi_doc_topics_per, bi_lda_per, perplexity_bi_per, coherence_bi_per = get_bigram_lda(per_community_messages) if not per_community_messages.empty else (pd.DataFrame(), None, 0, 0)

    df_lda_scores = pd.DataFrame({
        'month': [month],
        'unigram_absolute': [[perplexity_abs, coherence_abs]],
        'unigram_weighted': [[perplexity_per, coherence_per]],
        'bigram_absolute': [[perplexity_bi_abs, coherence_bi_abs]],
        'bigram_weighted': [[perplexity_bi_per, coherence_bi_per]]
    })
    save_csv_to_directory(os.path.join(output_dir, data_type, 'LDA', 'scores'), content_type, f"{month}.csv", df_lda_scores)

    print("Extracting topics for matched communities...")
    matched_communities = []
    if not matched_df.empty:
        for ind, row in matched_df.iterrows():
            matched_communities.append(tuple(row[['abs_community', 'per_community']].values))

    if matched_communities and lda_abs is not None and lda_per is not None:
        matched_topic_df = get_matched_topic_df(
            lda_models=[lda_abs, lda_per, bi_lda_abs, bi_lda_per],
            dfs=[uni_doc_topics_abs, uni_doc_topics_per, bi_doc_topics_abs, bi_doc_topics_per],
            community_id_pairs=matched_communities
        )
        merged_match = pd.merge(
            matched_topic_df,
            matched_df[['abs_community', 'members', 'per_community']],
            left_on=['absolute_community', 'weighted_community'],
            right_on=['abs_community', 'per_community'],
            how='inner'
        ).drop(['abs_community', 'per_community'], axis=1)

        if not merged_match.empty:
            matched_csv = save_csv_to_directory(os.path.join(output_dir, data_type, 'LDA', 'matched'), content_type, f"{month}_{year}.csv", merged_match)
            save_pipeline_theme_inputs(
                matched_lda_csv=matched_csv,
                month=month,
                year=year,
                data_type=data_type,
                content_type=content_type,
                output_dir=output_dir,
            )

    print("Extracting topics for partially matched communities...")
    partial_communities = []
    if not partial_matched.empty:
        for ind, row in partial_matched.iterrows():
            partial_communities.append(tuple(row[['abs_community', 'per_community']].values))

    if partial_communities and lda_abs is not None and lda_per is not None:
        partial_matched_topic_df = get_matched_topic_df(
            lda_models=[lda_abs, lda_per, bi_lda_abs, bi_lda_per],
            dfs=[uni_doc_topics_abs, uni_doc_topics_per, bi_doc_topics_abs, bi_doc_topics_per],
            community_id_pairs=partial_communities
        )
        merge_partial = pd.merge(
            partial_matched_topic_df,
            partial_matched[['abs_community', 'absolute_members', 'weighted_members', 'jaccard_score', 'common_members', 'uncommon_members', 'per_community']],
            left_on=['absolute_community', 'weighted_community'],
            right_on=['abs_community', 'per_community'],
            how='inner'
        ).drop(['abs_community', 'per_community'], axis=1)

        if not merge_partial.empty:
            save_csv_to_directory(os.path.join(output_dir, data_type, 'LDA', 'partial_matched'), content_type, f"{month}_{year}.csv", merge_partial)

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
    print(f"Topic input artifacts saved at: {topic_input_dir.resolve()}")
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
    print(f"Theme input artifacts saved at: {theme_input_dir.resolve()}")
    return theme_input_dir


def run_topic_phase_from_saved_inputs(
    output_dir: str,
    data_type: str,
    content_type: str,
    month: str,
    year: str,
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
    )

def run_full_pipeline(
    df: pd.DataFrame,
    content_type: str = 'reply',
    data_type: str = 'twitter',
    month: str = 'march',
    year: str = '2017',
    date_column: str = 'created_at',
    creator_relation: str = 'REPLIED_TO',
    spreader_relation: str = 'REPLIED_BY',
    creator_node_column: str = 'target',
    spreader_node_column: str = 'target',
    text_node_column_creator_df: str = 'source',
    min_total_post: int = 10,
    min_shared_post: int = 5,
    min_members: int = 3,
    output_dir: str = 'results',
    include_topics: bool = True,
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
        output_dir=output_dir
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
        )

    print("Full pipeline completed successfully!")
    return True


def run_network_community_pipeline(
    df: pd.DataFrame,
    content_type: str = 'reply',
    data_type: str = 'twitter',
    month: str = 'march',
    year: str = '2017',
    date_column: str = 'created_at',
    creator_relation: str = 'REPLIED_TO',
    spreader_relation: str = 'REPLIED_BY',
    creator_node_column: str = 'target',
    spreader_node_column: str = 'target',
    text_node_column_creator_df: str = 'source',
    min_total_post: int = 10,
    min_shared_post: int = 5,
    min_members: int = 3,
    output_dir: str = 'results',
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
    )
