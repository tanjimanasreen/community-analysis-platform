import pandas as pd
import json
import time
from src.providers.base import BaseLLMProvider as LLMProvider
from src.config.defaults import default_config

def map_theme(community_value, reference_df, reference_community_column, theme_gpt, theme_names):
    for idx, row in reference_df.iterrows():
        if community_value in row[reference_community_column]:
            return pd.Series([row[theme_gpt], row[theme_names]])
    return pd.Series([None, None])

def extract_unique_keywords(month_df):
    """Prepares 'all_keywords', 'absolute_keywords', 'weighted_keywords' columns"""
    df = month_df.copy()

    df['all_keywords'] = df['absolute_unigram_keywords'] + df['absolute_bigram_keywords'] + df['weighted_unigram_keywords'] + df['weighted_bigram_keywords']
    df['all_keywords'] = df['all_keywords'].apply(lambda x: list(dict.fromkeys(x)))
    df['all_keywords'] = df['all_keywords'].apply(lambda x: str(x).replace("[", "").replace("]", "").replace(" ", "").replace("'", ""))

    df['absolute_keywords'] = df['absolute_unigram_keywords'] + df['absolute_bigram_keywords']
    df['absolute_keywords'] = df['absolute_keywords'].apply(lambda x: list(dict.fromkeys(x)))
    df['absolute_keywords'] = df['absolute_keywords'].apply(lambda x: str(x).replace("[", "").replace("]", "").replace(" ", "").replace("'", ""))

    df['weighted_keywords'] = df['weighted_unigram_keywords'] + df['weighted_bigram_keywords']
    df['weighted_keywords'] = df['weighted_keywords'].apply(lambda x: list(dict.fromkeys(x)))
    df['weighted_keywords'] = df['weighted_keywords'].apply(lambda x: str(x).replace("[", "").replace("]", "").replace(" ", "").replace("'", ""))

    return df


def call_gpt_theme_api(keywords: str):
    """Compatibility wrapper for the original GPT theme API call.

    Resolves the provider via the provider factory to ensure fallback and
    champion routing are preserved.
    """
    from src.providers.factory import build_theme_provider
    provider = build_theme_provider(default_config)
    return provider.generate_theme(keywords)


def generate_gpt_theme(month_df: pd.DataFrame):
    """Backward-compatible GPT theme generator."""
    from src.providers.factory import build_theme_provider
    provider = build_theme_provider(default_config)
    return generate_llm_themes(provider, month_df)

def generate_llm_themes(provider: LLMProvider, month_df: pd.DataFrame):
    df = extract_unique_keywords(month_df)

    absolute_temp_df = df[['absolute_community', 'absolute_keywords']]
    absolute_grouped_df = absolute_temp_df.groupby('absolute_keywords').agg({'absolute_community': list}).reset_index()

    weighted_temp_df = df[['weighted_community', 'weighted_keywords']]
    weighted_grouped_df = weighted_temp_df.groupby('weighted_keywords').agg({'weighted_community': list}).reset_index()

    for ind, row in absolute_grouped_df.iterrows():
        gpt_result_abs = provider.generate_theme(row['absolute_keywords'])
        absolute_grouped_df.at[ind, 'absolute_theme_gpt'] = str(gpt_result_abs)
        absolute_grouped_df.at[ind, 'absolute_theme_names'] = '.'.join(list(gpt_result_abs.keys()))

    for ind, row in weighted_grouped_df.iterrows():
        gpt_result_wei = provider.generate_theme(row['weighted_keywords'])
        weighted_grouped_df.at[ind, 'weighted_theme_gpt'] = str(gpt_result_wei)
        weighted_grouped_df.at[ind, 'weighted_theme_names'] = '.'.join(list(gpt_result_wei.keys()))

    for ind, row in df.iterrows():
        gpt_result = provider.generate_theme(row['all_keywords'])
        df.at[ind, 'general_theme_gpt'] = str(gpt_result)
        df.at[ind, 'general_theme_names'] = '.'.join(list(gpt_result.keys()))

    df[['absolute_theme_gpt', 'absolute_theme_names']] = df['absolute_community'].apply(
        map_theme, args=(absolute_grouped_df, 'absolute_community', 'absolute_theme_gpt', 'absolute_theme_names')
    )
    df[['weighted_theme_gpt', 'weighted_theme_names']] = df['weighted_community'].apply(
        map_theme, args=(weighted_grouped_df, 'weighted_community', 'weighted_theme_gpt', 'weighted_theme_names')
    )

    return df
