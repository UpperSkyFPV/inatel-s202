import inspect
import itertools
import json
import re
import readline
from typing import Any, Callable, Union, get_args, get_origin, get_type_hints

from rich import print


REGEX_STR = r"""(?:[^\s"`'|]|"(?:\\.|[^"])*"|`(?:\\.|[^`])*`|'(?:\\.|[^'])*')+|\|"""
REGEX = re.compile(REGEX_STR)

VarArgs = tuple[Any, ...]


def regex_lex(s: str) -> list[str]:
    return REGEX.findall(s)


def is_falsey_str(s: str) -> bool:
    return s == "False" or s == "false" or s == ""


class CliBase:
    """Base for creating an interactive CLI.

    Commands are defined using methods that start with `cmd_`,
    with it's arguments (typed please) beeing inspected for the
    command arguments.

    For example, this function:
    ```py
    def cmd_hello(self, name: str):
        '''This string will appear with the `help` command'''
        return f"Hello {name}!"
    ```
    will generate a command `hello NAME` with full support for
    positional and keyword arguments (like `hello name=bob`)
    with **completion**!
    Custom completion can also be implemented using a method like:
    ```py
    def completion_hello(
        self,
        sig: inspect.Signature,
        state: int,
        args: list[str],
        kwargs: dict[str, str],
    ) -> str | None:
        return None
    ```
    View the example implementation for the `completion_help`
    command and the `completer` method for help.

    Tips:
    - Running an empty command (just `ENTER` in the prompt) will
      repeat the last command.
    - The `_` value will be replaced with the return value of the
      last command.
    - Setting the `$SILENT` variable to `True` will disable some
      warnings, like:
      - Access to undefined variables
    - Setting the `$DEBUG` variable to `True` will make so that
      every command's args and kwargs are printed before they are
      handed to the implementation function.
    - Setting the `$PROMPT` variable will change the CLI prompt.
    - Strings can use the following caracters as delimiters: `"`,
      `'` and ```
    - The `^` prefix enters _json_ mode, so that the following
      WORD (joined characters or quoted string) will be parsed as
      json.
    """

    previous_command: str | None
    last_result: Any
    keep_running: bool
    env: dict[Any, Any]

    def __init__(self) -> None:
        self.previous_command = None
        self.last_result = None
        self.keep_running = True
        self.env = {"SILENT": False, "DEBUG": False, "PROMPT": "> "}

    def run(self):
        """Run the REPL. Exit with `CTR+D` or `exit`. `CTRL+C` cancels the current prompt"""
        # setup readline for tab complete
        readline.parse_and_bind("tab: complete")
        # setup our custom completion function
        readline.set_completer(self.completer)

        # the REPL loop runs until `exit` is called
        while self.keep_running:
            # Read a line (using `readline` under the hood), checking for
            # `CTRL+D` and `CTRL+C`.
            try:
                line = input(self.env.get("PROMPT", "> "))
            except EOFError:
                break
            except KeyboardInterrupt:
                print()
                continue

            # parse the arguments
            commands = self.parse_argv(line)
            if self.env.get("DEBUG", False):
                print("commands:", commands)

            # re-run the last command on empty input
            if len(commands) == 0:
                if self.previous_command is not None:
                    commands = self.parse_argv(self.previous_command)
                else:
                    continue

            for idx, (args, kwargs, _) in enumerate(commands):
                if len(args) == 0:
                    self.pwarn("Trailing piping found in command")
                    break

                # save what was the return code of the command and the actual line executed
                self.last_result = self.exec(args, kwargs, idx > 0)

            print(f"< {repr(self.last_result)}")

            self.previous_command = line

        print("\nbye!")

    def completer(self, text: str, state: int) -> str | None:
        """Black magic to get completion for the command."""
        origline = readline.get_line_buffer()
        line = origline.lstrip()
        stripped = len(origline) - len(line)
        begidx = readline.get_begidx() - stripped

        def root_complete():
            """Options for the top-level commands"""
            options = [
                j
                for j in (self.get_usable_name(i) for i in self.list_commands())
                if j.startswith(text)
            ]

            if state < len(options):
                return options[state]
            return None

        # at the start of the line
        if begidx == 0:
            return root_complete()

        # parse the arguments as they are
        commands = self.parse_argv(line, True)
        if len(commands) == 0:
            return root_complete()

        args, kwargs, last_was_kw = commands[-1]
        if len(args) == 0:
            return root_complete()

        # get the top-level command that is typed
        cmd = args.pop(0)
        if cmd == "":
            return root_complete()

        # get the actual method that should be called
        m = self.get_method(cmd)
        if m is None:
            return root_complete()

        # inspect the method and do a lot of checks to make completion for
        # the arguments to the command
        sig = inspect.signature(m)
        if (a := getattr(self, f"completion_{cmd}", None)) is not None:
            return a(sig, state, args, kwargs)

        argnames = [
            arg.name for arg in sig.parameters.values() if arg.name not in kwargs
        ]
        if len(args) == 0 and len(kwargs) == 0:
            if state < len(argnames):
                return argnames[state]
            return None

        if last_was_kw and line[-1] != " ":
            _, value = list(kwargs.items())[-1]
            if value == "":
                return None

            if value.startswith("$"):
                keys = [
                    k for k in (f"${i}" for i in self.env.keys()) if k.startswith(value)
                ]
                if state < len(keys):
                    return keys[state][1:]
                return None

            # if state < len(argnames):
            #     return argnames[state]
            return None

        key = args[-1] if len(args) > 0 else ""
        if key.startswith("$"):
            keys = [k for k in (f"${i}" for i in self.env.keys()) if k.startswith(key)]
            if state < len(keys):
                return keys[state][1:]
            return None

        idx = len(args) - 1 if len(args) > 0 else 0
        argnames = [a for a in argnames[idx:] if line[-1] == " " or a.startswith(key)]
        if state < len(argnames):
            return argnames[state]
        return None

    def parse_argv(
        self, line: str, silent=False
    ) -> list[tuple[list[str], dict[str, str], bool]]:
        """Returns a tuple with:
        - positional arguments
        - keyword arguments
        - if the last parsed argument was keyword argument"""
        words = regex_lex(line)
        out: list[tuple[list[str], dict[str, str], bool]] = []

        for cmd in (
            value
            for key, value in itertools.groupby(words, lambda z: z == "|")
            if not key
        ):
            args = []
            kwargs = {}
            last_was_kw = False

            for part in cmd:
                eq = part.split("=")
                # print(f"{eq=}")
                match eq:
                    case [s]:
                        args.append(s)
                        if len(kwargs) > 0 and not silent:
                            self.perror(
                                "Positional parameters should be before keyword parameters"
                            )
                        last_was_kw = False
                    case ["", _]:
                        args.append(part)
                        last_was_kw = True
                    case [lhs, rhs]:
                        kwargs[lhs] = rhs
                        last_was_kw = True

            out.append((args, kwargs, last_was_kw))

        return out

    def get_method(self, name: str) -> Callable | None:
        """Get a method by it's command name"""
        return getattr(self, f"cmd_{name}", None)

    def apply_args(
        self, method: Callable, args: list[str], kwargs: dict[str, str], is_piped: bool
    ):
        """Transform the arguments to the correct types expected by the function.

        This is where we substitute variables (with `$"name"`) and the `_` special value
        """
        hints = get_type_hints(method)

        conv_args = []
        conv_kwargs = {}

        had_underscore = False

        def any_startswith(v, s) -> bool:
            if isinstance(v, str):
                return v.startswith(s)
            return False

        def cleanup_type(arg):
            """Perform substitution and convert to inferred type"""
            nonlocal had_underscore

            if arg == "_":
                # the result of the last command
                arg = self.last_result
                had_underscore = True
            elif any_startswith(arg, "$"):
                # variables
                value = self.env.get(arg[1:], None)
                if value is None and not self.env.get("SILENT", False):
                    self.pwarn(f"undefined variable '{arg}'")

                arg = value
            elif (
                any_startswith(arg, '"')
                or any_startswith(arg, "'")
                or any_startswith(arg, "`")
            ):
                # explicit strings
                arg = arg[1:-1]
            elif any_startswith(arg, "^"):
                # json thing
                arg = arg[1:]
                if (
                    any_startswith(arg, '"')
                    or any_startswith(arg, "'")
                    or any_startswith(arg, "`")
                ):
                    arg = arg[1:-1]
                print(arg)
                arg = json.loads(arg)
            elif is_falsey_str(arg):
                # convert to boolean
                arg = False
            elif isinstance(arg, str) and arg.isnumeric():
                # convert to int
                arg = int(arg)

            return arg

        def convert_type(key: str, ty, arg):
            """Perform substitution and conversion to the target type of the command"""
            nonlocal had_underscore

            arg = cleanup_type(arg)

            if self.env.get("DEBUG", False):
                print(f"{arg=}: {ty=}")

            try:
                if get_origin(ty) is Union:
                    ty = get_args(ty)[0]
                    return ty(arg)
                if ty is Any or get_origin(ty) is tuple:
                    return arg

                if callable(ty):
                    return ty(arg)
            except ValueError as e:
                self.perror(f"invalid value for {key}: {e}")

            return arg

        for key, kwarg in kwargs.items():
            key = cleanup_type(key)
            if str(key) not in hints:
                continue

            ty = hints.pop(str(key))
            # print(f"{key=}, {kwarg=}: {ty=} {type(ty)=}")

            conv = convert_type(str(key), ty, kwarg)
            conv_kwargs[key] = conv

        for idx, (arg, (key, ty)) in enumerate(zip(args, hints.items())):
            # print(f"{key=}, {arg=}: {ty=} {type(ty)=}")
            conv_args.append(convert_type(f"position {idx}", ty, arg))

        if len(conv_args) < len(args):
            conv_args += args[len(conv_args):]

        if not had_underscore and is_piped:
            conv_args.append(self.last_result)

        return conv_args, conv_kwargs

    def exec(self, args: list[str], kwargs: dict[str, str], is_piped: bool):
        name = args.pop(0)
        method = self.get_method(name)
        if method is None or not callable(method):
            return self.unknown_command(name)

        if self.env.get("DEBUG", False):
            print("method:", inspect.signature(method))

        try:
            if self.env.get("DEBUG", False):
                print("raw:", args, kwargs)

            args, kwargs = self.apply_args(method, args, kwargs, is_piped)

            if self.env.get("DEBUG", False):
                print("parsed:", args, kwargs)

            return method(*args, **kwargs)
        except (TypeError, ValueError) as e:
            self.perror(f"{e}")
        except Exception as e:
            # catch all
            print(f"[red]Command error:[/]", e)
            return e

    def unknown_command(self, name: str):
        self.perror(f"unknown command: '{name}'")

    def perror(self, msg: str):
        print(f"[red]error: {msg}")

    def pwarn(self, msg: str):
        print(f"[yellow]warnings: {msg}")

    def list_commands(self) -> list[str]:
        """Get the names of all commands"""
        s = "cmd_"
        return [c for c in dir(self) if c.startswith(s)]

    def get_usable_name(self, name: str) -> str:
        """Remove the `cmd_` from the given function name"""
        return name[len("cmd_") :]

    def cmd_help(self, name: str | None = None):
        """Get help for how to use the CLI"""
        if name is None:
            print("Available commands:")

            def pretty_type(t: Any) -> str:
                if t is inspect.Signature.empty:
                    return "None"

                s = str(t)
                klass_start = "<class '"
                if s.startswith(klass_start):
                    return str(t)[len(klass_start) : -len("'>")]

                return str(t)

            for name in self.list_commands():
                sig = inspect.signature(getattr(self, name))
                name = self.get_usable_name(name)
                params = [
                    f"{p.name}: {pretty_type(p.annotation)}"
                    for p in sig.parameters.values()
                ]
                print(
                    f"- {name}({', '.join(params)}) -> {pretty_type(sig.return_annotation)}"
                )
            return

        method = self.get_method(name)
        if method is None:
            self.unknown_command(name)
            return

        help(method)

    def completion_help(
        self,
        sig: inspect.Signature,
        state: int,
        args: list[str],
        kwargs: dict[str, str],
    ) -> str | None:
        if len(args) <= 1:
            arg = args[-1] if len(args) > 0 else ""
            commands = [
                d
                for d in (self.get_usable_name(c) for c in self.list_commands())
                if d.startswith(arg)
            ]
            if state < len(commands):
                return commands[state]
            return None

        return None

    def cmd_inspect(self, name: str):
        """Use `get_type_hints` to inspect a command."""
        method = self.get_method(name)
        if method is None:
            self.unknown_command(name)
            return

        return get_type_hints(method)

    def cmd_set(self, key: str, value: Any):
        """Set a variable in the env to some value"""
        self.env[key] = value
        return value

    def cmd_idx(self, d: list[Any], *idxs: int) -> Any | None:
        """Get a value from the given list.
        Returns on the first `non-list` item that it gets.
        If no indexes are given, then retuns the input dictionary.

        Examples:
            - `get ^[0,[1,2]] 0` will output `0`.
            - `get ^[0,[1,2]] 1 0` will output `1`.
            - `get ^[0,[1,2]] 1 0 12` will output `1` as well.
        """

        for idx in idxs:
            d = d[idx]
            if not isinstance(d, list):
                break

        return d

    def cmd_key(self, d: dict[Any, Any], *keys: VarArgs) -> Any | None:
        """Get a value from the given dictionary.
        Returns on the first `non-dictionary` item that it gets.
        If no keys are given, then retuns the input dictionary.

        Examples:
            - `get ^{"a":0} a` will output `0`.
            - `get ^{"a":0} a b` will output `0` as well.
        """
        for key in keys:
            d = d.get(key, None)
            if not isinstance(d, dict):
                break

        return d

    def cmd_echo(self, value: Any):
        """Print the value and also return it"""
        print(value)
        return value

    def cmd_dumpenv(self):
        """Dump the environment"""
        return self.env

    def cmd_saveenv(self, name="env.json"):
        """Save the current environment to a json file"""

        def _default(obj):
            try:
                from bson.objectid import ObjectId

                if isinstance(obj, ObjectId):
                    return str(obj)
            except ImportError:
                pass
            raise ValueError(f"Object {type(obj)} is not json serializable")

        with open(name, "w") as f:
            json.dump(self.env, f, default=_default)

        return name

    def cmd_loadenv(self, name="env.json", overwrite=False):
        """Load an environment and set it as current. If `overwrite` is
        `False`, then merges with current environment"""
        with open(name) as f:
            env = json.load(f)

        if overwrite:
            self.env = env
        else:
            # python 3.9
            self.env = self.env | env

    def cmd_test(self, value: Any) -> bool:
        """Given any value, will try to convert it to a boolean.
        The only "false's" are empty strings, `false` and `False`"""
        if value == "False" or value == "false" or value == "":
            return False

        return True

    def cmd_exit(self):
        """Exit from the REPL loop"""
        self.keep_running = False
