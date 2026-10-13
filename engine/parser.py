
import ast
from pathlib import Path


def module_name(file_path, root):
    relative = file_path.relative_to(root).with_suffix("")
    parts = list(relative.parts)

    if parts[-1] == "__init__":
        parts.pop()

    return ".".join(parts)


def get_call_name(node):
    """Return a call name such as 'checkout' or 'pricing.calculate_total'."""
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = get_call_name(node.value)
        return f"{parent}.{node.attr}" if parent else None

    return None


def collect_calls(function_node):
    """Collect calls without attributing nested function bodies to their parent."""
    calls = []

    def visit(node):
        if node is not function_node and isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)
        ):
            return

        if isinstance(node, ast.Call):
            name = get_call_name(node.func)
            if name:
                calls.append(name)

        for child in ast.iter_child_nodes(node):
            visit(child)

    for statement in function_node.body:
        visit(statement)

    return sorted(set(calls))


def parse_python_project(project_root):
    root = Path(project_root).resolve()
    functions = {}

    ignored_directories = {
        ".venv", "venv", "__pycache__", ".git", ".pytest_cache"
    }

    for file_path in sorted(root.rglob("*.py")):
        if any(part in ignored_directories for part in file_path.parts):
            continue

        module = module_name(file_path, root)
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))

        imports = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    if alias.name != "*":
                        local_name = alias.asname or alias.name
                        imports[local_name] = f"{node.module}.{alias.name}"

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    local_name = alias.asname or alias.name.split(".")[0]
                    imported_module = alias.name if alias.asname else local_name
                    imports[local_name] = imported_module

        # Only collect module-level functions. Nested functions are not
        # separate top-level graph nodes in this initial version.
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            qualified_name = f"{module}.{node.name}"

            functions[qualified_name] = {
                "name": node.name,
                "qualified_name": qualified_name,
                "module": module,
                "line": node.lineno,
                "end_line": node.end_lineno or node.lineno,
                "calls": collect_calls(node),
                "imports": imports.copy(),
                "file": str(file_path),
            }

    return functions
