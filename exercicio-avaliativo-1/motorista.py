from dataclasses import dataclass
from typing import Any

from bson.objectid import ObjectId
from database import Database


@dataclass
class Passageiro:
    nome: str
    documento: str

    def to_json(self) -> dict:
        return {"nome": self.nome, "documento": self.documento}


@dataclass
class Corrida:
    nota: int
    distancia: float
    valor: float
    passageiro: Passageiro

    def to_json(self) -> dict:
        return {
            "nota": self.nota,
            "distancia": self.distancia,
            "valor": self.valor,
            "passageiro": self.passageiro.to_json(),
        }


@dataclass
class Motorista:
    corridas: list[Corrida]
    nota: int

    def to_json(self) -> dict:
        return {"nota": self.nota, "corridas": [c.to_json() for c in self.corridas]}


@dataclass
class MotoristaDAO:
    db: Database

    def create(self, corridas: list[Corrida], nota: int) -> ObjectId:
        res = self.db.collection.insert_one(Motorista(corridas, nota).to_json())

        return res.inserted_id

    def read(self, id: str | ObjectId) -> Motorista | None:
        return self.db.collection.find_one({"_id": ObjectId(id)})

    def update(
        self, id: str | ObjectId, corridas: list[Corrida] | None, nota: int | None
    ) -> ObjectId:
        obj = {
            k: v
            for k, v in {"corridas": corridas, "nota": nota}.items()
            if v is not None
        }

        res = self.db.collection.update_one({"_id": ObjectId(id)}, {"$set": obj})

        return res.upserted_id

    def delete(self, id: str | ObjectId) -> bool:
        res = self.db.collection.delete_one({"_id": ObjectId(id)})

        return res.acknowledged

    def find(
        self, filter: dict[str, Any] = {}, projection: dict[str, Any] = {}
    ) -> list[Motorista]:
        return list(self.db.collection.find(filter, projection))
