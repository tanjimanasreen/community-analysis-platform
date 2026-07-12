import os

# Explicitly direct local result storage to the private directory, separated from DB
os.environ.setdefault("PREFECT_LOCAL_STORAGE_PATH", os.path.abspath(".prefect_results"))
