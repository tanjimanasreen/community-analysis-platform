from src.config.settings import get_database_settings
from neo4j import GraphDatabase


class MemgraphClient:
    """
    Client wrapper for connecting to the local Memgraph instance.
    Memgraph is compatible with the Neo4j bolt protocol and python driver.
    """

    def __init__(self, uri=None, user=None, password=None, database=None):
        settings = get_database_settings()
        self.uri = uri or settings.uri
        self.user = user or settings.user or ""
        self.password = password or settings.password or ""
        self.database = database or settings.database
        self.driver = self.get_driver()

    def get_driver(self):
        # Memgraph defaults to empty strings for auth if not set.
        return GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def execute_query(self, query: str, parameters: dict | None = None) -> list[dict]:
        with self.driver.session(database=self.database) as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]
