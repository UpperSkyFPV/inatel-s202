import pymongo.errors as mongo_errors
from rich import print

from cli import CliBase
from database import Database
from motorista import Corrida, MotoristaDAO, Passageiro


HOST = "mongodb+srv://uppr:{password}@cluster0.xjctoyg.mongodb.net/?retryWrites=true&w=majority"


class MotoristaCLI(CliBase):
    mdao: MotoristaDAO

    def __init__(self, mdao: MotoristaDAO) -> None:
        super().__init__()
        self.mdao = mdao

    def cmd_create(self, nota: int, corridas: str | list[Corrida]):
        """Cria um novo motorista com suas corridas. É importante notas que
        `corridas` é uma lista. Para usar o modo interativo, passe `*` para o
        argumento corridas."""

        c = []
        if isinstance(corridas, str):
            i = 0
            while True:
                try:
                    cnota = int(input(f"[{i}] nota> "))
                    cdist = float(input(f"[{i}] distancia> "))
                    cvalor = float(input(f"[{i}] valor> "))

                    print(f"[{i}] passageiro: ")
                    cpnome = input(f"    passageiro.nome> ")
                    cpdoc = input(f"    passageiro.documento> ")

                    c.append(Corrida(cnota, cdist, cvalor, Passageiro(cpnome, cpdoc)))

                    i += 1
                except EOFError:
                    print()
                    break
                except ValueError as e:
                    print(f"Invalid value for field: {e}")
        else:
            c = corridas

        try:
            return self.mdao.create(c, nota)
        except mongo_errors.WriteError as e:
            print(e)

    def cmd_view(self):
        """Visualizar todos os motoristas salvos"""
        return self.mdao.find()


def main() -> None:
    with open(".secret") as f:
        password = f.read().strip()

    host = HOST.format(password=password)
    db = Database(host, "atlas-cluster", "Motoristas")
    mdao = MotoristaDAO(db)

    cli = MotoristaCLI(mdao)
    cli.run()


if __name__ == "__main__":
    main()
