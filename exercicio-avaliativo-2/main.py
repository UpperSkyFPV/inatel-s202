from typing import Optional
from rich import print

from cli import CliBase
from database import Database
from teacher_crud import TeacherCRUD


class Cli(CliBase):
    teachers: TeacherCRUD

    def __init__(self, teacher_crud: TeacherCRUD) -> None:
        super().__init__()
        self.teachers = teacher_crud

    def cmd_create(self, name: str, ano_nasc: int, cpf: str):
        """Create a new teacher."""
        try:
            return self.teachers.create(name, ano_nasc, cpf)
        except Exception as e:
            # NOTE: ^ Not the best exception handling
            print(e)

    def cmd_read(self, name: Optional[str] = None):
        """Get a teacher by name"""

        try:
            return self.teachers.read(name)
        except Exception as e:
            print(e)

    def cmd_delete(self, name: str):
        """Delete a teacher using their name"""

        try:
            return self.teachers.delete(name)
        except Exception as e:
            print(e)

    def cmd_update(self, name: str, cpf: str):
        """Update the CPF of a teacher using their name"""

        try:
            return self.teachers.update(name, cpf)
        except Exception as e:
            print(e)


def main() -> None:
    with open(".secret") as f:
        password = f.read().strip()

    db = Database("neo4j+s://54129c6f.databases.neo4j.io:7687", "neo4j", password)
    crud = TeacherCRUD(db)

    # 4.b
    crud.create(name="Chris Lima", ano_nasc=1956, cpf="189.052.396-66")

    # 4.c
    t = crud.read("Chris Lima")
    print(t)

    # 4.d
    crud.update("Chris Lima", "162.052.777-77")

    # 4.e
    cli = Cli(crud)
    cli.run()


if __name__ == "__main__":
    main()
