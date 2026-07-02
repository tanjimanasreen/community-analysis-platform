import pytest
import pandas as pd
from src.topics.text_preprocessor import clean_text, replace_emojis, remove_emojis, message_preprocess
from src.topics.topic_matching import get_cutoff_probability

def test_clean_text():
    text = "Dog @username https://example.com #hashtag www.test.com ahaha jajaja. How are you?"
    cleaned = clean_text(text)
    assert "username" not in cleaned
    assert "https" not in cleaned
    assert "hashtag" in cleaned
    assert "www" not in cleaned
    assert "ahaha" not in cleaned
    assert "jajaja" not in cleaned
    assert "dog" in cleaned
    
def test_message_preprocess():
    df = pd.DataFrame({
        'messages': [
            ["This is a test message 😊.", "Another message https://link.com @user"]
        ]
    })
    
    processed = message_preprocess(df)
    assert len(processed) == 1
    processed_text = processed.iloc[0]
    
    assert "😊" not in processed_text
    assert "linkcom" not in processed_text
    assert "user" not in processed_text
    assert "test" in processed_text
    assert "message" in processed_text
    
def test_get_cutoff_probability():
    # If we have a smooth decrease, elbow should be found
    probs = [0.5, 0.2, 0.1, 0.05, 0.02, 0.01, 0.005, 0.001]
    cutoff = get_cutoff_probability(probs)
    # The elbow is probably around 0.1 or 0.05
    assert cutoff > 0.0
