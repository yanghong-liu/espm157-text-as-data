"""Lightweight notebook check: valid nbformat, every code cell parses, no committed credentials."""
import ast, re, sys, pathlib
import nbformat

secret = re.compile(r"""(api_key|token|secret|password|bearer)\s*[=:]\s*["'][A-Za-z0-9_\-\.]{16,}["']|sk-[A-Za-z0-9]{20,}""", re.I)
failures = []
for path in sorted(pathlib.Path(".").glob("*.ipynb")):
    nb = nbformat.read(path, as_version=4)
    nbformat.validate(nb)
    for i, cell in enumerate(nb.cells):
        text = cell.source + "".join(str(o) for o in cell.get("outputs", []))
        if secret.search(text):
            failures.append(f"{path} cell {i}: looks like a hard-coded credential")
        if cell.cell_type == "code":
            source = "\n".join(line for line in cell.source.splitlines() if not line.lstrip().startswith(("%", "!")))
            try:
                ast.parse(source)
            except SyntaxError as error:
                failures.append(f"{path} cell {i}: {error}")
    print(f"{path}: {len(nb.cells)} cells checked")
print("\n".join(failures) or "all checks passed")
sys.exit(bool(failures))
