# Projeto Banco de Dados II

O projeto implementado é uma rede social simplificada usando de um banco de dados orientado a grafos, o *Neo4J*.

A implementação foi feita em **Python** usando somente da biblioteca oficial para conexão com o banco para processamento.

Foi feito uso também da biblioteca [rich](https://github.com/Textualize/rich) para tornar o *output* mais apresentável. Todas as outras funcionalidades usaram somente da biblioteca padrão do **Python 3.11**.

> Versões mais antigas da linguagem podem não funcionar.

---

## A funcionalidade

Foi implementado o suficiente para permitir:

- Criar usuários com: **nome**
- Criar *posts* com: **título** e **conteúdo**. Todo *post* deve obrigatoriamente estar conectado a um usuário através da relação: `CREATED_BY`.
- Dar *like* em posts, criando uma relação `usuário -[:LIKED]-> post`.
- Seguir outros usuários, criando uma relação `usuário -[:FOLLOWS]-> usuário`.

---

## Implementação

O sistema possui uma classe `Database`, responsável por abstrair as *queries* usadas pelo *driver* *Neo4J* em funções específicas ao aplicativo.

Foi escolhido usar de uma única classe para abstrair todas as funcionalidades ao invés de *Data Access Objects* por conta das relações intricadas os tornarem inconvenientes.

---

Existem **3** objetos **POD** (*Plain Old Data*) que são utilizados pela classe `Database`:

- `User`: Que armazena um único usuário:

    ```py
    @dataclass
    class User:
        name: str
        id: str = ""
    ```

- `Post`: Que armazena um único *post*:

    ```py
    @dataclass
    class Post:
        title: str
        contents: str
        id: str = ""
    ```

- `FullPost`: Que armazena um *post* mais suas relações:

    ```py
    @dataclass
    class FullPost:
        title: str
        contents: str
        author: User
        likes: list[str] # user ids
        id: str = ""
    ```

---

## CLI

Como requisitado, foi feita uma interface por linha de comando para o *app*. Esta foi feita usando de um *shell* completamente customizado para tornar o processo de criar novos comandos e interagir com estes o mais simples o possível.

Aqueles acostumados com `bash` ou `sh` vão estranhar pouca coisa.

Comandos são simplesmente métodos que iniciam com `cmd_` definidos em uma instância que herde de `CliBase`.

---

Por exemplo, o comando `delete_user` é definido da seguinte forma:

```py
def cmd_delete_user(self, id: str) -> None:
    """Deleta um usuário pelo seu ID."""
    return self.db.delete_user(User("", id=id))
```

E permite que seja usado da seguinte forma já com *autocomplete* para seu nome e parâmetros:

```py
> help delete_user
Help on method cmd_delete_user in module __main__:

cmd_delete_user(id: str) -> None method of __main__.Cli instance
    Deleta um usuário pelo seu ID.

< None
> delete_user
error: Cli.cmd_delete_user() missing 1 required positional argument: 'id'
< None
> delete_user 4:af0946ba-f1c6-4c54-9f83-9cc521d1fd9a:0
< None
```

Esse método depende completamente da funcionalidade de *Type-Hints* do **Python**.

---

A implementação permite ainda diversas coisas avançadas como variáveis e expressões em cadeia.

Por exemplo:

```bash
> create_user Bob | field _ id | set Bob
< '4:af0946ba-f1c6-4c54-9f83-9cc521d1fd9a:14'
> view_posts_of $Bob
# truncated
< None
```

Ou ainda:

```bash
> get_user_by_name Bob | field _ id | view_posts_of silent=1 | idx _ 0 | field _ likes | idx _ 0 | get_user_by_id
< User(name='John', id='4:af0946ba-f1c6-4c54-9f83-9cc521d1fd9a:0')
```
