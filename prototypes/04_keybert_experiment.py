import pandas as pd
import json
from keybert import KeyBERT
from src.topics.text_preprocessor import clean_text

def run_keybert():
    print("Loading data...")
    df = pd.read_csv('data/telegram-neo4j-sample/samples_500_per_month/sample_translated_january_2019.csv')
    
    # We just need a sample to prototype.
    df = df.dropna(subset=['text'])
    
    print("Cleaning text...")
    df['cleaned_message'] = df['text'].apply(lambda x: clean_text(str(x)))
    docs = df['cleaned_message'].tolist()
    
    # Filter out empty docs
    docs = [d for d in docs if str(d).strip() != '']
    
    # Join documents to represent a "community"
    community_doc = " ".join(docs)
    
    print("Running KeyBERT on aggregated community text...")
    # Initialize KeyBERT
    kw_model = KeyBERT()
    
    # Extract keywords
    print("\n--- KeyBERT Results (Unigrams) ---")
    keywords = kw_model.extract_keywords(community_doc, keyphrase_ngram_range=(1, 1), stop_words='english', top_n=10)
    print(keywords)
    
    print("\n--- KeyBERT Results (Bigrams/Trigrams) ---")
    keyphrases = kw_model.extract_keywords(community_doc, keyphrase_ngram_range=(2, 3), stop_words='english', top_n=10)
    print(keyphrases)
    
    results = {
        "keywords": [k[0] for k in keywords],
        "keyphrases": [k[0] for k in keyphrases]
    }
    
    with open('prototypes/results/keybert_results.json', 'w') as f:
        json.dump(results, f, indent=4)
    print("\nResults saved to prototypes/results/keybert_results.json")

if __name__ == "__main__":
    run_keybert()
