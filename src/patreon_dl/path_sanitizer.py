_INVALID = set('<>:"/\\|?*') | {chr(c) for c in range(32)}


def sanitize(name: str, replacement: str = "_") -> str:
    return "".join(replacement if c in _INVALID else c for c in name)
