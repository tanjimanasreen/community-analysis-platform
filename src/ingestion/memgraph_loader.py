import csv
import ast
import re
from src.ingestion.schema import PRIMARY_KEYS, TELEGRAM_RELATION_MAP, TWITTER_RELATION_MAP

def clean_dict_string(dict_str):
    """
    Cleans the stringified neo4j dictionaries so ast.literal_eval can parse them.
    Replaces neo4j.time.DateTime(...) with a string representation.
    """
    datetime_pattern = re.compile(r"neo4j\.time\.DateTime\((.*?)tzinfo=<UTC>\)", re.DOTALL)
    cleaned = datetime_pattern.sub(r"'neo4j_time_(\1)'", dict_str)
    return cleaned

def generate_cypher(source_dict, target_dict, relation, platform):
    mapping = TELEGRAM_RELATION_MAP if platform == 'telegram' else TWITTER_RELATION_MAP
    if relation not in mapping:
        # Fallback or skip if relation is not mapped
        return None, None
    
    source_label, target_label = mapping[relation]
    
    source_pk_field = PRIMARY_KEYS.get(source_label, 'id')
    target_pk_field = PRIMARY_KEYS.get(target_label, 'id')
    
    # In some cases, dicts might not have the primary key. 
    # Try to find a fallback if the main one is missing.
    source_pk_val = source_dict.get(source_pk_field) or source_dict.get('id') or source_dict.get('to_id') or source_dict.get('from_id')
    target_pk_val = target_dict.get(target_pk_field) or target_dict.get('id') or target_dict.get('to_id') or target_dict.get('from_id')
    
    if not source_pk_val or not target_pk_val:
        return None, None

    # Construct MERGE query
    # We use parameters to prevent Cypher injection and handle types cleanly.
    query = f"""
    MERGE (s:{source_label} {{{source_pk_field}: $source_pk}})
    SET s += $source_props
    SET s.platform = $platform
    
    MERGE (t:{target_label} {{{target_pk_field}: $target_pk}})
    SET t += $target_props
    SET t.platform = $platform
    
    MERGE (s)-[r:{relation}]->(t)
    """
    
    params = {
        "source_pk": source_pk_val,
        "source_props": source_dict,
        "target_pk": target_pk_val,
        "target_props": target_dict,
        "platform": platform
    }
    
    return query, params

class MemgraphLoader:
    def __init__(self, client=None):
        if client is None:
            from src.graph_store.memgraph_client import MemgraphClient

            client = MemgraphClient()
        self.client = client

    def load_csv(self, file_path, platform):
        """
        Loads the exported CSV and imports it into Memgraph.
        """
        success_count = 0
        error_count = 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    source_str = clean_dict_string(row['source'])
                    target_str = clean_dict_string(row['target'])
                    
                    source_dict = ast.literal_eval(source_str)
                    target_dict = ast.literal_eval(target_str)
                    relation = row['relation']
                    
                    query, params = generate_cypher(source_dict, target_dict, relation, platform)
                    if query:
                        self.client.execute_query(query, params)
                        success_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    print(f"Error loading row: {row}. Error: {e}")
                    error_count += 1
                    
        return success_count, error_count
