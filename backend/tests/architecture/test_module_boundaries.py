"""Enforce module dependency rules for models and services."""

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "app"
MODULES = {"platform", "estate", "devices", "twin", "edge", "integration"}
ALLOWED: dict[str, set[str]] = {
    "platform": set(),
    "estate": {"platform"},
    "devices": {"estate", "platform"},
    "twin": {"devices", "estate", "platform"},
    "edge": {"twin", "devices", "estate", "platform"},
    "integration": {"edge", "twin", "devices", "estate", "platform"},
}


def _is_type_checking(node: ast.If) -> bool:
    """Return True when the ``if`` statement guards a ``TYPE_CHECKING`` block."""
    test = node.test
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
    )


def _runtime_imports(tree: ast.AST) -> list[str]:
    """Collect every dotted name imported outside of ``if TYPE_CHECKING:`` blocks."""
    names: list[str] = []

    def visit(node: ast.AST) -> None:
        if isinstance(node, ast.If) and _is_type_checking(node):
            for child in node.orelse:
                visit(child)
            return
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
            names.extend(f"{node.module}.{alias.name}" for alias in node.names)
        for child in ast.iter_child_nodes(node):
            visit(child)

    visit(tree)
    return names


def _target(import_name: str) -> tuple[str, str] | None:
    """Return the ``(layer, module)`` an import points at, or None if it is not module code."""
    parts = import_name.split(".")
    if len(parts) >= 3 and parts[0] == "app" and parts[1] in {"models", "services"}:
        if parts[2] in MODULES:
            return parts[1], parts[2]
    return None


def test_module_imports_respect_dependency_rules() -> None:
    """Models and services may only import the modules the architecture allows."""
    violations: set[str] = set()
    for layer in ("models", "services"):
        for module in MODULES:
            root = APP / layer / module
            if not root.exists():
                continue
            for file in root.rglob("*.py"):
                tree = ast.parse(file.read_text(encoding="utf-8"))
                for name in _runtime_imports(tree):
                    target = _target(name)
                    if target is None or target[1] == module:
                        continue
                    target_layer, target_module = target
                    rel = file.relative_to(APP)
                    if target_layer == "models":
                        violations.add(f"{rel} imports {name} (foreign model)")
                    elif target_module not in ALLOWED[module]:
                        violations.add(f"{rel} imports {name} (module not allowed)")
    assert not violations, "\n".join(sorted(violations))
