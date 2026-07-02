import pandas as pd
import json
import sys
from bertopic import BERTopic
from src.topics.text_preprocessor import clean_text

def run_bertopic():
    print("Loading data...")
    df = pd.read_csv('data/telegram-neo4j-sample/samples_500_per_month/sample_translated_january_2019.csv')
    
    # Clean text to remove noise
    df = df.dropna(subset=['text'])
    
    print("Cleaning text...")
    df['cleaned_message'] = df['text'].apply(lambda x: clean_text(str(x)))
    docs = df['cleaned_message'].tolist()
    
    # Filter out empty docs
    docs = [d for d in docs if str(d).strip() != '']
    
    print(f"Running BERTopic on {len(docs)} documents...")
    # Initialize BERTopic
    topic_model = BERTopic(language="english", calculate_probabilities=False, verbose=True)
    
    # Fit the model
    topics, probs = topic_model.fit_transform(docs)
    
    print("\n--- BERTopic Results ---")
    topic_info = topic_model.get_topic_info()
    print(topic_info.head(10))
    
    # Extract the top 5 topics and their words
    results = {}
    for topic_id in topic_info['Topic'].head(6):
        if topic_id == -1: continue # Skip outlier topic
        words = [word for word, _ in topic_model.get_topic(topic_id)]
        results[f"Topic {topic_id}"] = words
        print(f"Topic {topic_id}: {words}")
        
    with open('prototypes/results/bertopic_results.json', 'w') as f:
        json.dump(results, f, indent=4)
    print("\nResults saved to prototypes/results/bertopic_results.json")

if __name__ == "__main__":
    run_bertopic()
