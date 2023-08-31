from dataclasses import dataclass
import json
import os
from typing import Any

from rich import print
from database import Database

HOST = "192.168.122.94:27017"


@dataclass
class Pokedex:
    db: Database

    def one_by_name(self, name: str) -> dict[str, str] | None:
        result = self.db.collection.find_one({"name": name})
        if result is None:
            return None
        result = {**result, "_id": str(result["_id"])}

        json_log("one_by_name", {"name": name, "result": result})
        return result

    def of_types(self, ty: list[str]) -> list[dict[str, str]]:
        result = [
            {**r, "_id": str(r["_id"])}
            for r in self.db.collection.find({"type": {"$in": ty}})
        ]
        json_log("of_types", {"ty": ty, "result": result})
        return result

    def with_weeknesses(self, weeknesses: list[str]) -> list[dict[str, str]]:
        result = [
            cleanup(r)
            for r in self.db.collection.find({"weaknesses": {"$in": weeknesses}})
        ]
        json_log("with_weeknesses", {"weaknesses": weeknesses, "result": result})
        return result

    def with_spawns_in_range(self, min: float, max: float) -> list[dict[str, str]]:
        result = [
            cleanup(r)
            for r in self.db.collection.find({"avg_spawns": {"$lt": max, "$gt": min}})
        ]
        json_log("with_spawns_in_range", {"min": min, "max": max, "result": result})
        return result

    def with_candy_in_range(self, min: int, max: int) -> list[dict[str, str]]:
        result = [
            cleanup(r)
            for r in self.db.collection.find({"candy_count": {"$lt": max, "$gt": min}})
        ]
        json_log("with_candy_in_range", {"min": min, "max": max, "result": result})
        return result


def main() -> None:
    db = Database(HOST, database="pokedex", collection="pokemons")
    print(f"{db=}")

    # with open("dataset.json") as f:
    #     db.reset_database(json.load(f))

    pokedex = Pokedex(db)
    print(f"{pokedex=}")

    pokedex.one_by_name("Raticate")
    pokedex.of_types(["Normal"])
    pokedex.with_weeknesses(["Fighting", "Grass"])
    pokedex.with_spawns_in_range(0.5, 0.3)
    pokedex.with_candy_in_range(50, 100)

    print("DONE")


def json_log(name: str, data: Any, logdir="./json") -> None:
    if not os.path.exists(logdir):
        os.makedirs(logdir)

    with open(os.path.join(logdir, f"{name}.json"), "w") as f:
        json.dump(data, f, indent=4, separators=(",", ":"))


def cleanup(obj: dict[str, str]) -> dict[str, str]:
    return {**obj, "_id": str(obj["_id"])}


if __name__ == "__main__":
    main()
