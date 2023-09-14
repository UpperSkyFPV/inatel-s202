from dataclasses import dataclass
from typing import Any, TypedDict

from bson.objectid import ObjectId
import pymongo.errors as mongo_errors
from rich import print

from database import Database
from cli import CliBase

HOST = "192.168.122.94:27017"


class Book(TypedDict):
    titulo: str
    autor: str
    year: int
    preco: float


@dataclass
class Books:
    db: Database

    def create(self, title: str, author: str, year: int, price: float) -> ObjectId:
        res = self.db.collection.insert_one(
            {"titulo": title, "autor": author, "ano": year, "preco": price}
        )

        return res.inserted_id

    def read(self, id: str | ObjectId) -> Book | None:
        return self.db.collection.find_one({"_id": ObjectId(id)})

    def update(
        self,
        id: str | ObjectId,
        title: str | None = None,
        author: str | None = None,
        year: int | None = None,
        price: float | None = None,
    ) -> ObjectId:
        obj = {
            k: v
            for k, v in {
                "titulo": title,
                "autor": author,
                "ano": year,
                "preco": price,
            }.items()
            if v is not None
        }

        r = self.db.collection.update_one({"_id": ObjectId(id)}, {"$set": obj})
        return r.upserted_id

    def delete(self, id: str | ObjectId) -> bool:
        r = self.db.collection.delete_one({"_id": ObjectId(id)})
        return r.acknowledged

    def find(self, filter: dict[str, Any] = {}) -> list[Book]:
        return list(self.db.collection.find(filter))


class Cli(CliBase):
    books: Books

    def __init__(self, books: Books) -> None:
        super().__init__()
        self.books = books

    def cmd_create_book(self, title: str, author: str, year: int, price: float):
        """Create a new book and add it to the collection. Returns the `id` of the item just added, such `id` is used by the other CRUD operations"""
        try:
            return self.books.create(title, author, year, price)
        except mongo_errors.WriteError as e:
            print(e)

    def cmd_update_book(
        self,
        id: str | ObjectId,
        title: str | None = None,
        author: str | None = None,
        year: int | None = None,
        price: float | None = None,
    ):
        """Update the value of book. Fields that are not provided are not touched"""
        try:
            return self.books.update(id, title, author, year, price)
        except mongo_errors.WriteError as e:
            print(e)

    def cmd_read_book(self, id: str | ObjectId):
        """Read the value of a book using it's `_id`"""
        try:
            return self.books.read(id)
        except mongo_errors.WriteError as e:
            print(e)

    def cmd_delete_book(self, id: str | ObjectId):
        """Delete a book by it's `_id`. Returns if it was successfully deleted."""
        try:
            return self.books.delete(id)
        except mongo_errors.WriteError as e:
            print(e)

    def cmd_find_books(self, filter: dict[str, Any] = {}):
        """List all books in the database. A custom mongodb compliant filter can be given"""
        try:
            return self.books.find(filter)
        except mongo_errors.WriteError as e:
            print(e)


def main() -> None:
    db = Database(HOST, "relatorio-5", "Livros")
    books = Books(db)

    cli = Cli(books)
    cli.run()
    # id = books.create("Testing", "Testing", 2001, 3.14)
    # print(id)


if __name__ == "__main__":
    main()
