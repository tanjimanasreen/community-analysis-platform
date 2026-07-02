import os
import csv

TELEGRAM_QUERY = """MATCH (source:User)-[r:CREATED]->(target:Message) WHERE datetime({year:$year, month: $month, day:1}) <= target.date < datetime({year:$year_next, month: $month_next, day:1})
    Return source, target, TYPE(r) as relation 
    UNION
    MATCH (source:Message)-[r:SENT_TO]->(target:Channel) WHERE datetime({year:$year, month: $month, day:1}) <= source.date < datetime({year:$year_next, month: $month_next, day:1})
    Return source, target, TYPE(r) as relation
    UNION
    MATCH (source:User)-[r:PRODUCED]->(target:Forward_Message) WHERE datetime({year:$year, month: $month, day:1}) <= target.forwarded_date < datetime({year:$year_next, month: $month_next, day:1}) 
    Return source, target, TYPE(r) as relation
    UNION
    MATCH (source:Forward_Message)-[r:FORWARDED_BY]->(target:User) WHERE datetime({year:$year, month: $month, day:1}) <= source.forwarded_date < datetime({year:$year_next, month: $month_next, day:1}) 
    Return source, target, TYPE(r) as relation
    UNION
    MATCH (source:Forward_Message)-[r:FORWARDED_TO]->(target:Channel) WHERE datetime({year:$year, month: $month, day:1}) <= source.forwarded_date < datetime({year:$year_next, month: $month_next, day:1}) 
    Return source, target, TYPE(r) as relation
    UNION
    MATCH (source:Channel)-[r:ORIGINATED]->(target:Forward_Message) WHERE datetime({year:$year, month: $month, day:1}) <= target.forwarded_date < datetime({year:$year_next, month: $month_next, day:1}) 
    Return source, target, TYPE(r) as relation
"""

TWITTER_RETWEET_QUERY = """MATCH (source:Twitter_User)-[r:TWEETED]->(target:Retweet_Quote) WHERE datetime({year:$year, month:$month, day:1}) <= target.created_at < datetime({year:$year_next, month: $month_next, day: 1})
    Return source, target, TYPE(r) as relation
    UNION
    MATCH (source:Retweet_Quote)-[r:RETWEETED_BY]->(target:Twitter_User) WHERE datetime({year:$year, month: $month, day: 1}) <= source.created_at < datetime({year:$year_next, month: $month_next, day:1})
    Return source, target, TYPE(r) as relation
"""

TWITTER_REPLY_QUERY = """MATCH (source:Reply)-[r:REPLIED_BY]->(target:Twitter_User) WHERE datetime({year:$year, month:$month, day:1}) <= source.created_at < datetime({year:$year_next, month: $month_next, day: 1})
    Return source, target, TYPE(r) as relation
    UNION
    MATCH (source:Reply)-[r:REPLIED_TO]->(target:Twitter_User) WHERE datetime({year:$year, month: $month, day: 1}) <= source.created_at < datetime({year:$year_next, month: $month_next, day:1})
    Return source, target, TYPE(r) as relation
"""

QUERIES = {
    'telegram': TELEGRAM_QUERY,
    'twitter_retweet': TWITTER_RETWEET_QUERY,
    'twitter_reply': TWITTER_REPLY_QUERY
}

class Neo4jExporter:
    def __init__(self, uri=None, user=None, password=None, database="neo4j"):
        self.uri = uri or os.environ.get("NEO4J_URI")
        self.user = user or os.environ.get("NEO4J_USER")
        self.password = password or os.environ.get("NEO4J_PASSWORD")
        self.database = database or os.environ.get("NEO4J_DATABASE", "neo4j")

    def get_query(self, query_name):
        if query_name not in QUERIES:
            raise ValueError(f"Unknown query name: {query_name}")
        return QUERIES[query_name]

    def export(self, query_name, year, month, output_file):
        query = self.get_query(query_name)
        
        month = int(month)
        year = int(year)
        month_next = month + 1
        year_next = year
        if month_next > 12:
            month_next = 1
            year_next += 1

        params = {
            "year": year,
            "month": month,
            "year_next": year_next,
            "month_next": month_next
        }

        from neo4j import GraphDatabase

        with GraphDatabase.driver(self.uri, auth=(self.user, self.password)) as driver:
            driver.verify_connectivity()
            records, summary, keys = driver.execute_query(
                query,
                parameters_=params,
                database_=self.database
            )
        
            with open(output_file, 'w+', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['source', 'target', 'relation'])
                
                for record in records:
                    writer.writerow([record.data()['source'], record.data()['target'], record.data()['relation']])
            
            return summary
