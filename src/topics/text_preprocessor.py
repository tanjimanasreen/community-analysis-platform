from __future__ import annotations

import os
import re
import unicodedata
from collections.abc import Iterable

import demoji
import pandas as pd
from bs4 import BeautifulSoup

_current_dir = os.path.dirname(os.path.abspath(__file__))
_stopwords_path = os.path.join(_current_dir, "stopwords-list.txt")

with open(_stopwords_path, "r", encoding="utf-8") as stopword_file:
    _stop_words = {line.strip() for line in stopword_file if line.strip()}

_stop_words.update(
    {
        "dont",
        "im",
        "um",
        "un",
        "cant",
        "i",
        "me",
        "am",
        "mm",
        "yyyy",
        "ill",
        "month",
        "yesterday",
        "day",
        "today",
        "do",
        "not",
        "nomnomnomnom",
    }
)

# Compile once.  The previous implementation rebuilt every expression for every
# community document, which is expensive for large Twitter runs.
_REMOVE_USERNAME = re.compile(r"@[^ ]+")
_REMOVE_URLS = re.compile(r"https?://[A-Za-z0-9./]+")
_REMOVE_URLS_2 = re.compile(r"https?:[^\s]+")
_REMOVE_HASHTAG = re.compile(r"\#")
_REMOVE_WWW = re.compile(r"www\S+")
_REPLACE_WITH_SPACE = re.compile(r"[/(){}\[\]\|@,;.]")
_REMOVE_NOT_CHARS = re.compile(r"[^a-z A-Z]")
_REMOVE_AHAH = re.compile(r"\b(?:ah)+\b")
_REMOVE_AHA = re.compile(r"\b(?:ah)+a\b")
_REMOVE_HAHA = re.compile(r"\b(?:ha)+\b")
_REMOVE_REPETITION = re.compile(r"\b(\w+)( \1\b)+")
_REMOVE_JAJA = re.compile(r"\b(?:ja)+\b")
_MULTISPACE = re.compile(r" +")


def clean_text(text: str) -> str:
    """Apply the thesis text-cleaning rules to one combined document."""
    text = text.lower()
    text = _REMOVE_USERNAME.sub(" ", text)
    text = _REMOVE_URLS.sub(" ", text)
    text = _REMOVE_URLS_2.sub(" ", text)
    text = _REMOVE_HASHTAG.sub(" ", text)
    text = _REMOVE_WWW.sub(" ", text)
    text = _REPLACE_WITH_SPACE.sub(" ", text)
    text = _REMOVE_AHAH.sub(" ", text)
    text = _REMOVE_AHA.sub(" ", text)
    text = _REMOVE_HAHA.sub(" ", text)
    text = _REMOVE_JAJA.sub(" ", text)
    text = _REMOVE_NOT_CHARS.sub("", text)
    text = " ".join(word for word in text.split() if word not in _stop_words)
    return _REMOVE_REPETITION.sub(r"\1", text)


def replace_emojis(text: str) -> str:
    for emoji, context in demoji.findall(text).items():
        text = text.replace(emoji, f" {context} ")
        text = _MULTISPACE.sub(" ", text)
    return text


def remove_emojis(text: str) -> str:
    if not isinstance(text, str):
        return text
    for emoji in demoji.findall(text):
        text = text.replace(emoji, " ")
        text = _MULTISPACE.sub(" ", text)
    return text


def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFKD", text)


def clean_html(text: str) -> str:
    # Strip unencodable surrogates that break BeautifulSoup
    clean_text = text.encode("utf-8", "ignore").decode("utf-8")
    return BeautifulSoup(clean_text, "html.parser").get_text(strip=True)


def _preprocess_messages(messages: object) -> str:
    if not isinstance(messages, Iterable) or isinstance(messages, (str, bytes)):
        return clean_text("")

    cleaned_messages: list[str] = []
    for message in messages:
        if not isinstance(message, str):
            continue
        cleaned = normalize_unicode(clean_html(remove_emojis(message)))
        if cleaned.strip():
            cleaned_messages.append(cleaned)
    return clean_text(".".join(cleaned_messages))


def message_preprocess(text_df: pd.DataFrame) -> pd.Series:
    """Preprocess community message lists in a single dataframe pass."""
    if "messages" not in text_df.columns:
        raise KeyError("Community messages dataframe is missing column: messages")
    return text_df["messages"].map(_preprocess_messages)
