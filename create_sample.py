import pandas as pd
t_rows = []

# Read the 11 GB CSV in chunks
chunk_size = 1000
chunks = []
for chunk in pd.read_csv('data/raw/twitter/retweet_quote/2017/retweet_january_2017.csv', chunksize=1000):
    chunks.append(chunk)
    # Stop early, for example after reading 200,000 rows
    if len(chunks) * chunk_size >= 200000:
        break

# Concatenate and save
df_sampled = pd.concat(chunks, ignore_index=True)
df_sampled.to_csv('data/raw/twitter/retweet_quote/2017/retweet_january_2017_sampled.csv', index=False)
