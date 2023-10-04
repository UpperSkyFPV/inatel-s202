from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database as MongoDatabase
from pymongo.server_api import ServerApi


class Database:
    cluster_connection: MongoClient
    database: MongoDatabase
    collection: Collection

    def __init__(self, host: str, database: str, collection: str):
        self.connect(host, database, collection)

    def connect(self, host: str, database: str, collection: str):
        self.cluster_connection = MongoClient(
            host, tlsAllowInvalidCertificates=True, server_api=ServerApi("1")
        )
        self.db = self.cluster_connection[database]
        self.collection = self.db[collection]

    def reset_database(self, dataset: list[dict]):
        self.db.drop_collection(self.collection)
        self.collection.insert_many(dataset)
