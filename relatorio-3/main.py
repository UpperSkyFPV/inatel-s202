import json

from rich import print

from database import Database
from pokedex import Pokedex

HOST = "192.168.122.94:27017"


def main() -> None:
    db = Database(HOST, database="pokedex", collection="pokemons")
    print(f"{db=}")

    with open("dataset.json") as f:
        db.reset_database(json.load(f))

    pokedex = Pokedex(db)
    print(f"{pokedex=}")

    pokedex.one_by_name("Raticate")
    pokedex.of_types(["Normal"])
    pokedex.with_weeknesses(["Fighting", "Grass"])
    pokedex.with_spawns_in_range(0.5, 0.3)
    pokedex.with_candy_in_range(50, 100)

    print("DONE")


if __name__ == "__main__":
    main()
