from kneed import KneeLocator
import pandas as pd

def get_cutoff_probability(probabilities):
    knee = KneeLocator(range(1, len(probabilities) + 1), probabilities, curve="convex", direction="decreasing", S=3)

    if knee.elbow is not None:
        elbow_index = knee.elbow
        cutoff_probability = probabilities[elbow_index - 1]
    else:
        cutoff_index = int(len(probabilities) * 0.1)
        cutoff_probability = probabilities[cutoff_index - 1]

    return cutoff_probability

def get_matched_topic_df(lda_models, dfs, community_id_pairs, num_topics=15, top_n_keywords=50):
    lda_titles = ['absolute_unigram', 'weighted_unigram', 'absolute_bigram', 'weighted_bigram']
    community_order = ['absolute_community', 'weighted_community', 'absolute_community', 'weighted_community']
    
    community_topic_data = []
    
    for absolute_id, weighted_id in community_id_pairs:
        community_ids_ordered = [absolute_id, weighted_id, absolute_id, weighted_id]
        community_topic_details = {}
        
        for i, (lda_model, df, community_id) in enumerate(zip(lda_models, dfs, community_ids_ordered)):
            df_community = df[df['community_number'] == community_id]
            
            if df_community.empty:
                continue
                
            topic_id = df_community['dominant_topic'].iloc[0]
            
            if topic_id == -1:
                keywords = []
            else:
                topic_keywords_data = lda_model.show_topic(topic_id, topn=top_n_keywords)
                probabilities = [prob for word, prob in topic_keywords_data]

                cutoff_probability = get_cutoff_probability(probabilities)
                keywords = [word for word, prob in topic_keywords_data if prob >= cutoff_probability]

            community_topic_details[community_order[i]] = community_id
            community_topic_details[lda_titles[i]+"_topic"] = topic_id
            community_topic_details[lda_titles[i]+"_keywords"] = keywords
            
        community_topic_data.append(community_topic_details)
        
    community_topic_df = pd.DataFrame(community_topic_data)
    
    # Ensure all columns exist even if data is empty
    expected_columns = [
        'absolute_community', 'absolute_unigram_topic', 'absolute_unigram_keywords', 
        'weighted_community', 'weighted_unigram_topic', 'weighted_unigram_keywords', 
        'absolute_bigram_topic', 'absolute_bigram_keywords', 
        'weighted_bigram_topic', 'weighted_bigram_keywords'
    ]
    
    for col in expected_columns:
        if col not in community_topic_df.columns:
            community_topic_df[col] = pd.Series(dtype='object')
            
    return community_topic_df
