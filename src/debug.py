import json
import sys


def log(step: str, value) -> None:
    if isinstance(value, (dict, list, tuple)):
        value = json.dumps(value, ensure_ascii=False, default=str)
    print(f"!!! {step}: {value}", file=sys.stderr, flush=True)
