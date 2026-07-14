import ast
import re
import langdetect
import warnings
import pandas as pd
from langdetect import detect
from langdetect import DetectorFactory

DetectorFactory.seed = 0
target_lang = 'en'
warnings.filterwarnings("ignore")

def remove_urls(text):
    """
    This function removes the URLs from the text string
    Input: Text string
    Output: Cleaned text string
    """
    text = re.sub(r'https?:[^\s]+', ' ', text)
    text = re.sub(r'www\S+', ' ', text)
    return text

def detect_english(source_txt, index):
    """
    This function
    """
    if len(source_txt.strip()) == 0:
        return False
    else:
        try:
            result_lang = detect(source_txt)

            if result_lang == target_lang:
                return True

            else:

                return False
        except langdetect.lang_detect_exception.LangDetectException:
            # print(source_txt, index)
            return True

def lang_detection(df_data):
    df_data['text_translated'] = df_data['text'].apply(remove_urls)

    for ind, row in df_data.iterrows():
        df_data.at[ind, 'is_english'] = detect_english(row['text_translated'], ind)

    return df_data
