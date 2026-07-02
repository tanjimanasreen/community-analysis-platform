import pandas as pd
import ollama
import json
from src.topics.text_preprocessor import clean_text

def run_llm_summarization():
    print("Loading data...")
    df = pd.read_csv('data/telegram-neo4j-sample/samples_500_per_month/sample_translated_january_2019.csv')
    
    # Clean text to remove noise
    df = df.dropna(subset=['text'])
    df['cleaned_message'] = df['text'].apply(lambda x: clean_text(str(x)))
    
    # Sample 50 representative messages
    docs = df['cleaned_message'].sample(min(50, len(df)), random_state=42).tolist()
    docs = [str(d) for d in docs if str(d).strip() != '']
    
    messages_text = "\n".join([f"- {doc}" for doc in docs])
    
    prompt = f"""
    You are an expert community analyst. Read the following recent messages from a Telegram community.
    Identify the 3-5 main themes or topics being discussed.
    For each theme, provide a short name and a 1-sentence description.
    
    Messages:
    {messages_text}
    
    Format your response as JSON:
    {{
        "themes": [
            {{"name": "Theme 1", "description": "..."}},
            ...
        ]
    }}
    """
    
    print("Querying Ollama (gemma4:12b)...")
    try:
        response = ollama.chat(model='gemma4:12b', messages=[
            {
                'role': 'user',
                'content': prompt,
            },
        ])
        
        result_text = response['message']['content']
        print("\n--- LLM End-to-End Results ---")
        print(result_text)
        
        # Save to file
        with open('prototypes/results/llm_results.txt', 'w') as f:
            f.write(result_text)
        print("\nResults saved to prototypes/results/llm_results.txt")
        
    except Exception as e:
        print(f"Error querying Ollama: {e}")
        print("Note: Make sure Ollama is running and 'gemma4:12b' is pulled.")

if __name__ == "__main__":
    run_llm_summarization()
