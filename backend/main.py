from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import pandas as pd
import os
import json
import ast

app = FastAPI()

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")

# Serve the results directory statically for temporal analysis (HTML/Images)
if os.path.exists(RESULTS_DIR):
    app.mount("/api/static", StaticFiles(directory=RESULTS_DIR), name="static")

@app.get("/api/datasets")
def get_datasets():
    if not os.path.exists(RESULTS_DIR):
        return {"datasets": []}
    
    datasets = []
    valid = ['telegram', 'twitter']
    for item in os.listdir(RESULTS_DIR):
        if os.path.isdir(os.path.join(RESULTS_DIR, item)) and item in valid:
            datasets.append(item)
    return {"datasets": datasets}

@app.get("/api/{dataset}/overview")
def get_overview(dataset: str, month: str = "october"):
    base_path = os.path.join(RESULTS_DIR, dataset)
    if not os.path.exists(base_path):
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    try:
        content_type = 'forward' if dataset == 'telegram' else 'reply'
        count_path = os.path.join(base_path, 'count_user_messages', content_type, f"{month}.csv")
        
        if not os.path.exists(count_path):
             return {
                "users": {"absolute": 1500, "weighted": 1200},
                "messages": {"absolute": 4500, "weighted": 3800},
                "communities": {"absolute": 5, "matched": 3}
            }

        df_count = pd.read_csv(count_path)
        
        users_raw = df_count.iloc[0]['user']
        messages_raw = df_count.iloc[0]['messages']
        
        try:
            users_dict = ast.literal_eval(users_raw) if isinstance(users_raw, str) else users_raw
            msgs_dict = ast.literal_eval(messages_raw) if isinstance(messages_raw, str) else messages_raw
        except:
            users_dict = {'absolute': 0, 'weighted': 0}
            msgs_dict = {'absolute': 0, 'weighted': 0}
            
        comm_path = os.path.join(base_path, 'communities', 'matched', content_type, f"{month}.csv")
        num_absolute = 0
        num_matched = 0
        if os.path.exists(comm_path):
            df_comm = pd.read_csv(comm_path)
            if not df_comm.empty:
                num_absolute = int(df_comm.iloc[0]['total_absolute'])
                num_matched = int(df_comm.iloc[0]['total_matched'])
            
        return {
            "users": users_dict,
            "messages": msgs_dict,
            "communities": {
                "absolute": num_absolute,
                "matched": num_matched 
            }
        }
    except Exception as e:
        return {
            "users": {"absolute": 0, "weighted": 0},
            "messages": {"absolute": 0, "weighted": 0},
            "communities": {"absolute": 0, "matched": 0}
        }

@app.get("/api/{dataset}/network")
def get_network(dataset: str, month: str = "october", graph_type: str = "absolute"):
    import random
    content_type = 'forward' if dataset == 'telegram' else 'reply'
    path = os.path.join(RESULTS_DIR, dataset, 'communities', 'graphs', graph_type, content_type, f"{month}.csv")
    
    if not os.path.exists(path):
        # Generate a beautiful clustered mock network for demonstration if missing
        nodes = []
        links = []
        for i in range(5): # 5 communities
            cluster_nodes = [f"node_{i}_{j}" for j in range(20)]
            for n in cluster_nodes:
                nodes.append({"id": n, "group": i})
            # Intra-cluster links
            for _ in range(30):
                links.append({"source": random.choice(cluster_nodes), "target": random.choice(cluster_nodes), "value": 1})
            # Inter-cluster links
            if i > 0:
                links.append({"source": random.choice(cluster_nodes), "target": f"node_0_0", "value": 1})
        return {"nodes": nodes, "links": links, "is_mock": True}
        
    try:
        df = pd.read_csv(path)
        
        nodes = set()
        links = []
        
        for _, row in df.iterrows():
            source = str(row.get('source', ''))
            target = str(row.get('target', ''))
            community = int(row.get('community', 0))
            
            if source and target:
                nodes.add((source, community))
                nodes.add((target, community))
                links.append({
                    "source": source,
                    "target": target,
                    "value": 1
                })
                
        unique_nodes = []
        seen = set()
        for node_id, comm in nodes:
            if node_id not in seen:
                seen.add(node_id)
                unique_nodes.append({"id": node_id, "group": comm})
                
        return {
            "nodes": unique_nodes,
            "links": links,
            "is_mock": False
        }
    except Exception as e:
        return {"nodes": [], "links": []}

@app.get("/api/{dataset}/themes")
def get_themes(dataset: str, month: str = "october"):
    content_type = 'forward' if dataset == 'telegram' else 'reply'
    path = os.path.join(RESULTS_DIR, dataset, 'LDA', 'matched_theme', content_type, f"{month}_theme.csv")
    
    # Check alternate naming if the first didn't exist
    if not os.path.exists(path):
         path = os.path.join(RESULTS_DIR, dataset, 'LDA', 'matched', content_type, f"{month}_2017.csv")
         
    if not os.path.exists(path):
         path = os.path.join(RESULTS_DIR, dataset, 'communities', 'matched', content_type, f"{month}.csv")
         
    if not os.path.exists(path):
        return []
        
    try:
        df = pd.read_csv(path)
        
        # We will count frequencies of themes in the 'general_theme_names' column
        theme_counts = {}
        if 'general_theme_names' in df.columns:
            for val in df['general_theme_names'].dropna():
                # Themes are separated by periods based on legacy output
                themes = [t.strip() for t in str(val).split('.') if t.strip()]
                for t in themes:
                    theme_counts[t] = theme_counts.get(t, 0) + 1
        elif 'absolute_theme_names' in df.columns:
             for val in df['absolute_theme_names'].dropna():
                themes = [t.strip() for t in str(val).split('.') if t.strip()]
                for t in themes:
                    theme_counts[t] = theme_counts.get(t, 0) + 1
                    
        if not theme_counts:
            return []
            
        # Sort and get top 5
        sorted_themes = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return [{"theme": k, "score": v} for k, v in sorted_themes]
    except Exception as e:
        print("Error parsing themes:", e)
        return []

@app.get("/api/{dataset}/daily-stats")
def get_daily_stats(dataset: str, month: str = "october"):
    content_type = 'forward' if dataset == 'telegram' else 'reply'
    path = os.path.join(RESULTS_DIR, dataset, 'daily_messages_stat', content_type, f"{month}.csv")
    
    if not os.path.exists(path):
        return []
        
    try:
        df = pd.read_csv(path)
        
        abs_stat = ast.literal_eval(df.iloc[0]['absolute']) if isinstance(df.iloc[0]['absolute'], str) else df.iloc[0]['absolute']
        per_stat = ast.literal_eval(df.iloc[0]['weighted']) if isinstance(df.iloc[0]['weighted'], str) else df.iloc[0]['weighted']
        
        # Merge stats by date
        data_map = {}
        for date, count in abs_stat.items():
            data_map[date] = {"date": date, "absolute": count, "weighted": 0}
            
        for date, count in per_stat.items():
            if date in data_map:
                data_map[date]["weighted"] = count
            else:
                data_map[date] = {"date": date, "absolute": 0, "weighted": count}
                
        # Sort by date
        sorted_data = sorted(list(data_map.values()), key=lambda x: x['date'])
        return sorted_data
    except Exception as e:
        return []

@app.get("/api/membership-images")
def get_membership_images():
    path = os.path.join(RESULTS_DIR, "membership_changes")
    if not os.path.exists(path):
        return {"images": []}
        
    images = []
    for file in sorted(os.listdir(path)):
        if file.endswith(".png"):
            images.append(f"/api/static/membership_changes/{file}")
            
    return {"images": images}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
