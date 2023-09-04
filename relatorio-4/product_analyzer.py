from dataclasses import dataclass
from typing import Any, TypedDict

from database import Database


class SalesByDay(TypedDict):
    _id: str
    total: int


class BestSeller(TypedDict):
    _id: str
    sold: int


class GBId(TypedDict):
    client: int
    day: str


class GreatestBuyer(TypedDict):
    _id: GBId
    bought: int


class SoldMoreThanOnce(TypedDict):
    _id: str
    sold: int


@dataclass
class ProductAnalyzer:
    db: Database

    def sales_by_day(self) -> list[SalesByDay]:
        sbd = self.db.collection.aggregate(
            [
                {"$unwind": "$produtos"},
                {
                    "$group": {
                        "_id": "$data_compra",
                        "total": {"$sum": "$produtos.quantidade"},
                    }
                },
            ]
        )

        return [r for r in sbd]

    def best_seller(self) -> BestSeller:
        bs = self.db.collection.aggregate(
            [
                {"$unwind": "$produtos"},
                {
                    "$group": {
                        "_id": "$produtos.descricao",
                        "sold": {"$sum": "$produtos.quantidade"},
                    },
                },
                {"$sort": {"sold": -1}},
                {"$limit": 1},
            ]
        )

        return next(bs)

    def greatest_buyer(self) -> GreatestBuyer:
        gb = self.db.collection.aggregate(
            [
                {"$unwind": "$produtos"},
                {
                    "$group": {
                        "_id": {"client": "$cliente_id", "day": "$data_compra"},
                        "bought": {
                            "$sum": {
                                "$multiply": ["$produtos.quantidade", "$produtos.preco"]
                            }
                        },
                    }
                },
                {"$sort": {"bought": -1}},
                {"$limit": 1},
            ]
        )

        return next(gb)

    def sold_more_than_once(self) -> list[SoldMoreThanOnce]:
        smto = self.db.collection.aggregate(
            [
                {"$unwind": "$produtos"},
                {
                    "$group": {
                        "_id": "$produtos.descricao",
                        "sold": {
                            "$sum": "$produtos.quantidade",
                        },
                    }
                },
                {"$match": {"sold": {"$gt": 1}}},
            ]
        )

        return [r for r in smto]
