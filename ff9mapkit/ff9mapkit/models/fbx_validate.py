"""Offline validator for the emitted FBX-ASCII: a faithful Python port of Memoria's ``FbxAsciiReader``
tokenizer + ``ReadNode`` (``Memoria/Assets/3DModel/FbxAsciiReader.cs``).

Its whole job is to fail EXACTLY where the engine's reader would, so a syntax bug (like a missing node
colon) is caught at export time -- offline -- instead of by a null model + a softlocked field in-game.
``parse(text)`` returns the node tree or raises :class:`FbxParseError` with the same line/column the
engine reports. :func:`validate` adds light structural checks (an Objects + Connections block, at least
one Geometry, a Root bone).
"""
from __future__ import annotations


class FbxParseError(Exception):
    def __init__(self, line, col, msg):
        super().__init__(f"line {line} col {col}: {msg}")
        self.line, self.col = line, col


class _Ident(str):
    """Marks a bare identifier token (vs a quoted string), mirroring the reader's Identifier class."""


class Node:
    __slots__ = ("name", "props", "children")

    def __init__(self, name):
        self.name = name
        self.props = []
        self.children = []


def _is_digit(c: str, first: bool) -> bool:
    if c.isdigit():
        return True
    if c in "-+":
        return True
    if c in ".eEXx":
        return not first
    return False


class _Reader:
    def __init__(self, text: str):
        self.s = text
        self.i = 0
        self.line = 1
        self.col = 1
        self._prev_char = None
        self._prev_single = _SENTINEL
        self._prev_token = _SENTINEL
        self.end = False
        self._was_cr = False

    def _read_char(self):
        if self._prev_char is not None:
            c = self._prev_char
            self._prev_char = None
            return c
        if self.i >= len(self.s):
            self.end = True
            return "\0"
        ch = self.s[self.i]
        self.i += 1
        if ch == "\r":
            self._was_cr = True
            self.line += 1
            self.col = 0
        else:
            if ch == "\n" and not self._was_cr:
                self.line += 1
                self.col = 0
            self._was_cr = False
        self.col += 1
        return ch

    def _read_token_single(self):
        if self._prev_single is not _SENTINEL:
            r = self._prev_single
            self._prev_single = _SENTINEL
            return r
        c = self._read_char()
        if self.end:
            return _EOS
        if c == ";":
            while True:
                d = self._read_char()
                if d in ("\r", "\n") or self.end:
                    break
            return None
        if c in "{}*:,":
            return c
        if c == '"':
            sb = []
            while True:
                c = self._read_char()
                if c == '"':
                    break
                if self.end:
                    raise FbxParseError(self.line, self.col, "Unexpected end of stream; expecting end quote")
                sb.append(c)
            return "".join(sb)
        if c.isspace():
            while True:
                c = self._read_char()
                if not c.isspace() or self.end:
                    break
            if not self.end:
                self._prev_char = c
            return None
        if _is_digit(c, True):
            sb = [c]
            while True:
                c = self._read_char()
                if _is_digit(c, False) and not self.end:
                    sb.append(c)
                else:
                    break
            if not self.end:
                self._prev_char = c
            st = "".join(sb)
            try:
                if "." in st or "e" in st or "E" in st:
                    return float(st)
                return int(st)
            except ValueError:
                raise FbxParseError(self.line, self.col, "Invalid number") from None
        if c.isalpha() or c == "_":
            sb = [c]
            while True:
                c = self._read_char()
                if (c.isalnum() or c == "_") and not self.end:
                    sb.append(c)
                else:
                    break
            if not self.end:
                self._prev_char = c
            return _Ident("".join(sb))
        raise FbxParseError(self.line, self.col, f"Unknown character {c}")

    def read_token(self):
        if self._prev_token is not _SENTINEL:
            r = self._prev_token
            self._prev_token = _SENTINEL
            return r
        while True:
            ret = self._read_token_single()
            if ret is not None:
                break
        if isinstance(ret, _Ident):
            while True:
                colon = self._read_token_single()
                if colon is not None:
                    break
            if colon != ":":
                if len(ret) > 1:
                    raise FbxParseError(self.line, self.col,
                                        f"Unexpected '{colon}', expected ':' or a single-char literal")
                ret2 = ret[0]
                self._prev_single = colon
                return ret2
        return ret

    def _read_array(self):
        length = self.read_token()
        if not isinstance(length, int):
            raise FbxParseError(self.line, self.col, f"Unexpected '{length}', expected an integer")
        self._expect("{")
        self._expect(_Ident("a"))
        vals, expect_comma = [], False
        while True:
            t = self.read_token()
            if t == "}":
                break
            if expect_comma:
                if t != ",":
                    raise FbxParseError(self.line, self.col, f"Unexpected '{t}', expected ','")
                expect_comma = False
                continue
            if not isinstance(t, (int, float)):
                raise FbxParseError(self.line, self.col, f"Unexpected '{t}', expected a number")
            vals.append(t)
            expect_comma = True
        if len(vals) != length:
            raise FbxParseError(self.line, self.col,
                                f"array length {len(vals)} != declared {length}")
        return vals

    def _expect(self, token):
        t = self.read_token()
        # Identifier equality is by string; '{' etc are plain chars
        if isinstance(token, _Ident):
            if not (isinstance(t, _Ident) and str(t) == str(token)):
                raise FbxParseError(self.line, self.col, f"Unexpected '{t}', expected {token}")
        elif t != token:
            raise FbxParseError(self.line, self.col, f"Unexpected '{t}', expected {token}")

    def read_node(self):
        first = self.read_token()
        if not isinstance(first, _Ident):
            if first is _EOS:
                return None
            raise FbxParseError(self.line, self.col, f"Unexpected '{first}', expected an identifier")
        node = Node(str(first))
        expect_comma = False
        token = self.read_token()
        while token != "{" and not isinstance(token, _Ident) and token != "}":
            if expect_comma:
                if token != ",":
                    raise FbxParseError(self.line, self.col, f"Unexpected '{token}', expected a ','")
                expect_comma = False
                token = self.read_token()
                continue
            if token == "*":
                token = self._read_array()
            elif token in ("}", ":", ","):
                raise FbxParseError(self.line, self.col, f"Unexpected '{token}' in property list")
            node.props.append(token)
            expect_comma = True
            token = self.read_token()
        if isinstance(token, _Ident) or token == "}":
            self._prev_token = token
            return node
        # token == '{': read children until matching '}'
        while True:
            end_brace = self.read_token()
            if end_brace == "}":
                break
            self._prev_token = end_brace
            node.children.append(self.read_node())
        return node

    def read(self):
        import re
        # skip whitespace, read optional version comment line
        while True:
            c = self._read_char()
            if not c.isspace() or self.end:
                break
        if c == ";":
            sb = [c]
            while True:
                c = self._read_char()
                if c in ("\r", "\n") or self.end:
                    break
                sb.append(c)
            re.match(r"; FBX (\d)\.(\d)\.(\d) project file", "".join(sb))
        else:
            self._prev_char = c
        nodes = []
        while True:
            n = self.read_node()
            if n is None:
                break
            nodes.append(n)
        return nodes


_SENTINEL = object()


class _Eos:
    def __repr__(self):
        return "end of stream"


_EOS = _Eos()


def parse(text: str) -> list:
    """Parse FBX-ASCII exactly as the engine's FbxAsciiReader would. Raises FbxParseError on any syntax
    error (same line/col the engine reports). Returns the top-level node list."""
    return _Reader(text).read()


def validate(text: str) -> list:
    """Parse + light structural checks (Objects/Connections/Geometry/Root bone). Returns the node list;
    raises FbxParseError / ValueError on a problem."""
    nodes = parse(text)
    top = {n.name: n for n in nodes}
    if "Objects" not in top:
        raise ValueError("no Objects block")
    if "Connections" not in top:
        raise ValueError("no Connections block")
    kinds = [n.name for n in top["Objects"].children if n]
    if "Geometry" not in kinds:
        raise ValueError("no Geometry in Objects")
    roots = [n for n in top["Objects"].children
             if n and n.name == "Model" and len(n.props) >= 3 and n.props[2] == "Root"]
    if not roots:
        raise ValueError("no Root-typed bone Model (FbxSkeleton needs one)")
    return nodes
