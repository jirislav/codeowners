"""
Python port of https://github.com/softprops/codeowners
"""
import re
from typing import List, Optional, Pattern, Tuple

from typing_extensions import Literal

__all__ = ["CodeOwners"]

OwnerTuple = Tuple[Literal["USERNAME", "TEAM", "EMAIL"], str]


TEAM = re.compile(r"^@\S+/\S+")
USERNAME = re.compile(r"^@\S+")
EMAIL = re.compile(r"^\S+@\S+")


def path_to_regex(pattern: str) -> Pattern[str]:
    """
    ported from https://github.com/hmarr/codeowners/blob/d0452091447bd2a29ee508eebc5a79874fb5d4ff/match.go#L33
    """
    regex = ""

    try:
        slash_pos = pattern.index("/")
        anchored = slash_pos != len(pattern) - 1
    except ValueError:
        anchored = False

    if anchored:
        regex += r"\A"
    else:
        regex += r"(?:\A|/)"

    matches_dir = pattern[-1] == "/"
    pattern_trimmed = pattern.strip("/")

    in_char_class = False
    escaped = False

    # NOTE: this is an ugly hack so we can skip a letter in the loop, maybe
    # refactor using generators or similar?
    i = -1
    while i < len(pattern_trimmed) - 1:
        i += 1
        ch = pattern_trimmed[i]

        if escaped:
            regex += re.escape(ch)
            escaped = False
            continue

        if ch == "\\":
            escaped = True
        elif ch == "*":
            if i + 1 < len(pattern_trimmed) and pattern_trimmed[i + 1] == "*":
                left_anchored = i == 0
                leading_slash = i > 0 and pattern_trimmed[i - 1] == "/"
                right_anchored = i + 2 == len(pattern_trimmed)
                trailing_slash = (
                    i + 2 < len(pattern_trimmed) and pattern_trimmed[i + 2] == "/"
                )

                if (left_anchored or leading_slash) and (
                    right_anchored or trailing_slash
                ):
                    regex += ".*"

                    i += 2
                    continue
            regex += "[^/]*"
        elif ch == "?":
            regex += "[^/]"
        elif ch == "[":
            in_char_class = True
            regex += ch
        elif ch == "]":
            if in_char_class:
                regex += ch
                in_char_class = False
            else:
                regex += re.escape(ch)
        else:
            regex += re.escape(ch)

    if in_char_class:
        raise ValueError(f"unterminated character class in pattern {pattern}")

    if matches_dir:
        regex += "/"
    else:
        regex += r"(?:\Z|/)"
    return re.compile(regex)


def parse_owner(owner: str) -> Optional[OwnerTuple]:
    if TEAM.match(owner):
        return ("TEAM", owner)
    if USERNAME.match(owner):
        return ("USERNAME", owner)
    if EMAIL.match(owner):
        return ("EMAIL", owner)
    return None


def pattern_matches(path: str, pattern: Pattern[str]) -> bool:
    return pattern.search(path) is not None


class CodeOwners:
    def __init__(self, text: str) -> None:
        paths: List[Tuple[Pattern[str], List[OwnerTuple]]] = []
        for line in text.splitlines():
            if line != "" and not line.startswith("#"):
                elements = iter(line.split())
                path = next(elements, None)
                if path is not None:
                    owners: List[OwnerTuple] = []
                    for owner in elements:
                        owner_res = parse_owner(owner)
                        if owner_res is not None:
                            owners.append(owner_res)
                    paths.append((path_to_regex(path), owners))
        paths.reverse()
        self.paths = paths

    def of(self, filepath: str) -> List[OwnerTuple]:
        for pattern, owners in self.paths:
            if pattern_matches(filepath, pattern):
                return owners
        return []
