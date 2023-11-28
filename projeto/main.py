import json
from typing import Optional

from rich.console import Console
from rich.table import Table

from cli import CliBase
from database import Database
from models import FullPost, Post, User

c = Console()


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

        table = Table("id", "name", title="Users")
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

        table = Table("id", "author", "likes", "title", "contents", title="Posts")
        for post in posts:
            table.add_row(
                post.id,
                post.author.name,
                str(len(post.likes)),
                post.title,
                post.contents,
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

        table = Table(
            "id", "author", "likes", "title", "contents", title=f"Posts of user {id}"
        )
        for post in posts:
            table.add_row(
                post.id,
                post.author.name,
                str(len(post.likes)),
                post.title,
                post.contents,
            )

        c.print(table)

    def cmd_likes_of(self, postid: str, silent: bool = False) -> list[User] | None:
        """Print de todos os usuário que deram um like em um post.
        - O parâmetro `silent` pode ser usado para não usar do print, e sim retornar a lista.
        """
        users = self.db.get_likes(Post("", "", postid))
        if silent:
            return users

        table = Table("id", "name", title=f"Likes of post {postid}")
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

        table = Table("id", "name", title=f"User {id} is following")
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

        table = Table("id", "name", title=f"Followers of {id}")
        for user in users:
            table.add_row(user.id, user.name)

        c.print(table)

    def cmd_create_user(self, name: str) -> User:
        """Cria um novo usuário e retorna seu objeto."""
        return self.db.create_user(User(name=name))

    def cmd_create_post(self, created_by: str, title: str, contents: str) -> Post:
        """Cria um novo post e retorna seu objeto.
        - Se `created_by` for 'me' ou um string vazio, vai ser usar o usuário logado no momento.
        """
        if created_by == "me" or created_by == "":
            if self.curr_user is None:
                c.print(f"[red]No user is logged in for use of {created_by=}")
            else:
                created_by = self.curr_user.id

        return self.db.create_post(User("", id=created_by), Post(title, contents))

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
        opt = json.load(f)

    db = Database.connect(opt["host"], opt["username"], opt["password"])
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
