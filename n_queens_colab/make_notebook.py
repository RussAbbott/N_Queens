import json, re

with open('n_queens_colab.py', 'r', encoding='utf-8') as f:
    source = f.read()

# Discover every  # ── Section name ───  marker and its position.
marker_re = re.compile(r'^#(?:@title)? ── (.+?)─*$', re.MULTILINE)
found     = [(m.group(1).strip(), m.start()) for m in marker_re.finditer(source)]

# Split source into (name, content) pairs.
sections = []
for i, (name, pos) in enumerate(found):
    end = found[i + 1][1] if i + 1 < len(found) else len(source)
    sections.append((name, source[pos:end].rstrip()))


def strip_marker(src):
    """Drop the first non-empty line (the # ── header line)."""
    lines = src.split('\n')
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    return '\n'.join(lines[i + 1:]).lstrip('\n')


def code_cell(src):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": src,
    }


def markdown_cell(src):
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": src,
    }


cells  = []
cell_nbr = 0

for name, content in sections:
    body = strip_marker(content)
    if name == 'Markdown':
        # Extract the content of the MARKDOWN_CELL triple-quoted string.
        m = re.search(r'MARKDOWN_CELL\s*=\s*"""\\\n(.*?)"""', body, re.DOTALL)
        cells.append(markdown_cell(m.group(1).rstrip() if m else body))
    else:
        cell_nbr += 1
        cells.append(code_cell(f'# Cell {cell_nbr}. {name}\n\n{body}'))


notebook = {
    "cells": cells,
    "metadata": {
        "colab": {"provenance": []},
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "version": "3.10.0",
        },
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

with open('n_queens_colab.ipynb', 'w', encoding='utf-8') as f:
    json.dump(notebook, f, indent=1, ensure_ascii=False)

print("Created n_queens_colab.ipynb")
