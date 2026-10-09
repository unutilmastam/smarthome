"""Expand-only migration rule (ADR 0011). Run in CI before every deploy.

    python scripts/check_migrations.py [migrations/versions]

A normal ("expand") migration may only ADD things that the previous release can live
with: new tables, new nullable columns (or NOT NULL with server_default), new indexes.
Destructive changes (drop/rename tables or columns, making a column NOT NULL, dropping
constraints/indexes, raw DROP/RENAME/ALTER SQL) are only allowed in a separate
"contract" migration, marked with a module-level `CONTRACT = True`, released AFTER a
release whose code no longer uses the dropped thing. A contract migration must not
also expand anything, so the two never ship together.
"""

import ast
import re
import sys
from pathlib import Path
from typing import List

DESTRUCTIVE = {"drop_table", "drop_column", "rename_table", "drop_constraint", "drop_index"}
EXPANDING = {"create_table", "add_column", "create_index", "create_unique_constraint",
             "create_foreign_key", "create_check_constraint"}
RAW_SQL_DESTRUCTIVE = re.compile(r"\b(DROP|RENAME|TRUNCATE|DELETE)\b|ALTER\s+TABLE.*\b(DROP|ALTER|RENAME)\b",
                                 re.I | re.S)


def _upgrade(tree: ast.Module):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "upgrade":
            return node
    return None


def _is_contract(tree: ast.Module) -> bool:
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "CONTRACT" for t in node.targets):
            return isinstance(node.value, ast.Constant) and node.value.value is True
    return False


def _kw(call: ast.Call, name: str):
    for k in call.keywords:
        if k.arg == name:
            return k.value
    return None


def check_file(path: Path) -> List[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    up = _upgrade(tree)
    if up is None:
        return [f"{path.name}: no upgrade() function"]
    contract = _is_contract(tree)
    destructive, expanding, problems = [], [], []
    for call in (n for n in ast.walk(up) if isinstance(n, ast.Call)):
        if not isinstance(call.func, ast.Attribute):
            continue
        name = call.func.attr
        line = f"{path.name}:{call.lineno}"
        if name in DESTRUCTIVE:
            destructive.append(f"{line} {name}")
        elif name in EXPANDING:
            expanding.append(f"{line} {name}")
            if name == "add_column":
                col = call.args[-1] if call.args else None
                if isinstance(col, ast.Call):
                    nullable = _kw(col, "nullable")
                    if (isinstance(nullable, ast.Constant) and nullable.value is False
                            and _kw(col, "server_default") is None):
                        problems.append(f"{line} add_column NOT NULL without server_default "
                                        "(the previous release cannot insert rows)")
        elif name == "alter_column":
            if _kw(call, "new_column_name") is not None:
                destructive.append(f"{line} alter_column(new_column_name=...) rename")
            nullable = _kw(call, "nullable")
            if isinstance(nullable, ast.Constant) and nullable.value is False:
                destructive.append(f"{line} alter_column(nullable=False)")
            if _kw(call, "type_") is not None:
                destructive.append(f"{line} alter_column(type_=...)")
        elif name == "execute":
            arg = call.args[0] if call.args else None
            text = arg.value if isinstance(arg, ast.Constant) and isinstance(arg.value, str) else ""
            if not text or RAW_SQL_DESTRUCTIVE.search(text):
                destructive.append(f"{line} op.execute(raw SQL) — destructive or not checkable")
    if contract:
        if expanding:
            problems.append(f"{path.name}: CONTRACT migration must not also expand: {expanding}")
        if not destructive:
            problems.append(f"{path.name}: CONTRACT = True but nothing destructive")
    elif destructive:
        problems += [f"{d} (destructive: put it in a separate CONTRACT migration in a later "
                     "release)" for d in destructive]
    return problems


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    folder = Path(argv[0]) if argv else Path(__file__).resolve().parents[1] / "migrations" / "versions"
    problems = []
    files = sorted(folder.glob("*.py"))
    for f in files:
        problems += check_file(f)
    for p in problems:
        print(p)
    print(f"checked {len(files)} migrations: " + ("OK (expand-only)" if not problems
                                                 else f"{len(problems)} problem(s)"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
