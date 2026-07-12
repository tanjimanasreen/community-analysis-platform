import os
import pandas as pd
import ast

from src.providers.cached import CachedProvider
from src.providers.factory import build_theme_provider
from src.themes.gpt_themes import generate_llm_themes
# Future imports from Milestone 4, 5, 6 will go here:
# from src.themes.community_transition import calculate_jaccard_transitions
# from src.themes.sankey_paths import generate_sankey
# from src.themes.heatmaps import ...

from src.themes.data_loader import load_prepare_data
from src.themes.community_transition import get_community_transition
from src.themes.sankey_paths import get_path_info, find_all_sankey_paths
from src.visualization.community_transition import draw_community_transition_diagram
from src.visualization.membership_changes import draw_members_transition_diagram
from src.themes.theme_similarity import extract_themes
from src.visualization.theme_similarity import draw_theme_similarity_heatmap

def process_single_file_themes(df: pd.DataFrame, provider) -> pd.DataFrame:
    # Ensure correct lists
    for col in ['absolute_unigram_keywords', 'absolute_bigram_keywords', 
                'weighted_unigram_keywords', 'weighted_bigram_keywords']:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) and x.startswith('[') else x)
        else:
            df[col] = [[] for _ in range(len(df))]
            
    if 'absolute_community' not in df.columns:
        df['absolute_community'] = -1
    if 'weighted_community' not in df.columns:
        df['weighted_community'] = -1
        
    themed_df = generate_llm_themes(provider, df)
    return themed_df

def run_theme_pipeline(
    input_dir: str,
    year: str,
    content_type: str,
    output_dir: str,
    config: dict | None = None,
    provider=None,
    render_visuals: bool = True,
    similarity_model_name: str = 'paraphrase-MiniLM-L6-v2',
):
    """
    Runs the full theme intelligence pipeline on the LDA outputs directory.
    Provider is resolved from config via the provider factory unless explicitly
    passed (e.g. in tests via provider=MockProvider(...)).
    """
    os.makedirs(output_dir, exist_ok=True)

    # Milestone 1: Data Loading
    print(f"Loading data from {input_dir} for year {year}...")
    monthly_data_dict = load_prepare_data(input_dir, year)
    return run_theme_pipeline_from_monthly_data(
        monthly_data_dict=monthly_data_dict,
        year=year,
        content_type=content_type,
        output_dir=output_dir,
        config=config,
        provider=provider,
        render_visuals=render_visuals,
        similarity_model_name=similarity_model_name,
    )


def run_theme_pipeline_from_bundle(
    bundle,
    year: str,
    content_type: str,
    output_dir: str,
    config: dict | None = None,
    provider=None,
    render_visuals: bool = True,
    similarity_model_name: str = 'paraphrase-MiniLM-L6-v2',
):
    return run_theme_pipeline_from_monthly_data(
        monthly_data_dict=bundle.monthly_data,
        year=year,
        content_type=content_type,
        output_dir=output_dir,
        config=config,
        provider=provider,
        render_visuals=render_visuals,
        similarity_model_name=similarity_model_name,
    )


def run_theme_pipeline_from_monthly_data(
    monthly_data_dict: dict[str, pd.DataFrame],
    year: str,
    content_type: str,
    output_dir: str,
    config: dict | None = None,
    provider=None,
    render_visuals: bool = True,
    similarity_model_name: str = 'paraphrase-MiniLM-L6-v2',
):
    import ast
    os.makedirs(output_dir, exist_ok=True)
    if not monthly_data_dict:
        print("No monthly matched LDA files found. Theme pipeline will emit empty transition output.")

    # Milestone 2: GPT Theme Generation
    print("Generating themes via LLM for all months...")
    if provider is not None:
        # Test injection — wrap in CachedProvider if not already wrapped
        if not isinstance(provider, CachedProvider):
            provider = CachedProvider(provider)
    else:
        # Production path — build provider from config (reads providers.yml via factory)
        provider = build_theme_provider(config or {})
    
    themed_monthly_dict = {}
    for month, df in monthly_data_dict.items():
        print(f"Processing themes for {month}...")
        themed_df = process_single_file_themes(df, provider)
        themed_monthly_dict[month] = themed_df
        # Save themed output
        output_path = os.path.join(output_dir, f"{month}_{year}_with_themes.csv")
        themed_df.to_csv(output_path, index=False)
        print(f"Themes generated and saved to {output_path}")
        
    # Milestone 3: Community Transition
    print("Calculating community transitions...")
    matched_df = get_community_transition(themed_monthly_dict, content_type)
    transitions_path = os.path.join(output_dir, "community_transition.csv")
    matched_df.to_csv(transitions_path, index=False)
    print(f"Community transitions saved to {transitions_path}")
    
    # Milestone 4: Sankey Diagrams
    print("Generating Sankey diagrams...")
    source_ind, target_ind, score, all_community = get_path_info(matched_df)
    sankey_dir = os.path.join(output_dir, "sankey")
    if render_visuals:
        draw_community_transition_diagram(sankey_dir, source_ind, target_ind, score, all_community, matched_df)
    
    # Milestone 5: Membership Changes
    print("Calculating membership changes and diagrams...")
    paths_detected = find_all_sankey_paths(source_ind, target_ind, all_community)
    members_dir = os.path.join(output_dir, "membership_changes")
    if render_visuals:
        draw_members_transition_diagram(members_dir, paths_detected, matched_df)
    
    # Milestone 6: Theme Similarity Heatmaps
    print("Generating theme similarity heatmaps...")
    similarity_dir = os.path.join(output_dir, "theme_similarity")
    
    community_absolute_themes = extract_themes(matched_df, paths_detected, 'start_month_absolute_theme', 'end_month_absolute_theme')
    if render_visuals:
        draw_theme_similarity_heatmap(community_absolute_themes, similarity_dir, 'absolute_theme', model_name=similarity_model_name)
    
    community_weighted_themes = extract_themes(matched_df, paths_detected, 'start_month_weighted_theme', 'end_month_weighted_theme')
    if render_visuals:
        draw_theme_similarity_heatmap(community_weighted_themes, similarity_dir, 'weighted_theme', model_name=similarity_model_name)
    
    community_general_themes = extract_themes(matched_df, paths_detected, 'start_month_general_theme', 'end_month_general_theme')
    if render_visuals:
        draw_theme_similarity_heatmap(community_general_themes, similarity_dir, 'general_theme', model_name=similarity_model_name)
    
    print("Full theme intelligence pipeline completed successfully!")
    return matched_df
