from dataclasses import dataclass

import pymongo.errors as mongo_errors
from rich import print

from database import Database
from cli import CliBase

HOST = "192.168.122.94:27017"


@dataclass
class Books:
    db: Database

    def create(self, title: str, author: str, year: int, price: float) -> str:
        res = self.db.collection.insert_one(
            {"titulo": title, "autor": author, "ano": year, "preco": price}
        )

        return res.inserted_id


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


def main() -> None:
    db = Database(HOST, "relatorio-5", "people")
    books = Books(db)

    cli = Cli(books)
    cli.run()
    # id = books.create("Testing", "Testing", 2001, 3.14)
    # print(id)


if __name__ == "__main__":
    main()
