import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import pandas as pd
from pathlib import Path

from utils.network_data_extractor import *
from utils.lang_detector import *
from utils.lang_translator import *
from utils.network_graph import *
from utils.community_generator import *
from utils.similarity_detector import *
from utils.text_preprocessor import *
from utils.lda_analysis import *

import importlib
import sys


# Reload necessary modules
_ = importlib.reload(sys.modules['utils.lda_analysis'])
_ = importlib.reload(sys.modules['utils.community_generator'])
_ = importlib.reload(sys.modules['utils.network_data_extractor'])
_ = importlib.reload(sys.modules['utils.similarity_detector'])


def save_csv_to_directory(base_dir, subfolder, filename, data):
    """
    Creates a directory if not present and saves a CSV file inside it.

    Parameters:
    - base_dir (str or Path): Base directory.
    - subfolder (str): Subdirectory to create inside base_dir.
    - filename (str): CSV filename (e.g., 'output.csv').
    - data (dataframe): Data to write into CSV.
    """
    path = Path(base_dir) / subfolder
    path.mkdir(parents=True, exist_ok=True)  # Create dir if it doesn't exist

    csv_path = path / filename
    data.to_csv(csv_path, index=False)

    print(f"CSV saved at: {csv_path.resolve()}")


def main():
    
    # Define parameters for twitter data
    month = 'march'
    year = '2017'
    content_type = 'reply'
    data_file = content_type + "_" + month + "_" + year + ".csv"
    # Path to data directory
    path =  "/Volumes/T7 Shield/Immigration-Tweets/SODATap/monthly_reply/"
    data_type = 'twitter'
    date_column = "created_at"

     # Relation types Parameters
    creator_relation = "REPLIED_TO" # Author
    spreader_relation = "REPLIED_BY" #Speader/Co-author

    # creator_relation = "TWEETED"
    # spreader_relation = "RETWEETED_BY"

    # Column Names of the User nodes in the df_data DataFrame
    creater_node_column = 'target'
    spreader_node_column = 'target'

    # Column Names of the Message nodes in the df_creator DataFrame
    text_node_column_creator_df = 'source'


    # Define parameters for telegram data
    # month = 'october'
    # year = '2019'
    # translated_file = "translated_" + month + "_" + year + ".csv"
    # data_file =  month + "_" + year + ".csv"
    # telegram_path_translated = "/Volumes/T7 Shield/Telegram/Monthly/Translated/"
    # path = "/Volumes/T7 Shield/Telegram/Monthly/"
    # data_type = 'telegram'
    # date_column = "created_date"

    """Loading Data"""
    df_data = pd.read_csv(path + data_file, low_memory=False)
    print(df_data.tail())

    df_creator, df_spreader = get_creator_spreader(df_data, creator_relation, spreader_relation)
    

    df_user = create_user_df(df_spreader, df_creator, creater_node_column, spreader_node_column)
    print(df_user.head())

   
    df_network = create_network_df(df_creator, text_node_column_creator_df)
    print(df_network.head())

    followee_follower_df = get_follower_followee_network(df_network)
    print(followee_follower_df.head())   

    
    if data_type == 'telegram':
        df_network = pd.read_csv(telegram_path_translated+translated_file)
        print(df_network.head())
    else:
        df_network = lang_detection(df_network)
        # print(df_network.head())
        save_csv_to_directory(data_type+'/network_data/',content_type,month+year+'.csv', df_network)
        # df_network.to_csv(data_type+'/network_data/'+content_type+'/'+month+year+'.csv',index=False)
    
    # Create the network graph
    G_absolute, G_percentage = get_network_graph(followee_follower_df)
    
    # Get the community structure
    abs_weight = 'shared_post'
    per_weight = 'weighted_post'
    abs_com, abs_part = get_louvain_community(G_absolute, abs_weight)
    per_com, per_part = get_louvain_community(G_percentage, per_weight)
   
    # Filter Prominent Communities
    min_members = 3

    promiment_communities_abs = detect_promiment_communities(abs_com, min_members)
    promiment_communities_per = detect_promiment_communities(per_com, min_members)

    # Extract Prominent Communities in Dataframe
    abs_community = get_promiment_communities(promiment_communities_abs, G_absolute)
    print(abs_community.head())
    per_community = get_promiment_communities(promiment_communities_per, G_percentage)
    print(per_community.head())

    # Extract Promiment Communities' Messages
    abs_community_messages = get_community_messages(promiment_communities_abs, abs_community, df_network, df_user)
    print(abs_community_messages.head())
    per_community_messages = get_community_messages(promiment_communities_per, per_community, df_network, df_user)
    print(per_community_messages.head())

    # User Centrality
    abs_degree = get_prominent_communities_stat(promiment_communities_abs, G_absolute, df_user)  
    per_degree = get_prominent_communities_stat(promiment_communities_per, G_percentage, df_user)   
    user_centrality = {'month': month, 'absolute': abs_degree, 'weighted': per_degree}

    # Creating a DataFrame
    df_user_centrality = pd.DataFrame({
        'month': user_centrality['month'],
        'absolute': [user_centrality['absolute']],
        'weighted': [user_centrality['weighted']]
    })
    print(df_user_centrality)
    # Writing DataFrame to a CSV file
    save_csv_to_directory(data_type+'/user_centrality/',content_type,month+'.csv', df_user_centrality)
    # df_user_centrality.to_csv(data_type+'/user_centrality/'+content_type+'/'+month+'.csv', index=False)

    # User Messages Count
    total_abs_users = len(set(abs_community.source.to_list() + abs_community.target.to_list()))
    total_per_users = len(set(per_community.source.to_list() + per_community.target.to_list()))

    user_messages_count = {'month': month, 'user': {'absolute': total_abs_users, 'weighted': total_per_users}, 
                        'messages': {'absolute': abs_community_messages.total_messages.sum(), 
                                        'weighted': per_community_messages.total_messages.sum()}}

    # Creating a DataFrame
    df_user_messages_count = pd.DataFrame({
        'month': user_messages_count['month'],
        'user': [user_messages_count['user']],
        'messages': [user_messages_count['messages']]
    })
    # print(df_user_messages_count.head())
    # Writing DataFrame to a CSV file
    save_csv_to_directory(data_type+'/count_user_messages/',content_type,month+'.csv', df_user_messages_count)
    # df_user_messages_count.to_csv(data_type+'/count_user_messages/'+content_type+'_'+month+'.csv', index=False)

    # Daily Messages Forwarded/Sent in Communities
    abs_msg_stat = get_overall_community_messages_stat(date_column, promiment_communities_abs, abs_community, df_network)
    per_msg_stat = get_overall_community_messages_stat(date_column, promiment_communities_per, per_community, df_network)

    daily_messages_stat = {'month': month, 'absolute': abs_msg_stat, 'weighted': per_msg_stat}


    df_daily_messages_stat = pd.DataFrame({
        'month': daily_messages_stat['month'],
        'absolute': [daily_messages_stat['absolute']],
        'weighted': [daily_messages_stat['weighted']]
    })
    # display(df_daily_messages_stat)

    # Writing DataFrame to a CSV file
    save_csv_to_directory(data_type + '/daily_messages_stat/', content_type, month+'.csv', df_daily_messages_stat)
    # df_daily_messages_stat.to_csv(data_type +'/daily_messages_stat/'+content_type+'_'+month+'.csv', index=False)

   
    # Community Similarity Detection
    matched_df, partial_matched, unmatched_abs, unmatched_per = find_matching_communities(abs_community, per_community)

    #Number of Matched and Partially Matched Communities
    number_of_community = {'month' : month, 'matched': len(matched_df), 'absolute': len(promiment_communities_abs), 'weighted': len(promiment_communities_per)}

    df_number_of_community = pd.DataFrame({
        'month': number_of_community['month'],
        'total_matched': [number_of_community['matched']],
        'total_absolute': [number_of_community['absolute']],
        'total_weighted': [number_of_community['weighted']]
    })

    # Writing DataFrame to a CSV file
    save_csv_to_directory(data_type + '/communities/matched/', content_type, month+'.csv', df_number_of_community)
    # df_number_of_community.to_csv(data_type + '/communities/matched/'+content_type+'_'+month+'.csv', index=False)
    #Save partially matched communities
    partial_matched_community = partial_matched.copy()
    partial_matched_community.rename(columns={'abs_community': 'absolute', 'per_community': 'weighted'}, inplace=True)
    partial_matched_community['month'] = month
    df_partial_matched_community = partial_matched_community[['month', 'absolute', 'weighted', 'jaccard_score']]

    save_csv_to_directory(data_type + '/communities/partially_matched/', content_type, month+'.csv', df_partial_matched_community)
    # df_partial_matched_community.to_csv(data_type +'/communities/partially_matched/'+content_type+'_'+month+'.csv', index=False)


    # Topic Modelling
    # Preprocessing
    abs_community_messages['messages_processed'] = message_preprocess(abs_community_messages)
    per_community_messages['messages_processed'] = message_preprocess(per_community_messages)

    # LDA-Unigram
    uni_document_topics_abs, lda_abs, perplexity_abs, coherence_abs = get_unigram_lda(abs_community_messages)
    uni_document_topics_per,lda_per, perplexity_per, coherence_per = get_unigram_lda(per_community_messages)

    # LDA-Bigram
    bigram_document_topics_abs, bi_lda_abs, perplexity_bi_abs, coherence_bi_abs = get_bigram_lda(abs_community_messages)
    bigram_document_topics_per, bi_lda_per, perplexity_bi_per, coherence_bi_per = get_bigram_lda(per_community_messages)    

    # LDA Score
    lda_scores = {'month': month, 
              'unigram_absolute': [perplexity_abs, coherence_abs], 
              'unigram_weighted': [perplexity_per, coherence_per], 
              'bigram_absolute': [perplexity_bi_abs, coherence_bi_abs], 
              'bigram_weighted': [perplexity_bi_per, coherence_bi_per]}


    df_lda_scores = pd.DataFrame({
        'month': lda_scores['month'],
        'unigram_absolute': [lda_scores['unigram_absolute']],
        'unigram_weighted': [lda_scores['unigram_weighted']],
        'bigram_absolute': [lda_scores['bigram_absolute']],
        'bigram_weighted': [lda_scores['bigram_weighted']]
    })

    # Writing DataFrame to a CSV file
    save_csv_to_directory(data_type + '/LDA/scores/', content_type, month+'.csv', df_lda_scores)
    # df_lda_scores.to_csv(data_type + '/LDA/scores/'+content_type+'_'+month+'.csv', index=False)

    # Get Keywords for Matched Communities
    matched_communities = []
    for ind, row in matched_df.iterrows():
        matched_communities.append(tuple(row[['abs_community', 'per_community']].values))

    if matched_communities:
        matched_topic_df = get_matched_topic_df(
            lda_models=[lda_abs, lda_per, bi_lda_abs, bi_lda_per],
            dfs=[uni_document_topics_abs, uni_document_topics_per, bigram_document_topics_abs, bigram_document_topics_per],
            community_id_pairs=matched_communities,       
        )    

        merged_match = pd.merge(matched_topic_df, matched_df[['abs_community', 'members', 'per_community']], 
                                left_on=['absolute_community', 'weighted_community'], 
                                right_on=['abs_community', 'per_community'], 
                                how='inner').drop(['abs_community', 'per_community'], axis=1)

        if not merged_match.empty:
            save_csv_to_directory(data_type + '/LDA/matched/', content_type, month+'_'+year+'.csv', merged_match)
            # merged_match.to_csv(data_type +'/LDA/matched/'+content_type+'_'+data_file, index=False)

    # Get Keywords for Partially Matched Communities
    partial_communities = []
    for ind, row in partial_matched.iterrows():
        partial_communities.append(tuple(row[['abs_community', 'per_community']].values))


    if partial_communities:
        partial_matched_topic_df = get_matched_topic_df(
            lda_models=[lda_abs, lda_per, bi_lda_abs, bi_lda_per],
            dfs=[uni_document_topics_abs, uni_document_topics_per, bigram_document_topics_abs, bigram_document_topics_per],
            community_id_pairs=partial_communities,  
            
        )

        
        merge_partial = pd.merge(partial_matched_topic_df, partial_matched[['abs_community', 'absolute_members', 'weighted_members', 'jaccard_score', 'common_members',	'uncommon_members', 'per_community']], 
                                 left_on=['absolute_community', 'weighted_community'], 
                                 right_on=['abs_community', 'per_community'], 
                                 how='inner').drop(['abs_community', 'per_community'], axis=1)

        if not merge_partial.empty:
            save_csv_to_directory(data_type + '/LDA/partial_matched/', content_type, month+'_'+year+'.csv', merge_partial)
            # merge_partial.to_csv(data_type+'/LDA/partial_matched/'+content_type+'_'+data_file, index=False)


if __name__ == "__main__":
    main()