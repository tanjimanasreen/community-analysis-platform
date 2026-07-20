import pytest
from src.topics.text_preprocessor import clean_text

def test_clean_text_strips_urls():
    assert clean_text("Check this out https://example.com/foo") == "check"

def test_clean_text_strips_usernames():
    assert clean_text("Hello @user and @other_user!") == "hello"

def test_clean_text_removes_hashtags_symbols_but_keeps_word():
    assert clean_text("Loving this #python #coding") == "loving python coding"

def test_clean_text_strips_emojis():
    assert clean_text("Hello 😀 world 🌍") == "hello world"

def test_clean_text_decodes_html():
    assert clean_text("Hello &amp; world <p>test</p>") == "hello world test"

def test_clean_text_collapses_repeated_words():
    assert clean_text("hello hello world") == "hello world"

def test_clean_text_lowercases():
    assert clean_text("HeLlO wOrLd") == "hello world"

def test_clean_text_removes_stopwords():
    # 'this' and 'is' are usually stopwords. 'test' might not be.
    text = "this is a test of the system"
    result = clean_text(text)
    assert "this" not in result
    assert "is" not in result
    assert "test" in result
    assert "system" in result

def test_clean_text_empty():
    assert clean_text("") == ""
    assert clean_text("   ") == ""

def test_clean_text_extended_stopwords():
    # Test typical social media stopwords extended in the custom list
    assert clean_text("im going to dont do that") == "going"
