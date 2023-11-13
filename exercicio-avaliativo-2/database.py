from typing import Callable, LiteralString, TypeVar
from neo4j import Driver, GraphDatabase, ManagedTransaction

T = TypeVar("T")


class Database:
    driver: Driver

    def __init__(self, uri: str, user: str, password: str) -> None:
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self.driver.close()

    def read(self, query: LiteralString, *args, **kwargs):
        return self.exec_read(lambda tx: list(tx.run(query, *args, **kwargs)))

    def write(self, query: LiteralString, *args, **kwargs):
        return self.exec_write(lambda tx: list(tx.run(query, *args, **kwargs)))

    def reset(self) -> None:
        self.write("match (n) detach delete n")

    def exec_read(self, fn: Callable[[ManagedTransaction], T]) -> T:
        with self.driver.session() as s:
            return s.execute_read(fn)

    def exec_write(self, fn: Callable[[ManagedTransaction], T]) -> T:
        with self.driver.session() as s:
            return s.execute_write(fn)
