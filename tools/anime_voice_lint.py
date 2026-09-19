#!/usr/bin/env python3
"""Lightweight static checks for the anime_voice app.

No C toolchain is available on this machine, so instead of a real compile we
check the two classes of error that actually bit us while writing the module:

  1. unbalanced braces / parens / brackets (catches truncated edits)
  2. undefined cross-module symbols: every av_* / memo_* style identifier that
     is *called* must be either declared in one of the module headers or
     defined in the same translation unit.

Plus a couple of cheap sanity checks (duplicate function definitions, headers
without include guards).
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

APP = (Path(__file__).resolve().parents[1]
       / "app" / "contest2026_236_anime_voice")

SRC = sorted(APP.glob("*.c"))
HDR = sorted(APP.glob("*.h"))
ALL = SRC + HDR

# ---------------------------------------------------------------- balance ---

def strip_noise(text: str) -> str:
    """Remove comments and string/char literals so they do not skew counting."""
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
        elif c == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
        elif c in "\"'":
            quote = c
            out.append(" ")
            i += 1
            while i < n:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == quote:
                    i += 1
                    break
                i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def check_balance(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    text = strip_noise(raw)
    problems = []
    for open_c, close_c, name in (("{", "}", "brace"), ("(", ")", "paren"),
                                  ("[", "]", "bracket")):
        depth = 0
        line = 1
        lowest = 0
        for ch in text:
            if ch == "\n":
                line += 1
            elif ch == open_c:
                depth += 1
            elif ch == close_c:
                depth -= 1
                lowest = min(lowest, depth)
        if depth != 0:
            problems.append(f"{path.name}: unbalanced {name} (net {depth:+d})")
        if lowest < 0:
            problems.append(f"{path.name}: {name} closed before opened")
    return problems


# ---------------------------------------------------------------- symbols ---

CALL_RE = re.compile(r"\b([a-z_][a-z0-9_]*)\s*\(")

KNOWN_MACROS = {
    "if", "for", "while", "switch", "return", "sizeof", "defined", "do",
    "else", "static_assert", "offsetof", "alignof", "typeof", "sizeof_field",
}

DEF_RE = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_ \t\*]*?\b([a-z_][a-z0-9_]*)\s*\("
    r"[^;{]*?\)\s*\{",
    re.M,
)

PROTO_RE = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_ \t\*]*?\b([a-z_][a-z0-9_]*)\s*\([^;{]*\)\s*;",
    re.M,
)


def collect_defs_and_protos():
    defs = defaultdict(list)
    protos = defaultdict(list)
    for path in ALL:
        text = strip_noise(path.read_text(encoding="utf-8", errors="replace"))
        for m in DEF_RE.finditer(text):
            defs[m.group(1)].append(path.name)
        for m in PROTO_RE.finditer(text):
            protos[m.group(1)].append(path.name)
    return defs, protos


def check_symbols(defs, protos):
    """Every call to an `av_*` identifier must resolve somewhere."""
    problems = []
    for path in SRC + HDR:
        text = strip_noise(path.read_text(encoding="utf-8", errors="replace"))
        local = set(re.findall(
            r"\b(?:static\s+)?[A-Za-z_][A-Za-z0-9_ \t\*]*?\b([a-z_][a-z0-9_]*)\s*\([^;{]*\)\s*[\{;]",
            text))
        for m in CALL_RE.finditer(text):
            name = m.group(1)
            if name in KNOWN_MACROS or not name.startswith(("av_", "anime_")):
                continue
            if name in local or name in protos:
                continue
            problems.append(f"{path.name}: call to undefined '{name}()'")
    return sorted(set(problems))


def check_duplicate_defs(defs):
    return [f"{name}: defined in {', '.join(files)}"
            for name, files in defs.items() if len(files) > 1]


def check_guards():
    problems = []
    for path in HDR:
        text = path.read_text(encoding="utf-8", errors="replace")
        if "#ifndef" not in text.split("\n\n")[0] and "#pragma once" not in text:
            # guard may appear after the banner comment; search the header top
            head = text[:600]
            if "#ifndef" not in head and "#pragma once" not in head:
                problems.append(f"{path.name}: no include guard found near top")
    return problems


def main() -> int:
    problems = []
    for path in ALL:
        problems += check_balance(path)

    defs, protos = collect_defs_and_protos()
    problems += check_symbols(defs, protos)
    problems += check_duplicate_defs(defs)
    problems += check_guards()

    print(f"scanned {len(ALL)} files in {APP}")
    print(f"  functions defined : {len(defs)}")
    print(f"  prototypes found  : {len(protos)}")
    if not problems:
        print("\nOK - no structural problems found")
        return 0

    print(f"\n{len(problems)} problem(s):")
    for p in problems:
        print("  -", p)
    return 1


if __name__ == "__main__":
    sys.exit(main())
