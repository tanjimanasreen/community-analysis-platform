import sys
from src.cli import validate_config, _prepare_translation_candidate_texts
config = validate_config("configs/telegram/forwarded_message_evolution.yml")
all_texts, dataset_count = _prepare_translation_candidate_texts(config)
unique_texts = set(all_texts)
total_chars = sum(len(text) for text in unique_texts)
print("Total texts across all months:", len(all_texts))
print("Total unique texts (what Azure sees):", len(unique_texts))
print("Total characters in unique texts:", total_chars)
