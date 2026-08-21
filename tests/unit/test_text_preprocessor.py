import pandas as pd

from src.topics.text_preprocessor import clean_text, message_preprocess


def _preprocess_message(message: str) -> str:
    frame = pd.DataFrame({"messages": [[message]]})
    return message_preprocess(frame).iloc[0]


def test_clean_text_strips_urls():
    assert clean_text("Check this out https://example.com/foo") == "check"


def test_clean_text_strips_usernames():
    assert clean_text("Signal @user and @other_user!") == "signal"


def test_clean_text_removes_hashtags_symbols_but_keeps_word():
    assert clean_text("Loving this #python #coding") == "loving python coding"


def test_message_preprocess_strips_emojis():
    assert _preprocess_message("Signal 😀 planet 🌍") == "signal planet"


def test_message_preprocess_cleans_html():
    assert _preprocess_message("<p>Signal</p> &amp; planet") == "signal planet"


def test_message_preprocess_normalizes_unicode():
    assert _preprocess_message("Café signal") == "cafe signal"


def test_clean_text_collapses_repeated_words():
    assert clean_text("signal signal planet") == "signal planet"


def test_clean_text_lowercases():
    assert clean_text("SiGnAl PlAnEt") == "signal planet"


def test_clean_text_removes_stopwords():
    assert clean_text("this is a test of the system signal") == "test signal"


def test_clean_text_empty():
    assert clean_text("") == ""
    assert clean_text("   ") == ""


def test_clean_text_extended_stopwords():
    assert clean_text("im going to dont do that signal") == "signal"
