from dataclasses import dataclass

from database import Database
from json_log import json_log


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


def cleanup(obj: dict[str, str]) -> dict[str, str]:
    return {**obj, "_id": str(obj["_id"])}
