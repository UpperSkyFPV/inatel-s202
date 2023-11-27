from dataclasses import dataclass


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
    likes: list[str]
    id: str = ""
