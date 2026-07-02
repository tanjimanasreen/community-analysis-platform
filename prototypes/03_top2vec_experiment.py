import pandas as pd
import json
from top2vec import Top2Vec
from src.topics.text_preprocessor import clean_text

def run_top2vec():
    print("Loading data...")
    df = pd.read_csv('data/telegram-neo4j-sample/samples_500_per_month/sample_translated_january_2019.csv')
    
    # We just need a sample to prototype.
    df = df.dropna(subset=['text'])
    
    print("Cleaning text...")
    df['cleaned_message'] = df['text'].apply(lambda x: clean_text(str(x)))
    docs = df['cleaned_message'].tolist()
    
    # Filter out empty docs
    docs = [d for d in docs if str(d).strip() != '']
    
    print(f"Running Top2Vec on {len(docs)} documents...")
    # Initialize Top2Vec
    # Top2Vec will train a doc2vec model by default
    model = Top2Vec(documents=docs, speed="fast-learn", workers=4)
    
    print("\n--- Top2Vec Results ---")
    topic_words, word_scores, topic_nums = model.get_topics()
    
    results = {}
    for i in range(min(5, len(topic_nums))):
        words = topic_words[i][:10].tolist()
        results[f"Topic {i}"] = words
        print(f"Topic {i}: {words}")
        
    with open('prototypes/results/top2vec_results.json', 'w') as f:
        json.dump(results, f, indent=4)
    print("\nResults saved to prototypes/results/top2vec_results.json")

if __name__ == "__main__":
    run_top2vec()
