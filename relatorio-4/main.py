import json

from rich import print

from database import Database
from product_analyzer import ProductAnalyzer

HOST = "192.168.122.94:27017"


def main() -> None:
    db = Database(HOST, "mercado", "produtos")
    with open("dataset.json") as f:
        db.reset_database(json.load(f))

    pa = ProductAnalyzer(db)

    sales_by_day = pa.sales_by_day()
    print(f"{sales_by_day=}")

    best_seller = pa.best_seller()
    print(f"{best_seller=}")

    greatest_buyer = pa.greatest_buyer()
    print(f"{greatest_buyer=}")

    sold_more_than_once = pa.sold_more_than_once()
    print(f"{sold_more_than_once=}")


if __name__ == "__main__":
    main()
