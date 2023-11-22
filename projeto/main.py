from dataclasses import dataclass
from typing import Callable, Optional, TypeVar

from neo4j import Driver, GraphDatabase, ManagedTransaction
from rich.console import Console
from rich.table import Table
from cli import CliBase

c = Console()

T = TypeVar("T")


@dataclass
class User:
    name: str
    id: str = ""


@dataclass
class Post:
    title: str
    contents: str
    id: str = ""


@dataclass
class FullPost:
    title: str
    contents: str
    author: User
    likes: int
    id: str = ""


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

            return [
                FullPost(
                    author=user,
                    title=item.value("p.title"),
                    contents=item.value("p.contents"),
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
                    return p.title, p.contents, elementid(p), u.name, elementid(u), count(uu)
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
            likes=r.get("count(uu)"),
            id=r.get("elementid(p)"),
        )

    def get_posts_of_tx(self, tx: ManagedTransaction, user: User) -> list[FullPost]:
        r = tx.run(
            """match(p:Post)-[:CREATED_BY]->(u:User)
                optional match(uu:User)-[:LIKED]->(p)
                    where elementid(u) = $userid
                    return p.title, p.contents, elementid(p), u.name, elementid(u), count(uu)
            """,
            userid=user.id,
        )

        return [
            FullPost(
                title=i.get("p.title"),
                contents=i.get("p.contents"),
                author=User(i.get("u.name"), i.get("elementid(u)")),
                likes=i.get("count(uu)"),
                id=i.get("elementid(p)"),
            )
            for i in r
        ]

    def get_posts_tx(self, tx: ManagedTransaction) -> list[FullPost]:
        r = tx.run(
            """match(p:Post)
                optional match(p)-[:CREATED_BY]->(u:User)
                optional match(uu:User)-[:LIKED]->(p)
                    return p.title, p.contents, elementid(p), u.name, elementid(u), count(uu)
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
                likes=i.get("count(uu)"),
                id=i.get("elementid(p)"),
            )
            for i in r
        ]

    def delete_post_tx(self, tx: ManagedTransaction, post: Post) -> None:
        tx.run(
            "match(p:Post) where elementid(p) = $postid detach delete p", userid=post.id
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


class Cli(CliBase):
    db: Database
    curr_user: User | None

    def __init__(self, console: Console, db: Database) -> None:
        super().__init__(console)
        self.db = db
        self.curr_user = None

    def cmd_login(self, id: str = "", name: str = "") -> Optional[User]:
        """Faz o login como um usuário (usando seu ID ou nome). A partir desse momento
        algumas das funções poderão usar de atalhos, veja as documentções individuais.
        """
        if id == "" and name == "":
            c.print("[red]Give either `id` or `name`")
            return None

        if id != "":
            u = self.db.get_user_by_id(id)
            if u is None:
                c.print(f"[red]Failed to get user with id: {id}")
            self.curr_user = u
        elif name != "":
            u = self.db.get_user_by_name(name)
            if u is None:
                c.print(f"[red]Failed to get user with id: {id}")
            self.curr_user = u

        return self.curr_user

    def cmd_logout(self) -> None:
        """Logout do usuário atualmente logado."""
        if self.curr_user is None:
            c.print("[cyan]Not logged-in")

        self.curr_user = None

    def cmd_get_user_by_id(self, id: str) -> User | None:
        """Get an user by it's id
        - Se `id` for 'me' ou um string vazio, vai ser usar o usuário logado no momento.
        """
        if id == "me" or id == "":
            if self.curr_user is None:
                c.print(f"[red]No user is logged in for use of {id=}")
                return None

            id = self.curr_user.id

        return self.db.get_user_by_id(id)

    def cmd_get_user_by_name(self, name: str) -> User | None:
        """Get an user by it's name
        - Se `name` for um string vazio, vai ser usar o usuário logado no momento.
        """
        if name == "":
            if self.curr_user is None:
                c.print(f"[red]No user is logged in for use of {name=}")
                return None

            name = self.curr_user.name

        return self.db.get_user_by_name(name)

    def cmd_view_users(self, silent: bool = False) -> list[User] | None:
        """Print de todos os usuários registrados como uma tabela.
        O parâmetro `silent` pode ser usado para não usar do print, e sim retornar a lista.
        """
        users = self.db.get_users()
        if silent:
            return users

        table = Table("id", "name")
        for user in users:
            table.add_row(user.id, user.name)

        c.print(table)

    def cmd_view_posts(self, silent: bool = False) -> list[FullPost] | None:
        """Print de todos os posts registrados como uma tabela.
        O parâmetro `silent` pode ser usado para não usar do print, e sim retornar a lista.
        """
        posts = self.db.get_posts()
        if silent:
            return posts

        table = Table("id", "author", "likes", "title", "contents")
        for post in posts:
            table.add_row(
                post.id, post.author.name, str(post.likes), post.title, post.contents
            )

        c.print(table)

    def cmd_view_posts_of(self, id: str, silent: bool = False) -> list[FullPost] | None:
        """Print de todos os posts de um usuário específico.
        - O parâmetro `silent` pode ser usado para não usar do print, e sim retornar a lista.
        - Se `id` for 'me' ou um string vazio, vai ser usar o usuário logado no momento.
        """
        if id == "me" or id == "":
            if self.curr_user is None:
                c.print(f"[red]No user is logged in for use of {id=}")
                return None

            id = self.curr_user.id

        posts = self.db.get_posts_of(User("", id=id))
        if silent:
            return posts

        table = Table("id", "author", "likes", "title", "contents")
        for post in posts:
            table.add_row(
                post.id, post.author.name, str(post.likes), post.title, post.contents
            )

        c.print(table)

    def cmd_likes_of(self, postid: str, silent: bool = False) -> list[User] | None:
        """Print de todos os usuário que deram um like em um post.
        - O parâmetro `silent` pode ser usado para não usar do print, e sim retornar a lista.
        """
        users = self.db.get_likes(Post("", "", postid))
        if silent:
            return users

        table = Table("id", "name")
        for user in users:
            table.add_row(user.id, user.name)

        c.print(table)

    def cmd_like(self, userid: str, postid: str) -> None:
        """Dê um like em um post.
        - Se `id` for 'me' ou um string vazio, vai ser usar o usuário logado no momento.
        """
        if userid == "me" or userid == "":
            if self.curr_user is None:
                c.print(f"[red]No user is logged in for use of id={id=}")
                return

            userid = self.curr_user.id

        self.db.add_like(User("", id=userid), Post("", "", id=postid))

    def cmd_follow(self, userid: str, other_user_id: str) -> None:
        """Siga outro usuário.
        - Se `id` for 'me' ou um string vazio, vai ser usar o usuário logado no momento.
        """
        if userid == "me" or userid == "":
            if self.curr_user is None:
                c.print(f"[red]No user is logged in for use of id={id=}")
                return

            userid = self.curr_user.id

        self.db.add_follow(User("", id=userid), User("", id=other_user_id))

    def cmd_view_follows(self, id: str, silent: bool = False) -> list[User] | None:
        """Print de todos os usuários que seguem um usuário específico.
        - O parâmetro `silent` pode ser usado para não usar do print, e sim retornar a lista.
        - Se `id` for 'me' ou um string vazio, vai ser usar o usuário logado no momento.
        """
        if id == "me" or id == "":
            if self.curr_user is None:
                c.print(f"[red]No user is logged in for use of {id=}")
                return None

            id = self.curr_user.id

        users = self.db.get_follows(User("", id=id))
        if silent:
            return users

        table = Table("id", "name")
        for user in users:
            table.add_row(user.id, user.name)

        c.print(table)

    def cmd_view_followers(self, id: str, silent: bool = False) -> list[User] | None:
        """Print de todos os seguidores de um usuário específico.
        - O parâmetro `silent` pode ser usado para não usar do print, e sim retornar a lista.
        - Se `id` for 'me' ou um string vazio, vai ser usar o usuário logado no momento.
        """
        if id == "me" or id == "":
            if self.curr_user is None:
                c.print(f"[red]No user is logged in for use of {id=}")
                return None

            id = self.curr_user.id

        users = self.db.get_followers(User("", id=id))
        if silent:
            return users

        table = Table("id", "name")
        for user in users:
            table.add_row(user.id, user.name)

        c.print(table)

    def cmd_create_user(self, name: str) -> User:
        """Cria um novo usuário e retorna seu objeto."""
        return self.db.create_user(User(name=name))

    def cmd_create_post(self, created_by: str, title: str, contents: str) -> Post:
        """Cria um novo post e retorna seu objeto."""
        return self.db.create_post(User("", created_by), Post(title, contents))

    def cmd_delete_user(self, id: str) -> None:
        """Deleta um usuário pelo seu ID."""
        return self.db.delete_user(User("", id=id))

    def cmd_delete_post(self, id: str) -> None:
        """Deleta um post por seu ID.
        Importante: verifique a política de privacidade do serviço primeiro.
        """
        if self.curr_user is None:
            c.log("[red]Not logged in")
            return

        if self.curr_user.name != "Elon Musk":
            c.log("[bold red]Not allowed as per the privacy policy")
            return

        self.db.delete_post(Post("", "", id=id))

    def cmd_update_user(self, id: str, name: str) -> None:
        """Atualiza o nome de um usuário usando seu ID."""
        return self.db.update_user(User(name=name, id=id))

    def cmd_update_post(self, id: str, title: str, contents: str) -> None:
        """Atualiza o título e conteúdo de um post usando seu ID.
        Importante: verifique a política de privacidade do serviço primeiro.
        """
        if self.curr_user is None:
            c.print("[red]Not logged in")
            return

        if self.curr_user.name != "Elon Musk":
            c.log("[bold red]Not allowed as per the privacy policy")
            return

        return self.db.update_post(Post(title, contents, id))

    def cmd_User(self, name: str, id: str = "") -> User:
        """Cria um objeto `User` e o retorna."""
        return User(name, id)

    def cmd_Post(self, title: str, contents: str, id="") -> Post:
        """Cria um objeto `Post` e o retorna."""
        return Post(title, contents, id)


def main() -> None:
    c.log("starting")

    with open(".secret") as f:
        password = f.read().strip()

    db = Database.connect(
        "neo4j+s://54129c6f.databases.neo4j.io:7687", "neo4j", password
    )
    c.log("connected to database")

    cli = Cli(c, db)
    cli.run()

    # db.reset()
    # c.log("cleaned database")

    # bob = db.create_user(User("Bob"))
    # c.log(bob)

    # tom = db.create_user(User("Tom"))
    # c.log(tom)

    # john = db.create_user(User("John"))
    # c.log(john)

    # genius = db.create_post(bob, Post("Genius", "Tom is a genius"))
    # c.log(genius)

    # cpp = db.create_post(bob, Post("C++", "C++ is hard"))
    # c.log(cpp)

    # db.add_like(tom, genius)
    # db.add_like(tom, cpp)
    # c.log("added tom likes")

    # db.add_like(john, genius)
    # c.log("added john like")

    # r = db.get_liked_by(tom)
    # c.log(r)

    # r = db.get_likes(cpp)
    # c.log(r)

    # r = db.get_user_by_id(john.id)
    # c.log(r)

    # r = db.get_user_by_id("1kmlcads")
    # c.log(r)

    # r = db.get_users()
    # c.log(r)

    # p = db.get_posts()
    # c.log(p)

    # table = Table()

    # c.print(table)


if __name__ == "__main__":
    main()
