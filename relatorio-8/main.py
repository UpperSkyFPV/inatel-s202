from typing import Any, TypedDict

from neo4j import GraphDatabase, ManagedTransaction
from rich import print
from rich.progress import track


class Db:
    def __init__(self, uri: str, user: str, password: str) -> None:
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self.driver.close()

    def initialize(self, query: str) -> None:
        queries = [q.strip() for q in query.split("\n\n") if q != ""]
        # print(queries)

        with self.driver.session() as s:
            r = s.execute_write(lambda tx: tx.run("match (n) detach delete n"))
            print(r)

            for q in track(queries):
                r = s.execute_write(lambda tx: tx.run(q))  # type: ignore
                print(r)

    def create_player(self, uid: str, name: str) -> str:
        with self.driver.session() as s:
            r = s.execute_write(
                lambda tx: tx.run(
                    "CREATE(:Player{name:$name,uid:$uid})", name=name, uid=uid
                )
            )
            print(r)

        return uid

    def update_player_by_uid(self, uid: str, name: str) -> str:
        with self.driver.session() as s:
            r = s.execute_write(
                lambda tx: tx.run(
                    """\
                    MATCH(p:Player{uid:$uid})
                    SET p.name = $name
                    """,
                    uid=uid,
                    name=name,
                )
            )
            print(r)

        return uid

    def delete_player_by_uid(self, uid: str) -> str:
        with self.driver.session() as s:
            r = s.execute_write(
                lambda tx: tx.run(
                    """\
                    MATCH(p:Player{uid:$uid})
                    DETACH DELETE p
                    """,
                    uid=uid,
                )
            )
            print(r)

        return uid

    def create_match(self, uid: str, result: Any) -> str:
        with self.driver.session() as s:
            r = s.execute_write(
                lambda tx: tx.run(
                    "CREATE(:Match{uid:$uid,result:$result})", uid=uid, result=result
                )
            )
            print(r)

        return uid

    def update_match_by_uid(self, uid: str, result: Any) -> str:
        with self.driver.session() as s:
            r = s.execute_write(
                lambda tx: tx.run(
                    """\
                    MATCH(p:Match{uid:$uid})
                    SET p.result = $result
                    """,
                    uid=uid,
                    result=result,
                )
            )
            print(r)

        return uid

    def delete_match_by_uid(self, uid: str) -> str:
        with self.driver.session() as s:
            r = s.execute_write(
                lambda tx: tx.run(
                    """\
                    MATCH(p:Match{uid:$uid})
                    DETACH DELETE p
                    """,
                    uid=uid,
                )
            )
            print(r)

        return uid

    def set_played_at(self, puid: str, muid: str) -> None:
        with self.driver.session() as s:
            r = s.execute_write(
                lambda tx: tx.run(
                    """\
                    MATCH(m:Match{uid:$muid}),(p:Player{uid:$puid})\
                    CREATE(p) -[:PLAYED_AT]-> (m)\
                    """,
                    muid=muid,
                    puid=puid,
                )
            )
            print(r)

    def players(self) -> list:
        def reader(tx: ManagedTransaction):
            r = tx.run(
                """\
                    MATCH(p:Player)\
                    return p
                    """,
            )

            return list(r)

        with self.driver.session() as s:
            return s.execute_read(reader)

    def players_at(self, muid: str) -> list:
        def reader(tx: ManagedTransaction):
            r = tx.run(
                """\
                    MATCH(p:Player) -[r:PLAYED_AT]-> (m:Match{uid:$muid})\
                    return m, p
                    """,
                muid=muid,
            )

            return list(r)

        with self.driver.session() as s:
            return s.execute_read(reader)

    def matches_played(self, puid: str) -> list:
        def reader(tx: ManagedTransaction):
            r = tx.run(
                """\
                    MATCH(p:Player{uid:$puid}) -[r:PLAYED_AT]-> (m:Match)\
                    return m, p
                    """,
                puid=puid,
            )

            return list(r)

        with self.driver.session() as s:
            return s.execute_read(reader)


def main() -> None:
    with open(".secret") as f:
        password = f.read().strip()

    db = Db("neo4j+s://54129c6f.databases.neo4j.io:7687", "neo4j", password)
    db.initialize("")

    p1 = db.create_player("902q3pjfocq3iwew8i", "jogador1")
    p2 = db.create_player("16asd1c6a5sd1c6asd", "jogador2")
    p3 = db.create_player("5a4scASD4Cs5ad4cas", "jogador3")
    p4 = db.create_player("asd5csa4d5cas4dC5a", "jogador4")
    m1 = db.create_match("6as5cd1as6d51c6sas", [7, 1])
    m2 = db.create_match("ac66sdc5asd4Casd4a", [3, 2])
    m3 = db.create_match("la9sdca9s8d7asd6a6", [1, 1])
    m4 = db.create_match("546asdcasd45asd4aw", [2, 1])

    db.set_played_at(p1, m1)
    db.set_played_at(p2, m1)
    db.set_played_at(p3, m1)

    db.set_played_at(p3, m2)
    db.set_played_at(p4, m2)

    db.set_played_at(p2, m3)
    db.set_played_at(p3, m3)

    db.set_played_at(p1, m4)
    db.set_played_at(p2, m4)
    db.set_played_at(p3, m4)
    db.set_played_at(p4, m4)

    db.delete_player_by_uid(p4)

    db.update_match_by_uid(m3, [4, 3])

    p = db.players()
    print(p)

    pa = db.players_at("ac66sdc5asd4Casd4a")
    print(pa)

    mp = db.matches_played("16asd1c6a5sd1c6asd")
    print(mp)


if __name__ == "__main__":
    main()
