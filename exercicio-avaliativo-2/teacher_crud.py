from dataclasses import dataclass
from typing import Optional

from database import Database


@dataclass
class TeacherCRUD:
    db: Database

    def create(self, name: str, ano_nasc: int, cpf: str):
        return self.db.write(
            "CREATE(:Teacher{name: $name,ano_nasc: $ano_nasc,cpf: $cpf})",
            name=name,
            ano_nasc=ano_nasc,
            cpf=cpf,
        )

    def read(self, name: Optional[str] = None):
        if name is None:
            return self.db.read("MATCH(t:Teacher) return t")
        return self.db.read("MATCH(t:Teacher{name:$name}) return t", name=name)

    def delete(self, name: str):
        return self.db.write("MATCH(t:Teacher{name:$name}) detach delete t", name=name)

    def update(self, name: str, cpf: str):
        return self.db.write(
            "MATCH(t:Teacher{name:$name}) set t.cpf = $cpf", name=name, cpf=cpf
        )
