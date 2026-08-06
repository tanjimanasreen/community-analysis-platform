from src.config.settings import get_database_settings
import csv

TELEGRAM_QUERY = """MATCH (source:User)-[r:CREATED]->(target:Message) WHERE localdatetime({year:$year, month: $month, day:1}) <= target.date < localdatetime({year:$year_next, month: $month_next, day:1})
    Return source, target, TYPE(r) as relation
    UNION
    MATCH (source:Message)-[r:SENT_TO]->(target:Channel) WHERE localdatetime({year:$year, month: $month, day:1}) <= source.date < localdatetime({year:$year_next, month: $month_next, day:1})
    Return source, target, TYPE(r) as relation
    UNION
    MATCH (source:User)-[r:PRODUCED]->(target:Forward_Message) WHERE localdatetime({year:$year, month: $month, day:1}) <= target.forwarded_date < localdatetime({year:$year_next, month: $month_next, day:1})
    Return source, target, TYPE(r) as relation
    UNION
    MATCH (source:Forward_Message)-[r:FORWARDED_BY]->(target:User) WHERE localdatetime({year:$year, month: $month, day:1}) <= source.forwarded_date < localdatetime({year:$year_next, month: $month_next, day:1})
    Return source, target, TYPE(r) as relation
    UNION
    MATCH (source:Forward_Message)-[r:FORWARDED_TO]->(target:Channel) WHERE localdatetime({year:$year, month: $month, day:1}) <= source.forwarded_date < localdatetime({year:$year_next, month: $month_next, day:1})
    Return source, target, TYPE(r) as relation
    UNION
    MATCH (source:Channel)-[r:ORIGINATED]->(target:Forward_Message) WHERE localdatetime({year:$year, month: $month, day:1}) <= target.forwarded_date < localdatetime({year:$year_next, month: $month_next, day:1})
    Return source, target, TYPE(r) as relation
"""

TWITTER_RETWEET_QUERY = """MATCH (source:Twitter_User)-[r:TWEETED]->(target:Retweet_Quote) WHERE localdatetime({year:$year, month:$month, day:1}) <= target.created_at < localdatetime({year:$year_next, month: $month_next, day: 1})
    Return source, target, TYPE(r) as relation
    UNION
    MATCH (source:Retweet_Quote)-[r:RETWEETED_BY]->(target:Twitter_User) WHERE localdatetime({year:$year, month: $month, day: 1}) <= source.created_at < localdatetime({year:$year_next, month: $month_next, day:1})
    Return source, target, TYPE(r) as relation
"""

TWITTER_REPLY_QUERY = """MATCH (source:Reply)-[r:REPLIED_BY]->(target:Twitter_User) WHERE localdatetime({year:$year, month:$month, day:1}) <= source.created_at < localdatetime({year:$year_next, month: $month_next, day: 1})
    Return source, target, TYPE(r) as relation
    UNION
    MATCH (source:Reply)-[r:REPLIED_TO]->(target:Twitter_User) WHERE localdatetime({year:$year, month: $month, day: 1}) <= source.created_at < localdatetime({year:$year_next, month: $month_next, day:1})
    Return source, target, TYPE(r) as relation
"""

QUERIES = {
    "telegram": TELEGRAM_QUERY,
    "twitter_retweet": TWITTER_RETWEET_QUERY,
    "twitter_reply": TWITTER_REPLY_QUERY,
}


class Neo4jExporter:
    def __init__(self, uri=None, user=None, password=None, database=None):
        settings = get_database_settings()
        self.uri = uri or settings.uri
        self.user = user or settings.user or ""
        self.password = password or settings.password or ""
        self.database = database or settings.database

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
            "month_next": month_next,
        }

        from neo4j import GraphDatabase

        with GraphDatabase.driver(self.uri, auth=(self.user, self.password)) as driver:
            driver.verify_connectivity()
            records, summary, keys = driver.execute_query(
                query, parameters_=params, database_=self.database
            )

            with open(output_file, "w+", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["source", "target", "relation"])

                for record in records:
                    writer.writerow(
                        [
                            record.data()["source"],
                            record.data()["target"],
                            record.data()["relation"],
                        ]
                    )

            return summary
