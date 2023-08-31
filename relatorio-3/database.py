import pymongo  # pip install pymongo
from pymongo import MongoClient
from pymongo.database import Database as MongoDatabase
from pymongo.collection import Collection

# from dataset.pokemon_dataset import dataset


class Database:
    cluster_connection: MongoClient
    database: MongoDatabase
    collection: Collection

    def __init__(self, host: str, database: str, collection: str):
        self.connect(host, database, collection)

    def connect(self, host: str, database: str, collection: str):
        self.cluster_connection = MongoClient(host, tlsAllowInvalidCertificates=True)
        self.db = self.cluster_connection[database]
        self.collection = self.db[collection]

    def reset_database(self, dataset: list[dict]):
        self.db.drop_collection(self.collection)
        self.collection.insert_many(dataset)
