from rich.progress import track
from database import Database
from rich import print

DO_RESET = False


def run() -> None:
    with open(".secret") as f:
        password = f.read().strip()

    with open("data.txt") as f:
        initial_data = f.read().strip()

    db = Database("neo4j+s://54129c6f.databases.neo4j.io:7687", "neo4j", password)
    if DO_RESET:
        db.reset()
        for stmt in track(initial_data.split(";")):
            db.write(stmt.strip())  # type:ignore

    # 1.a Busque pelo professor “Teacher” cujo nome seja “Renzo”, retorne o ano_nasc e o CPF.
    r = db.read("match(t:Teacher{name: $name}) return t.ano_nasc, t.cpf", name="Renzo")
    print(r)

    # 1.b Busque pelos professores “Teacher” cujo nome comece com a letra “M”, retorne o name e o cpf.
    r = db.read("match (t:Teacher) where left(t.name, 1) = 'M' return t.name, t.cpf")
    print(r)

    # 1.c Busque pelos nomes de todas as cidades `“City”` e retorne-os.
    r = db.read("match (c:City) return c")
    print(r)

    # 1.d Busque pelas escolas “School”, onde o number seja maior ou igual a 150 e
    # menor ou igual a 550, retorne o nome da escola, o endereço e o número.
    r = db.read(
        "match (s:School) where s.number >= 150 or s.number <= 550 return s.name, s.address, s.number"
    )
    print(r)

    # 2.a Encontre o ano de nascimento do professor mais jovem e do professor mais velho.
    r = db.read("match (t:Teacher) return min(t.ano_nasc), max(t.ano_nasc)")
    print(r)

    # 2.b Encontre a média aritmética para os habitantes de todas as cidades, use
    # a propriedade “population”.
    r = db.read("match (c:City) return avg(c.population)")
    print(r)

    # 2.c Encontre a cidade cujo CEP seja igual a “37540-000” e retorne o nome
    # com todas as letras “a” substituídas por “A” .
    r = db.read(
        "match (c:City{cep: $cep}) return replace(c.name, 'a', 'A')", cep="37540-000"
    )
    print(r)

    # 2.d Para todos os professores, retorne um caractere, iniciando a partir da
    # 3ª letra do nome.
    r = db.read("match (t:Teacher) return substring(t.name, 3, 1)")
    print(r)


if __name__ == "__main__":
    run()
