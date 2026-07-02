import os
from neo4j import GraphDatabase

class MemgraphClient:
    """
    Client wrapper for connecting to the local Memgraph instance.
    Memgraph is compatible with the Neo4j bolt protocol and python driver.
    """
    def __init__(self, uri=None, user=None, password=None):
        self.uri = uri or os.environ.get("GRAPH_DB_URI", "bolt://localhost:7687")
        self.user = user or os.environ.get("GRAPH_DB_USER", "")
        self.password = password or os.environ.get("GRAPH_DB_PASSWORD", "")

    def get_driver(self):
        # Memgraph defaults to empty strings for auth if not set.
        return GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def execute_query(self, query, parameters=None):
        with self.get_driver() as driver:
            driver.verify_connectivity()
            records, summary, keys = driver.execute_query(
                query,
                parameters_=parameters
            )
            return records, summary, keys
