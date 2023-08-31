import json
import os
from typing import Any


def json_log(name: str, data: Any, logdir="./json") -> None:
    if not os.path.exists(logdir):
        os.makedirs(logdir)

    with open(os.path.join(logdir, f"{name}.json"), "w") as f:
        json.dump(data, f, indent=4, separators=(",", ":"))
