from bs4 import BeautifulSoup
import pandas as pd
import re
import demoji
import unicodedata
import string

with open('utils/stopwords-list.txt', 'r') as f:
    stop_words = []
    for l in f.readlines():
        # print(l)
        stop_words.append(l.strip())

stop_words.extend(['dont', 'im', 'um', 'un', 'cant', 'i', 'me', 'am', 'mm', 'yyyy', 'ill', 'month', 'yesterday', 'day', 'today', 'do', 'not', 'nomnomnomnom'])


def clean_text(text: str) -> str:
    """
        text: a string

        return: modified initial string
    """

    remove_username = re.compile(r'@[^ ]+')
    remove_urls = re.compile(r'https?://[A-Za-z0-9./]+')
    remove_urls_2 = re.compile(r'https?:[^\s]+')
    remove_hashtag = re.compile(r'\#')
    remove_www = re.compile(r'www\S+')
    # remove_cashtags_and_words = re.compile(r'\$\w+')

    replace_with_space = re.compile(r'[/(){}\[\]\|@,;.]')
    # remove_symbols1 = re.compile("[^0-9a-z_ğüşıöç .']")
    remove_not_chars = re.compile(r'[^a-z A-Z]')
    # stopwords = nltk.corpus.stopwords.words('english')
    # stop_words = stopwords.words('english')
    # remove_3chars = re.compile(r'\b\w{1,3}\b')
    remove_ahah = re.compile(r'\b(?:ah)+\b')
    remove_aha = re.compile(r'\b(?:ah)+a\b')
    remove_haha = re.compile(r'\b(?:ha)+\b')
    remove_repetition = re.compile(r'\b(\w+)( \1\b)+')
    remove_jaja = re.compile(r'\b(?:ja)+\b')

    text = text.lower()

    text = remove_username.sub(' ', text)
    text = remove_urls.sub(' ', text)
    text = remove_urls_2.sub(' ', text)
    text = remove_hashtag.sub(' ', text)
    text = remove_www.sub(' ', text)
    text = replace_with_space.sub(' ', text)
    text = remove_ahah.sub(' ', text)
    text = remove_aha.sub(' ', text)
    text = remove_haha.sub(' ', text)
    text = remove_jaja.sub(' ', text)

    # text = remove_cashtags_and_words.sub(' ', text)


    # text = remove_symbols1.sub('', text)
    text = remove_not_chars.sub('', text)
    # text = remove_3chars.sub('', text)
    text = ' '.join([word for word in text.split() if word not in stop_words])
    text = remove_repetition.sub(r'\1', text)

    return text

def replace_emojis(text: str) -> str:
    """
    Replace emojis in the text with their corresponding word using demoji.
    :param text:
    :return:
    """
    for emoji, context in demoji.findall(text).items():
        text = text.replace(emoji, ' ' + context + ' ')
        text = re.sub(' +', ' ', text)
    return text


# remove emoji
def remove_emojis(text: str) -> str:
    """
    Remove emojis in the text.
    :param text:
    :return:
    """
    if isinstance(text, str):
        for emoji, context in demoji.findall(text).items():
            text = text.replace(emoji, ' ')
            text = re.sub(' +', ' ', text)
    return text


# Example function to normalize Unicode strings
def normalize_unicode(text: str) -> str:
    return unicodedata.normalize('NFKD', text)

def clean_html(text: str) -> str:
    return BeautifulSoup(text, "html").get_text(strip=True)


def message_preprocess(text_df):

    # text_df['messages_processed']  = list(map(lambda messages: [remove_emojis(message) for message in messages], text_df['messages']))
    # text_df['messages_processed'] = list(map(lambda messages: [clean_html(message) for message in messages], text_df['messages_processed']))
    # text_df['messages_processed'] = list(map(lambda messages: [normalize_unicode(message) for message in messages], text_df['messages_processed']))
    # text_df['messages_processed']  = list(map(lambda messages: [clean_text(message) for message in messages], text_df['messages_processed']))
    # text_df['messages_processed'] = text_df['messages_processed'].apply(lambda x: [sentence for sentence in x if sentence.strip()])

    text_df['messages_processed'] = text_df['messages'].apply(lambda messages: [remove_emojis(message) for message in messages if isinstance(message, str)])
    text_df['messages_processed'] = text_df['messages_processed'].apply(lambda messages: [clean_html(message) for message in messages])
    text_df['messages_processed'] = text_df['messages_processed'].apply(lambda messages: [normalize_unicode(message) for message in messages])
    text_df['messages_processed'] = text_df['messages_processed'].apply(lambda x: [sentence for sentence in x if sentence.strip()])
    text_df['messages_processed'] = text_df['messages_processed'].apply(lambda x: '.'.join(x))
    # text_df['messages_processed'] = text_df['messages_processed'].apply(lambda messages: [clean_text(message) for message in messages])
    text_df['messages_processed'] = text_df['messages_processed'].apply(lambda messages: clean_text(messages))


    return text_df['messages_processed']
