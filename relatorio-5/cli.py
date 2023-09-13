import inspect
import json
import readline
import shlex
from typing import Any, Callable, Optional, Union, get_args, get_origin, get_type_hints
from rich import print


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

    Tips:
    - Running an empty command (just `ENTER` in the prompt) will
      repeat the last command.
    - The `_` value will be replaced with the return value of the
      last command.
    - Setting the `$SILENT` variable to `True` will disable some
      warnings, like:
      - Access to undefined variables
    - Setting the `$CHATTY` variable to `True` will make so that
      every command's args and kwargs are printed before they are
      handed to the implementation function.
    """

    previous_command: str | None
    last_result: Any
    keep_running: bool
    env: dict[str, Any]

    def __init__(self) -> None:
        self.previous_command = None
        self.last_result = None
        self.keep_running = True
        self.env = {"SILENT": False, "CHATTY": False}

    def run(self):
        """Run the REPL. Exit with `CTR+D`, `CTRL+C` or `exit`"""
        # setup readline for tab complete
        readline.parse_and_bind("tab: complete")
        # setup our custom completion function
        readline.set_completer(self.completer)

        # the REPL loop runs until `exit` is called
        while self.keep_running:
            # Read a line (using `readline` under the hood), checking for
            # `CTRL+D` and `CTRL+C`.
            try:
                line = input("> ")
            except (EOFError, KeyboardInterrupt):
                break

            # parse the arguments
            args, kwargs, _ = self.parse_argv(line)

            # re-run the last command on empty input
            if len(args) == 0:
                if self.previous_command is not None:
                    args, kwargs, _ = self.parse_argv(self.previous_command)
                else:
                    continue

            # save what was the return code of the command and the actual line executed
            self.last_result = self.exec(args, kwargs)
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
        args, kwargs, last_was_kw = self.parse_argv(line, True)
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

            if state < len(argnames):
                return argnames[state]
            return None

        key = args[-1] if len(args) > 0 else ""
        idx = len(args) - 1 if len(args) > 0 else 0
        argnames = [a for a in argnames[idx:] if line[-1] == " " or a.startswith(key)]
        if state < len(argnames):
            return argnames[state]
        return None

    def parse_argv(
        self, line: str, silent=False
    ) -> tuple[list[str], dict[str, str], bool]:
        """Returns a tuple with:
        - positional arguments
        - keyword arguments
        - if the last parsed argument was keyword argument"""
        s = shlex.split(line)

        args = []
        kwargs = {}
        last_was_kw = False

        for part in s:
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

        return args, kwargs, last_was_kw

    def get_method(self, name: str) -> Callable | None:
        """Get a method by it's command name"""
        return getattr(self, f"cmd_{name}", None)

    def apply_args(self, method: Callable, args: list[str], kwargs: dict[str, str]):
        """Transform the arguments to the correct types expected by the function.

        This is where we substitute variables (with `$"name"`) and the `_` special value
        """
        hints = get_type_hints(method)

        conv_args = []
        conv_kwargs = {}

        def convert_type(key: str, ty, arg):
            """Perform substitution and conversion to the target type of the command"""
            # the result of the last command
            if arg == "_":
                arg = self.last_result

            # variables
            elif len(arg) > 0 and arg[0] == "$":
                value = self.env.get(arg[1:], None)
                if value is None and not self.env.get("SILENT", False):
                    self.pwarn(f"undefined variable '{arg}'")

                arg = value

            try:
                if get_origin(ty) is Union:
                    ty = get_args(ty)[0]
                    return ty(arg)
                if ty is Any:
                    return arg

                if callable(ty):
                    return ty(arg)
            except ValueError as e:
                self.perror(f"invalid value for {key}: {e}")

            return arg

        for key, kwarg in kwargs.items():
            if key not in hints:
                continue

            ty = hints.pop(key)
            # print(f"{key=}, {kwarg=}: {ty=} {type(ty)=}")

            conv = convert_type(key, ty, kwarg)
            conv_kwargs[key] = conv

        for idx, (arg, (key, ty)) in enumerate(zip(args, hints.items())):
            # print(f"{key=}, {arg=}: {ty=} {type(ty)=}")
            conv_args.append(convert_type(f"position {idx}", ty, arg))

        return conv_args, conv_kwargs

    def exec(self, args: list[str], kwargs: dict[str, str]):
        name = args.pop(0)
        method = self.get_method(name)
        if method is None or not callable(method):
            return self.unknown_command(name)

        try:
            args, kwargs = self.apply_args(method, args, kwargs)

            if self.env.get("CHATTY", False):
                print(args, kwargs)
            r = method(*args, **kwargs)
            print(f"< {r}")
            return r
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

    def cmd_help(self, name: Optional[str] = None):
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

    def cmd_echo(self, value: Any):
        """Echo the value that it is given"""
        return value

    def cmd_dumpenv(self):
        """Dump the environment"""
        return self.env

    def cmd_saveenv(self, name="env.json"):
        """Save the current environment to a json file"""
        with open(name, 'w') as f:
            json.dump(self.env, f)

        return name

    def cmd_test(self, value: Any) -> bool:
        """Given any value, will try to convert it to a boolean.
        The only "false's" are empty strings and `False`"""
        if value == "False" or value == "":
            return False

        return True

    def cmd_exit(self):
        """Exit from the REPL loop"""
        self.keep_running = False
