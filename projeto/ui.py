from dataclasses import dataclass
import json
from typing import Literal, cast

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Input,
    LoadingIndicator,
    Markdown,
    Static,
    TextArea,
)

from database import Database
from models import FullPost, Post, User


class LogInWidget(Static):
    """Display a button for login"""

    @dataclass
    class Login(Message):
        user: User

    @dataclass
    class Logout(Message):
        ...

    db: Database

    def __init__(self, db: Database):
        super().__init__()
        self.db = db

    def compose(self) -> ComposeResult:
        yield Static("Not logged in!")
        yield Input(placeholder="Username")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        await self.query_one(Static).remove()
        await self.query_one(Input).remove()
        await self.mount(LoadingIndicator())

        self.run_worker(lambda: self.do_get_user(event.value), thread=True)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        await self.query_one(Static).remove()
        await self.query_one(Button).remove()

        await self.mount(Static("Not logged in!"), Input(placeholder="Username"))
        self.post_message(LogInWidget.Logout())

    def do_get_user(self, name: str) -> None:
        u = self.db.get_user_by_name(name)
        if u is None:
            self.run_worker(self.mount_login_things(name, "fail"))
            return

        self.post_message(LogInWidget.Login(u))
        self.run_worker(self.mount_login_things(u.name, "success"))

    async def mount_login_things(
        self, name: str, action: Literal["fail"] | Literal["success"]
    ) -> None:
        if action == "fail":
            await self.query(LoadingIndicator).remove()
            await self.mount(
                Static(f"Failed to login, no user with name: {name}"),
                Input(placeholder="Username"),
            )
        elif action == "success":
            await self.query(LoadingIndicator).remove()
            await self.mount(Static(f"Logged in as {name}"), Button("Log-out"))


class NewPostWidget(Static):
    """Display a form for creating new posts"""

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Title")
        yield TextArea(language="markdown")

        yield Button("POST")


class FollowingUserWidget(Static):
    user: User
    db: Database

    def __init__(self, user: User, db: Database) -> None:
        super().__init__()

        self.user = user
        self.db = db

    def get_user_followers(self):
        r = self.db.get_followers(self.user)

        self.run_worker(self.mount_followers(r))

    async def mount_followers(self, followers: list[User]):
        await self.query(LoadingIndicator).remove()
        await self.query(".followers").remove()
        await self.mount(Static(f"{len(followers)} followers", classes="followers"))

    def on_mount(self) -> None:
        self.run_worker(self.get_user_followers, thread=True)

    def compose(self) -> ComposeResult:
        yield Static(self.user.name, classes="username")
        yield Static("[i]...", classes="followers")


class FollowingWidget(VerticalScroll):
    db: Database

    logged_in_user: reactive[User | None] = reactive(None)
    users: list[User] = []

    def __init__(self, db: Database):
        super().__init__()
        self.db = db

    def watch_logged_in_user(
        self, old_user: User | None, new_user: User | None
    ) -> None:
        print(old_user, new_user)

        match (old_user, new_user):
            case (None, nu) if nu is not None:
                self.query(Static).remove()
                self.mount(LoadingIndicator())

                self.run_update_users()
            case (ou, None) if ou is not None:
                self.query(FollowingUserWidget).remove()
                self.mount(Static("[bold]Log-in to follow other users"))
            case (None, None):
                print("=====> (None, None)")

    def run_update_users(self) -> None:
        self.run_worker(self.update_users, thread=True)

    def update_users(self) -> None:
        if self.logged_in_user is None:
            return

        self.users = self.db.get_follows(self.logged_in_user)
        print(self.users)

        self.run_worker(self.mount_users(self.users))

    async def mount_users(self, users: list[User]):
        await self.query(LoadingIndicator).remove()
        await self.query(Static).remove()

        if len(users) == 0:
            await self.mount(Static("Not following anyone"))
        else:
            await self.mount_all((FollowingUserWidget(u, self.db) for u in users))

    def compose(self) -> ComposeResult:
        yield Static("[bold]Log-in to follow other users", classes="info_center")


class PostWidget(Static):
    post: FullPost
    logged_in_user: reactive[None | User] = reactive(None)

    @dataclass
    class Liked(Message):
        post: FullPost

    def __init__(self, post: FullPost) -> None:
        super().__init__()
        self.post = post

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical():
                yield Static(self.post.title, classes="title")
            with Vertical():
                yield Static(self.post.author.name, classes="author")

        yield Markdown(self.post.contents)

        with Container(classes="like_container"):
            yield Checkbox(
                f"{len(self.post.likes)} likes",
                False
                if self.logged_in_user is None
                else self.logged_in_user.id in self.post.likes,
                id="likeit",
                disabled=self.logged_in_user is None,
            )

            yield Checkbox(
                f"Follow [i]{self.post.author.name}",
                False,
                id="followit",
                disabled=self.logged_in_user is None,
            )

    def watch_logged_in_user(self, new_value: User | None) -> None:
        self.set_checkbox_disable(True)

        if new_value is not None:
            w = cast(Checkbox, self.query_one("#likeit"))
            w.value = new_value.id in self.post.likes

            # w = cast(Checkbox, self.query_one("#followit"))

        self.set_checkbox_disable(new_value is None)

    def set_checkbox_disable(self, val: bool) -> None:
        for c in self.query(Checkbox):
            c.disabled = val

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        chck = event.checkbox
        if chck.id == "likeit" and event.value:
            self.set_checkbox_disable(False)
            self.post_message(PostWidget.Liked(self.post))
        elif chck.id == "followit":
            ...


class FeedWidget(VerticalScroll):
    db: Database
    logged_in_user: reactive[User | None] = reactive(None)

    def __init__(self, db: Database):
        super().__init__()
        self.db = db

    async def run_update_posts(self) -> None:
        await self.query(PostWidget).remove()

        if len(self.query(LoadingIndicator)) == 0:
            await self.mount(
                LoadingIndicator(
                    id="inner-loading-indicator", classes="bordered-loading-indicator"
                )
            )

        self.run_worker(self.update_posts, thread=True, exclusive=True)

    def update_posts(self) -> None:
        posts = self.db.get_posts()

        self.run_worker(self.mount_posts(posts))

    async def mount_posts(self, posts: list[FullPost]):
        await self.query(LoadingIndicator).remove()
        await self.mount_all((PostWidget(p) for p in posts))

    def watch_logged_in_user(self, value: User | None) -> None:
        for p in self.query(PostWidget):
            p.logged_in_user = value

    def on_post_widget_liked(self, event: PostWidget.Liked) -> None:
        self.run_worker(lambda: self.liked_worker(event.post), thread=True)

    def liked_worker(self, post: Post) -> None:
        if self.logged_in_user is None:
            print("ERROR: Should not have a null user here")
            return

        self.db.add_like(self.logged_in_user, post)

        new_post = self.db.get_post_by_id(post.id)
        self.run_worker(self.update_one_post(new_post))

    async def update_one_post(self, new_post: FullPost | None) -> None:
        if new_post is None:
            await self.run_update_posts()
            return

        for i, c in enumerate(self.query(PostWidget)):
            if c.post.id == new_post.id:
                c.remove()

            self.mount(PostWidget(new_post), after=i)

    async def on_mount(self) -> None:
        await self.run_update_posts()


class SocialNetworkApp(App):
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("ctrl+q", "quit", "Quit from the App"),
        ("r", "refresh", "Refresh all"),
    ]

    CSS_PATH = ["dump.tcss", "loginwidget.tcss"]

    db: Database | None
    logged_in_user: reactive[User | None] = reactive(None, layout=True)

    def __init__(self):
        super().__init__()
        self.db = None

    def connect_to_database(self):
        self.log("connecting to database!")
        with open(".secret") as f:
            opt = json.load(f)

        self.db = Database.connect(opt["host"], opt["username"], opt["password"])
        self.log("Connected!")

        self.run_worker(self.mount_feed())

    async def mount_feed(self):
        assert self.db is not None

        await self.query("LoadingIndicator").remove()

        c = self.query_one("#content-container")
        await c.mount(FeedWidget(self.db))

        c = self.query_one("#left-dock")
        await c.mount(LogInWidget(self.db), FollowingWidget(self.db))

    def on_mount(self) -> None:
        self.run_worker(self.connect_to_database, thread=True)

    def on_log_in_widget_login(self, event: LogInWidget.Login):
        self.logged_in_user = event.user

    def on_log_in_widget_logout(self, event: LogInWidget.Logout):
        self.logged_in_user = None

    def watch_logged_in_user(
        self, old_user: User | None, new_user: User | None
    ) -> None:
        if w := self.query(FollowingWidget):
            w[0].logged_in_user = new_user
        if w := self.query(FeedWidget):
            w[0].logged_in_user = new_user

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal():
            with Vertical(id="left-dock"):
                yield LoadingIndicator(classes="bordered-loading-indicator")

            with Vertical(id="content-container"):
                yield NewPostWidget()
                yield LoadingIndicator(classes="bordered-loading-indicator")

        yield Footer()

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

    async def action_refresh(self) -> None:
        if w := self.query(FeedWidget):
            await w[0].run_update_posts()
        if w := self.query(FollowingWidget):
            w[0].run_update_users()

    def action_quit(self) -> None:
        self.exit()


if __name__ == "__main__":
    app = SocialNetworkApp()
    app.run()
