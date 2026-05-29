import json

with open('n_queens_colab.py', 'r', encoding='utf-8') as f:
    source = f.read()

# Split source at section-comment boundaries.
MARKERS = [
    '# ── Solver 1',
    '# ── Solver 2',
    '# ── Drawing',
    '# ── State',
    '# ── Widgets',
    '# ── Callbacks',
]

positions = [source.index(m) for m in MARKERS]

cell_app_output = source[:positions[0]].rstrip()
cell_solver1    = source[positions[0]:positions[1]].rstrip()
cell_solver2    = source[positions[1]:positions[2]].rstrip()
cell_drawing    = source[positions[2]:positions[3]].rstrip()
cell_state      = source[positions[3]:positions[4]].rstrip()
cell_widgets    = source[positions[4]:positions[5]].rstrip()
cell_callbacks  = source[positions[5]:].strip()

def strip_marker(src):
    """Strip the first non-empty line (the # ── marker) from a cell's source."""
    lines = src.split('\n')
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    i += 1  # skip the marker line itself
    return '\n'.join(lines[i:]).lstrip('\n')

def code_cell(src):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": src
    }

def headed_cell(header, src):
    return code_cell(f'{header}\n\n{src}')

MARKDOWN = """\
# N-Queens Solver

Click **Run all** on the third line after "+ Code" and "+ Text.

---

**Methods available**
- *In-order, recursion / generator* — assign queens row 0, 1, 2, … in order; \
domain propagation prunes available columns at each step.
- *MRV, recursion / generator* — Minimum Remaining Values heuristic: \
always assign the queen with the fewest remaining legal columns first, \
detecting dead ends earlier.
- *OR-Tools CP-SAT* — delegates to Google's industrial-strength \
constraint-programming solver (installed automatically on first use).

---

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/RussAbbott/N_Queens/blob/master/n_queens_colab/n_queens_colab.ipynb)

The Github repo is available [here](https://github.com/RussAbbott/N_Queens).\
"""

notebook = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": MARKDOWN
        },
        headed_cell('# Cell 1. N-Queens output',                         cell_app_output),
        headed_cell('# Cell 2. Solver 1: Domain propagation',       strip_marker(cell_solver1)),
        headed_cell('# Cell 3. Solver 2: OR-Tools CP-SAT',          strip_marker(cell_solver2)),
        headed_cell('# Cell 4. Drawing',                            strip_marker(cell_drawing)),
        headed_cell('# Cell 5. State',                              strip_marker(cell_state)),
        headed_cell('# Cell 6. Widgets',                            strip_marker(cell_widgets)),
        headed_cell('# Cell 7. Callbacks',                          strip_marker(cell_callbacks)),
    ],
    "metadata": {
        "colab": {"provenance": []},
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python",
            "version": "3.10.0"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 5
}

with open('n_queens_colab.ipynb', 'w', encoding='utf-8') as f:
    json.dump(notebook, f, indent=1, ensure_ascii=False)

print("Created n_queens_colab.ipynb")
