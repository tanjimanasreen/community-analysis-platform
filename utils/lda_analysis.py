from gensim.models import CoherenceModel, LdaModel
from nltk import word_tokenize, ngrams
from nltk.tokenize import WordPunctTokenizer, RegexpTokenizer
from gensim import models
from gensim.models import Phrases
from kneed import KneeLocator
import matplotlib.pyplot as plt
import pandas as pd
import gensim
import spacy
nlp = spacy.load('en_core_web_sm', disable=['parser', 'ner'])
# nlp.max_length = 3000000
nlp.max_length = 5000000 

num_topics = 15
topN_keywords = 50

def lemmatization(texts, allowed_postags=['NOUN', 'ADJ', 'VERB', 'ADV']):
    """https://spacy.io/api/annotation"""
    texts_out = []
    for sent in texts:
        doc = nlp(" ".join(sent)) 
        # texts_out.append([token.lemma_ for token in doc if token.pos_ in allowed_postags])
        texts_out.append([token.lemma_ for token in doc])
    return texts_out


def get_lda(dictionary, corpus):
    
    lda_model = LdaModel(corpus=corpus,
                    id2word=dictionary ,
                    num_topics=num_topics, 
                    random_state=100,
                    iterations = 100,
                    chunksize=20,
                    passes=80,
                    alpha='auto', 
                    eta='auto')
    
    return lda_model


def get_lda_stat(lda_model, corpus, id2word, lemmatized_tokens):
    perplexity_lda = lda_model.log_perplexity(corpus)  # a measure of how good the model is. lower the better.

    # Compute Coherence Score
    coherence_model_lda = CoherenceModel(model=lda_model, texts=lemmatized_tokens, dictionary=id2word, coherence='c_v')
    coherence_lda = coherence_model_lda.get_coherence()

    return perplexity_lda, coherence_lda


def get_topic_keywords(lda_model, topic_id, id2word, topn):
        """Retrieve the top n keywords for a given topic."""
        top_words = lda_model.get_topic_terms(topic_id, topn=topn)
        top_keywords = [id2word[word_id] for word_id, prob in top_words]
        return ', '.join(top_keywords)
    
def assign_dominant_topic(lda_model, corpus, id2word, data, topn_keywords):
    """
    Assigns the dominant topic and its top N keywords to each document in the provided DataFrame.
    
    Parameters:
    - lda_model: Trained LDA model.
    - corpus: List of documents in BoW format.
    - id2word: Dictionary used for the LDA model.
    - data: DataFrame containing the documents.
    - topn_keywords: Number of top keywords to retrieve for the dominant topic.
    
    Returns:
    - DataFrame with two new columns: 'dominant_topic' and 'topic_keywords'.
    """
        
    # Initialize lists to store results
    dominant_topics = []
    topic_keywords = []
    
    # Iterate over the corpus to get the dominant topic and keywords for each document
    for doc_bow in corpus:
        topic_distribution = lda_model.get_document_topics(doc_bow)
        topic_distribution = sorted(topic_distribution, key=lambda x: x[1], reverse=True)
        dominant_topic = topic_distribution[0][0]
        dominant_topics.append(dominant_topic)
        keywords = get_topic_keywords(lda_model, dominant_topic, id2word, topn=topn_keywords)
        topic_keywords.append(keywords)
    
    # Add the results to the DataFrame
    data['dominant_topic'] = dominant_topics
    data['topic_keywords'] = topic_keywords
    
    return data[['community_number', 'dominant_topic', 'topic_keywords', 'messages']]


# Unigram Model
def get_unigram_tokens(text_df):
    tokenizer = RegexpTokenizer(r'\w+')

    data_tokens = list(map(tokenizer.tokenize, text_df['messages_processed']))
    
    return data_tokens

def get_unigram_lda(text_df):
    
    data_tokens = get_unigram_tokens(text_df)

    lemmatized_tokens = lemmatization(data_tokens, allowed_postags=['NOUN', 'ADJ', 'VERB', 'ADV'])
    # lemmatized_tokens = [lst for lst in lemmatized_tokens if lst]

    #Get Dictionary
    id2word  = gensim.corpora.Dictionary(lemmatized_tokens) 

    # id2word.filter_extremes(no_below=2, no_above=0.2)

    #Get Corpus
    corpus = [id2word.doc2bow(doc) for doc in lemmatized_tokens]

    # model_list, coherence_values = compute_coherence_values(id2word, corpus, lemmatized_tokens, limit, start, step)
    # draw_coherence(limit, start, step, coherence_values)
    
   
    optimal_model = get_lda(id2word, corpus)

    perplexity, coherence = get_lda_stat(optimal_model, corpus, id2word, lemmatized_tokens)
    
    data = text_df.copy()
    document_topics = assign_dominant_topic(optimal_model, corpus, id2word, data, topn_keywords=topN_keywords)
    
    # plot_top_words(optimal_model, num_topics, 20, output_filepath='top_words_uni_abs.png')
    # plot_top_words_plotly(optimal_model, num_topics, 20)
    # plot_document_topics(optimal_model, corpus, num_topics)
    
    # n_top_topics=3
    
    # display(get_top_topics_per_document(optimal_model, corpus, n_top_topics))
    return document_topics, optimal_model, perplexity, coherence



# Bigram Model
def get_bigrams_tokens(text_df):
    tokenizer = RegexpTokenizer(r'\w+')

    data_tokens = list(map(tokenizer.tokenize, text_df['messages_processed']))

    bigrams_tokens = lemmatization(data_tokens, allowed_postags=['NOUN', 'ADJ', 'VERB', 'ADV'])

    # Add bigrams and trigrams to docs (only ones that appear 5 times or more).
    bigram = Phrases(bigrams_tokens, min_count=5)
    trigram = Phrases(bigram[bigrams_tokens])
    
    for idx in range(len(bigrams_tokens)):
        for token in bigram[bigrams_tokens[idx]]:
            if '_' in token:
                # Token is a bigram, add to document.
                bigrams_tokens[idx].append(token)
        for token in trigram[bigrams_tokens[idx]]:
            if '_' in token:
                # Token is a bigram, add to document.
                bigrams_tokens[idx].append(token)
                
    return bigrams_tokens

def get_bigram_lda(text_df):
    
    bigrams_tokens = get_bigrams_tokens(text_df)
    
    #Get Dictionary
    id2word  = gensim.corpora.Dictionary(bigrams_tokens) 

    # id2word.filter_extremes(no_below=2, no_above=0.2)

    #Get Corpus
    corpus = [id2word.doc2bow(doc) for doc in bigrams_tokens]

    optimal_model = get_lda(id2word, corpus)
    
    perplexity, coherence = get_lda_stat(optimal_model, corpus, id2word, bigrams_tokens)

    data = text_df.copy()
    document_topics = assign_dominant_topic(optimal_model, corpus, id2word, data, topn_keywords=topN_keywords)

    # plot_top_words(optimal_model, num_topics, 20, output_filepath='top_words_bi_abs.png')
    # display(get_top_topics_per_document(optimal_model, corpus, n_top_topics=1))

    return document_topics, optimal_model, perplexity, coherence
    


# Generation of the Matched and Partially Matched Communities and their Topics
def get_cutoff_probability(probabilities):
    """
    This function takes a list of probabilities and returns the cutoff probability
    based on the elbow point detected using the KneeLocator. If no elbow point is detected,
    a default cutoff (top 10%) is applied.
    
    :param probabilities: A list of probabilities.
    :return: The cutoff probability value.
    """
    # Use KneeLocator to find the elbow point
    knee = KneeLocator(range(1, len(probabilities) + 1), probabilities, curve="convex", direction="decreasing", S=3)

    # Check if a knee (elbow point) was found
    if knee.elbow is not None:
        elbow_index = knee.elbow
        cutoff_probability = probabilities[elbow_index - 1]  # Indexing starts from 0
    else:
        # Fallback strategy: Use top 10% as the cutoff if no elbow point is found
        cutoff_index = int(len(probabilities) * 0.1)  # Top 10%
        cutoff_probability = probabilities[cutoff_index - 1]

    return cutoff_probability

def get_matched_topic_df(lda_models, dfs, community_id_pairs, num_topics=num_topics, top_n_keywords=topN_keywords):
    # Titles for different LDA models in the desired order
    lda_titles = ['absolute_unigram', 'weighted_unigram', 'absolute_bigram', 'weighted_bigram']
    community_order = ['absolute_community', 'weighted_community', 'absolute_community', 'weighted_community']
    
   
    community_topic_df = pd.DataFrame(columns=['absolute_community', 'absolute_unigram_topic', 'absolute_unigram_keywords', 'weighted_community',
                                      'weighted_unigram_topic', 'weighted_unigram_keywords', 'absolute_bigram_topic',
                                       'absolute_bigram_keywords', 'weighted_bigram_topic', 'weighted_bigram_keywords']) 
    community_topic_details = {}
    # Iterate over each pair of community IDs
    for absolute_id, weighted_id in community_id_pairs:
        
        # Order of community IDs to match the order of LDA models
        community_ids_ordered = [absolute_id, weighted_id, absolute_id, weighted_id]
        # Loop through each LDA model and its corresponding dataframe in the new order
        for i, (lda_model, df, community_id) in enumerate(zip(lda_models, dfs, community_ids_ordered)):
            # Filter the dataframe for the current community_id
            df_community = df[df['community_number'] == community_id]
            
            
            # Get the dominant topic for the community
            topic_id = df_community['dominant_topic'].iloc[0]
            
            # Get the top n keywords for that topic
            topic_keywords_data = lda_model.show_topic(topic_id, topn=top_n_keywords)
            # print(topic_keywords_data)
            
            probabilities = [prob for word, prob in topic_keywords_data]

            # plt.plot(range(1, len(probabilities) + 1), probabilities, marker='o')
            # plt.xlabel('# of words (TopN)')
            # plt.ylabel('Probability')
            # plt.title('Elbow Method for Word Probability Cutoff')
            # plt.show()

            cutoff_probability = get_cutoff_probability(probabilities)

            # filtered_words = [(word, prob) for word, prob in topic_keywords_data if prob >= cutoff_probability]
            keywords = [word for word, prob in topic_keywords_data if prob >= cutoff_probability]

            # Extract Community Topic Details
            community_topic_details[community_order[i]] = community_id
            community_topic_details[lda_titles[i]+"_topic"] = topic_id
            community_topic_details[lda_titles[i]+"_keywords"] = keywords
            
        community_topic_df = community_topic_df.append(community_topic_details, ignore_index=True)
        
      
    return community_topic_df
        

# Old code
# def get_matched_topic_df(lda_models, dfs, community_id_pairs, num_topics=num_topics, top_n_keywords=topN_keywords):
#     # Titles for different LDA models in the desired order
#     lda_titles = ['absolute_unigram', 'weighted_unigram', 'absolute_bigram', 'weighted_bigram']
#     community_order = ['absolute_community', 'weighted_community', 'absolute_community', 'weighted_community']
    
   
#     community_topic_df = pd.DataFrame(columns=['absolute_community', 'absolute_unigram_topic', 'absolute_unigram_keywords', 'weighted_community',
#                                       'weighted_unigram_topic', 'weighted_unigram_keywords', 'absolute_bigram_topic',
#                                        'absolute_bigram_keywords', 'weighted_bigram_topic', 'weighted_bigram_keywords']) 
#     community_topic_details = {}
#     # Iterate over each pair of community IDs
#     for absolute_id, weighted_id in community_id_pairs:
        
#         # Order of community IDs to match the order of LDA models
#         community_ids_ordered = [absolute_id, weighted_id, absolute_id, weighted_id]
#         # Loop through each LDA model and its corresponding dataframe in the new order
#         for i, (lda_model, df, community_id) in enumerate(zip(lda_models, dfs, community_ids_ordered)):
#             # Filter the dataframe for the current community_id
#             df_community = df[df['community_number'] == community_id]
            
            
#             # Get the dominant topic for the community
#             topic_id = df_community['dominant_topic'].iloc[0]
            
#             # Get the top n keywords for that topic
#             topic_keywords_data = lda_model.show_topic(topic_id, topn=top_n_keywords)
#             print(topic_keywords_data)
#             keywords = [word for word, prob in topic_keywords_data]
#             probabilities = [prob for word, prob in topic_keywords_data]
            
#             # Extract Community Topic Details
#             community_topic_details[community_order[i]] = community_id
#             community_topic_details[lda_titles[i]+"_topic"] = topic_id
#             community_topic_details[lda_titles[i]+"_keywords"] = keywords
            
#         community_topic_df = community_topic_df.append(community_topic_details, ignore_index=True)
        
      
#     return community_topic_df
        


