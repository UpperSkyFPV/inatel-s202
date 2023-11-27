from dataclasses import dataclass
from typing import Callable, Optional, TypeVar

from neo4j import Driver, GraphDatabase, ManagedTransaction

from models import FullPost, Post, User

T = TypeVar("T")

DELETED_USER = User("`deleted`")


@dataclass
class Database:
    driver: Driver

    @staticmethod
    def connect(uri: str, user: str, password: str) -> "Database":
        d = GraphDatabase.driver(uri, auth=(user, password))

        return Database(d)

    def reset(self):
        with self.driver.session() as s:
            return s.execute_write(lambda tx: tx.run("match(n) detach delete(n)"))

    def write_session(self, cb: Callable[[ManagedTransaction], T]) -> T:
        with self.driver.session() as s:
            return s.execute_write(lambda tx: cb(tx))

    def read_session(self, cb: Callable[[ManagedTransaction], T]) -> T:
        with self.driver.session() as s:
            return s.execute_read(lambda tx: cb(tx))

    def create_user(self, user: User) -> User:
        def cb(tx: ManagedTransaction) -> User:
            if self.get_user_by_name_tx(tx, user.name) is not None:
                raise RuntimeError(f"duplicate name: {user.name}")

            return self.create_user_tx(tx, user)

        return self.write_session(cb)

    def delete_user(self, user: User) -> None:
        return self.write_session(lambda tx: self.delete_user_tx(tx, user))

    def update_user(self, user: User) -> None:
        """Overwrites current values"""
        return self.write_session(lambda tx: self.update_user_tx(tx, user))

    def get_user_by_id(self, userid: str) -> Optional[User]:
        return self.read_session(lambda tx: self.get_user_by_id_tx(tx, userid))

    def get_user_by_name(self, name: str) -> Optional[User]:
        return self.read_session(lambda tx: self.get_user_by_name_tx(tx, name))

    def get_users(self) -> list[User]:
        return self.read_session(lambda tx: self.get_users_tx(tx))

    def get_post_by_id(self, postid: str) -> Optional[FullPost]:
        return self.read_session(lambda tx: self.get_post_by_id_tx(tx, postid))

    def get_posts_of(self, user: User) -> list[FullPost]:
        return self.read_session(lambda tx: self.get_posts_of_tx(tx, user))

    def get_posts(self) -> list[FullPost]:
        return self.read_session(lambda tx: self.get_posts_tx(tx))

    def get_liked_by(self, user: User) -> list[FullPost]:
        if user.id == "":
            raise RuntimeError(f"id for user {user} was not filled")

        def cb(tx: ManagedTransaction) -> list[FullPost]:
            r = tx.run(
                """match(u:User)-[:LIKED]->(p:Post)
                    where elementid(u) = $userid
                    return elementid(p), p.title, p.contents, count(u)
                """,
                userid=user.id,
            )

            # TODO: see TODO below
            raise RuntimeError("programmer was lazy")

            return [
                FullPost(
                    author=user,
                    title=item.value("p.title"),
                    contents=item.value("p.contents"),
                    # TODO: Fix this, right now it will fail
                    likes=item.value("count(u)"),
                    id=item.value("elementid(p)"),
                )
                for item in r
            ]

        return self.read_session(cb)

    def get_likes(self, post: Post) -> list[User]:
        if post.id == "":
            raise RuntimeError(f"id for post {post} was not filled")

        def cb(tx: ManagedTransaction) -> list[User]:
            r = tx.run(
                """match(u:User)-[:LIKED]->(p:Post)
                    where elementid(p) = $postid
                    return elementid(u), u.name
                """,
                postid=post.id,
            )

            return [
                User(
                    name=item.value("u.name"),
                    id=item.value("elementid(u)"),
                )
                for item in r
            ]

        return self.read_session(cb)

    def get_followers(self, user: User) -> list[User]:
        if user.id == "":
            raise RuntimeError(f"id for user {user} was not filled")

        def cb(tx: ManagedTransaction) -> list[User]:
            r = tx.run(
                """match(u:User)-[:FOLLOWS]->(o:User)
                    where elementid(o) = $userid
                    return elementid(u), u.name
                """,
                userid=user.id,
            )

            return [User(name=u.get("u.name"), id=u.get("elementid(u)")) for u in r]

        return self.read_session(cb)

    def get_follows(self, user: User) -> list[User]:
        if user.id == "":
            raise RuntimeError(f"id for user {user} was not filled")

        def cb(tx: ManagedTransaction) -> list[User]:
            r = tx.run(
                """match(u:User)-[:FOLLOWS]->(o:User)
                    where elementid(u) = $userid
                    return elementid(o), o.name
                """,
                userid=user.id,
            )

            return [User(name=u.get("o.name"), id=u.get("elementid(o)")) for u in r]

        return self.read_session(cb)

    def create_post(self, user: User, post: Post) -> Post:
        return self.write_session(lambda tx: self.create_post_tx(tx, user, post))

    def delete_post(self, post: Post) -> None:
        return self.write_session(lambda tx: self.delete_post_tx(tx, post))

    def update_post(self, post: Post) -> None:
        """Overwrites current values"""
        return self.write_session(lambda tx: self.update_post_tx(tx, post))

    def add_like(self, user: User, post: Post) -> None:
        return self.write_session(lambda tx: self.add_like_tx(tx, user, post))

    def add_follow(self, user: User, other: User) -> None:
        return self.write_session(lambda tx: self.add_follow_tx(tx, user, other))

    def create_user_tx(self, tx: ManagedTransaction, user: User) -> User:
        r = tx.run(
            "create(u:User{name: $name}) return elementid(u)", name=user.name
        ).single()
        assert r is not None

        _, v = r.items("elementid(u)")[0]
        assert isinstance(v, str)

        return User(user.name, v)

    def delete_user_tx(self, tx: ManagedTransaction, user: User) -> None:
        tx.run(
            "match(u:User) where elementid(u) = $userid detach delete u", userid=user.id
        )

    def update_user_tx(self, tx: ManagedTransaction, user: User) -> None:
        tx.run(
            "match(u:User) where elementid(u) = $userid set u.name=$name",
            userid=user.id,
            name=user.name,
        )

    def get_user_by_id_tx(self, tx: ManagedTransaction, userid: str) -> Optional[User]:
        r = tx.run(
            "match(u:User) where elementid(u) = $userid return u.name", userid=userid
        )
        r = r.single()
        if r is None:
            return None

        return User(r.get("u.name"), userid)

    def get_user_by_name_tx(self, tx: ManagedTransaction, name: str) -> Optional[User]:
        r = tx.run("match(u:User{name: $name}) return elementid(u)", name=name)
        r = r.single()
        if r is None:
            return None

        return User(name, r.get("elementid(u)"))

    def get_users_tx(self, tx: ManagedTransaction) -> list[User]:
        r = tx.run("match(u:User) return elementid(u), u.name")

        return [User(i.get("u.name"), i.get("elementid(u)")) for i in r]

    def create_post_tx(self, tx: ManagedTransaction, user: User, post: Post) -> Post:
        if user.id == "":
            raise RuntimeError(f"id for user {user} was not filled")

        r = tx.run(
            """match(u:User) where elementid(u) = $userid
                create(p:Post{title: $title, contents: $contents})-[:CREATED_BY]->(u)
                return elementid(p)
            """,
            userid=user.id,
            title=post.title,
            contents=post.contents,
        ).single()
        assert r is not None

        _, v = r.items("elementid(p)")[0]
        assert isinstance(v, str)

        return Post(post.title, post.contents, v)

    def get_post_by_id_tx(
        self, tx: ManagedTransaction, postid: str
    ) -> Optional[FullPost]:
        r = tx.run(
            """match(p:Post)
                optional match(p)-[:CREATED_BY]->(u:User)
                optional match(uu:User)-[:LIKED]->(p)
                    where elementid(p) = $postid
                    return p.title, p.contents, elementid(p), u.name, elementid(u), collect(elementid(uu)) as likes
            """,
            postid=postid,
        )
        r = r.single()
        if r is None:
            return None

        userid = r.get("elementid(u)")
        author = (
            DELETED_USER
            if userid is None
            else User(r.get("u.name"), r.get("elementid(u)"))
        )

        return FullPost(
            title=r.get("p.title"),
            contents=r.get("p.contents"),
            author=author,
            likes=r.get("likes"),
            id=r.get("elementid(p)"),
        )

    def get_posts_of_tx(self, tx: ManagedTransaction, user: User) -> list[FullPost]:
        r = tx.run(
            """match(p:Post)-[:CREATED_BY]->(u:User)
                optional match(uu:User)-[:LIKED]->(p)
                    where elementid(u) = $userid
                    return p.title, p.contents, elementid(p), u.name, elementid(u), collect(elementid(uu)) as likes
            """,
            userid=user.id,
        )

        return [
            FullPost(
                title=i.get("p.title"),
                contents=i.get("p.contents"),
                author=User(i.get("u.name"), i.get("elementid(u)")),
                likes=i.get("likes"),
                id=i.get("elementid(p)"),
            )
            for i in r
        ]

    def get_posts_tx(self, tx: ManagedTransaction) -> list[FullPost]:
        r = tx.run(
            """match(p:Post)
                optional match(p)-[:CREATED_BY]->(u:User)
                optional match(uu:User)-[:LIKED]->(p)
                    return p.title, p.contents, elementid(p), u.name, elementid(u), collect(elementid(uu)) as likes
            """
        )

        return [
            FullPost(
                title=i.get("p.title"),
                contents=i.get("p.contents"),
                author=(
                    User(i.get("u.name"), i.get("elementid(u)"))
                    if i.get("elementid(u)") is not None
                    else DELETED_USER
                ),
                likes=i.get("likes"),
                id=i.get("elementid(p)"),
            )
            for i in r
        ]

    def delete_post_tx(self, tx: ManagedTransaction, post: Post) -> None:
        tx.run(
            "match(p:Post) where elementid(p) = $postid detach delete p", postid=post.id
        )

    def update_post_tx(self, tx: ManagedTransaction, post: Post) -> None:
        tx.run(
            "match(p:Post) where elementid(p) = $postid set p.title=$title, p.contents=$contents",
            postid=post.id,
            title=post.title,
            contents=post.contents,
        )

    def add_like_tx(self, tx: ManagedTransaction, user: User, post: Post) -> None:
        if user.id == "" or post.id == "":
            raise RuntimeError(f"id for user {user} or for post {post} was not filled")

        tx.run(
            """match(u:User),(p:Post)
                where elementid(u) = $userid
                  and elementid(p) = $postid
                create(u)-[:LIKED]->(p)
            """,
            userid=user.id,
            postid=post.id,
        )

    def add_follow_tx(self, tx: ManagedTransaction, user: User, other: User) -> None:
        if user.id == "" or user.id == "":
            raise RuntimeError(f"id for user {user} or for user {user} was not filled")

        tx.run(
            """match(u:User),(o:User)
                where elementid(u) = $userid
                  and elementid(o) = $otherid
                create(u)-[:FOLLOWS]->(o)
            """,
            userid=user.id,
            otherid=other.id,
        )
