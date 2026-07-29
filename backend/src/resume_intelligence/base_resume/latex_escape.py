"""LaTeX special-character escaping for candidate-provided text."""

_SPECIAL_CHARS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def latex_escape(text: str) -> str:
    """Escapes LaTeX special characters in plain candidate text (not URLs or macros)."""
    if not text:
        return ""
    # Backslash must be replaced first so we don't double-escape the replacements below.
    out = text.replace("\\", "\x00")
    for char, repl in _SPECIAL_CHARS.items():
        if char == "\\":
            continue
        out = out.replace(char, repl)
    return out.replace("\x00", r"\textbackslash{}")
