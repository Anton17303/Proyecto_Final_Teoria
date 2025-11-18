from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class _Line:
    indent: int
    content: str
    is_list_item: bool


_BLOCK = object()


class _SimpleYAMLParser:
    def __init__(self, text: str) -> None:
        self.lines: List[_Line] = self._prepare_lines(text)
        self.index = 0

    @staticmethod
    def _prepare_lines(text: str) -> List[_Line]:
        lines: List[_Line] = []
        for raw in text.splitlines():
            cleaned = _strip_comments(raw)
            if not cleaned.strip() or cleaned.strip() == "---":
                continue
            indent = len(cleaned) - len(cleaned.lstrip(" "))
            content = cleaned[indent:]
            is_list = content.lstrip().startswith("- ")
            if is_list:
                content = content.lstrip()[2:]
            lines.append(_Line(indent=indent, content=content.strip(), is_list_item=is_list))
        return lines

    def parse(self) -> Any:
        if not self.lines:
            return None
        line = self.lines[self.index]
        if line.is_list_item:
            return self._parse_list(line.indent)
        return self._parse_mapping(line.indent)

    def _parse_mapping(self, indent: int) -> dict:
        result = {}
        while self.index < len(self.lines):
            line = self.lines[self.index]
            if line.indent < indent:
                break
            if line.indent > indent:
                raise ValueError("Indentación inválida en el archivo YAML.")
            if line.is_list_item:
                raise ValueError("Se esperaba un mapeo pero se encontró una lista.")
            key, value_token = self._split_key_value(line.content)
            self.index += 1
            if value_token is _BLOCK:
                value = self._parse_nested_block(indent + 2)
            else:
                value = _parse_scalar(value_token)
            result[key] = value
        return result

    def _parse_list(self, indent: int) -> list:
        items = []
        while self.index < len(self.lines):
            line = self.lines[self.index]
            if line.indent < indent or not line.is_list_item:
                break
            if line.indent > indent:
                raise ValueError("Indentación inválida dentro de una lista.")
            self.index += 1
            if not line.content:
                value = self._parse_nested_block(indent + 2)
                items.append(value)
                continue
            if ":" in line.content:
                synthetic = _Line(indent=indent + 2, content=line.content, is_list_item=False)
                self.lines.insert(self.index, synthetic)
                value = self._parse_nested_block(indent + 2)
                items.append(value)
                continue
            items.append(_parse_scalar(line.content))
        return items

    def _parse_nested_block(self, indent: int) -> Any:
        if self.index >= len(self.lines):
            return None
        next_line = self.lines[self.index]
        if next_line.indent < indent:
            return None
        if next_line.is_list_item:
            return self._parse_list(next_line.indent)
        return self._parse_mapping(next_line.indent)

    @staticmethod
    def _split_key_value(content: str) -> tuple[str, Any]:
        if ":" not in content:
            raise ValueError("Cada entrada de un mapeo debe contener ':'")
        key, remainder = content.split(":", 1)
        key = key.strip()
        remainder = remainder.strip()
        if not remainder:
            return key, _BLOCK
        return key, remainder


def _parse_scalar(token: str) -> Any:
    if token in {"null", "Null", "NULL", "~"}:
        return None
    if token in {"true", "True"}:
        return True
    if token in {"false", "False"}:
        return False
    if token.startswith("'") and token.endswith("'"):
        return token[1:-1]
    if token.startswith('"') and token.endswith('"'):
        return token[1:-1]
    if token.startswith("[") and token.endswith("]"):
        inner = token[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part.strip()) for part in inner.split(",")]
    try:
        return int(token)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        pass
    return token


def _strip_comments(line: str) -> str:
    result = []
    in_single = False
    in_double = False
    for char in line:
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            break
        result.append(char)
    return "".join(result).rstrip()


def safe_load(stream: Any) -> Any:
    """Versión reducida de yaml.safe_load."""

    if hasattr(stream, "read"):
        text = stream.read()
    else:
        text = str(stream)
    parser = _SimpleYAMLParser(text)
    return parser.parse()