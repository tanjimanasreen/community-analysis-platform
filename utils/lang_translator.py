import ast
import time
import re
import warnings
import pandas as pd
from deep_translator import GoogleTranslator

warnings.filterwarnings("ignore")
target_lang = 'en'
google_translator = GoogleTranslator(source='auto', target=target_lang)

def translate_english(source_txt, index):
    if len(source_txt.strip()) == 0:
        return source_txt, False
    else:
        try:
            time.sleep(1)
            translated_text = google_translator.translate(source_txt)
            print("translated till", index)
            return translated_text, True
        except Exception as e:
            print(e)
            print(source_txt, index)
            return source_txt, False

def lang_translate(data):

    data['is_translated'] = False
    df_translate = data[data.is_english == False]

    for ind, row in df_translate.iterrows():
        df_translate.at[ind, 'text_translated'], df_translate.at[ind, 'is_translated'] = translate_english(row['text_translated'], ind)

    data.update(df_translate)

    return data
