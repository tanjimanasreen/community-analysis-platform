import os
from bs4 import BeautifulSoup
import pandas as pd
import re
import demoji
import unicodedata
import string

# Load stop words from the same directory as this script
current_dir = os.path.dirname(os.path.abspath(__file__))
stopwords_path = os.path.join(current_dir, "stopwords-list.txt")

with open(stopwords_path, "r") as f:
    stop_words = []
    for l in f.readlines():
        stop_words.append(l.strip())

stop_words.extend(
    [
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
    ]
)


def clean_text(text: str) -> str:
    """
    Cleans text by removing URLs, usernames, hashtags, special characters, and repeated sequences.
    """
    remove_username = re.compile(r"@[^ ]+")
    remove_urls = re.compile(r"https?://[A-Za-z0-9./]+")
    remove_urls_2 = re.compile(r"https?:[^\s]+")
    remove_hashtag = re.compile(r"\#")
    remove_www = re.compile(r"www\S+")

    replace_with_space = re.compile(r"[/(){}\[\]\|@,;.]")
    remove_not_chars = re.compile(r"[^a-z A-Z]")

    remove_ahah = re.compile(r"\b(?:ah)+\b")
    remove_aha = re.compile(r"\b(?:ah)+a\b")
    remove_haha = re.compile(r"\b(?:ha)+\b")
    remove_repetition = re.compile(r"\b(\w+)( \1\b)+")
    remove_jaja = re.compile(r"\b(?:ja)+\b")

    text = text.lower()

    text = remove_username.sub(" ", text)
    text = remove_urls.sub(" ", text)
    text = remove_urls_2.sub(" ", text)
    text = remove_hashtag.sub(" ", text)
    text = remove_www.sub(" ", text)
    text = replace_with_space.sub(" ", text)
    text = remove_ahah.sub(" ", text)
    text = remove_aha.sub(" ", text)
    text = remove_haha.sub(" ", text)
    text = remove_jaja.sub(" ", text)

    text = remove_not_chars.sub("", text)
    text = " ".join([word for word in text.split() if word not in stop_words])
    text = remove_repetition.sub(r"\1", text)

    return text


def replace_emojis(text: str) -> str:
    for emoji, context in demoji.findall(text).items():
        text = text.replace(emoji, " " + context + " ")
        text = re.sub(" +", " ", text)
    return text


def remove_emojis(text: str) -> str:
    if isinstance(text, str):
        for emoji, context in demoji.findall(text).items():
            text = text.replace(emoji, " ")
            text = re.sub(" +", " ", text)
    return text


def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFKD", text)


def clean_html(text: str) -> str:
    return BeautifulSoup(text, "html.parser").get_text(strip=True)


def message_preprocess(text_df):
    text_df["messages_processed"] = text_df["messages"].apply(
        lambda messages: [
            remove_emojis(message) for message in messages if isinstance(message, str)
        ]
    )
    text_df["messages_processed"] = text_df["messages_processed"].apply(
        lambda messages: [clean_html(message) for message in messages]
    )
    text_df["messages_processed"] = text_df["messages_processed"].apply(
        lambda messages: [normalize_unicode(message) for message in messages]
    )
    text_df["messages_processed"] = text_df["messages_processed"].apply(
        lambda x: [sentence for sentence in x if sentence.strip()]
    )
    text_df["messages_processed"] = text_df["messages_processed"].apply(
        lambda x: ".".join(x)
    )
    text_df["messages_processed"] = text_df["messages_processed"].apply(
        lambda messages: clean_text(messages)
    )

    return text_df["messages_processed"]
