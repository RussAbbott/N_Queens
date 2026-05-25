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
    '# ── Layout',
]

positions = [source.index(m) for m in MARKERS]

cell_imports   = source[:positions[0]].rstrip()
cell_solver1   = source[positions[0]:positions[1]].rstrip()
cell_solver2   = source[positions[1]:positions[2]].rstrip()
cell_drawing   = source[positions[2]:positions[3]].rstrip()
cell_state     = source[positions[3]:positions[4]].rstrip()
cell_widgets   = source[positions[4]:positions[5]].rstrip()
cell_callbacks = source[positions[5]:positions[6]].rstrip()
cell_layout    = source[positions[6]:].strip()

pip_and_imports = (
    '!pip install ortools "protobuf>=3.20.2,<6.0.0" -q\n\n'
    + cell_imports
)

def code_cell(src):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": src
    }

MARKDOWN = """\
# N-Queens Solver

## First time (or after a Colab disconnect)
1. Click the **pip-install cell** (the second cell below).
2. From the **Runtime** menu choose **Run this cell and below**. \
A red squiggly line will appear under `show` in the **Layout cell** (the first cell below) — you can ignore it.
3. Click the **Layout cell**. Click the white circle with the forward-pointing triangle \
(upper-left corner) to run the app.

## Subsequent runs
Just run the **Layout cell** (the first cell below).

---

**Methods available**
- *In-order, recursion / generator* — assign queens row 0, 1, 2, … in order; \
domain propagation prunes available columns at each step.
- *MRV, recursion / generator* — Minimum Remaining Values heuristic: \
always assign the queen with the fewest remaining legal columns first, \
detecting dead ends earlier.
- *OR-Tools CP-SAT* — delegates to Google's industrial-strength \
constraint-programming solver.\
"""

notebook = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": MARKDOWN
        },
        code_cell(cell_layout),       # Cell 1 — Layout (top, easy to re-run)
        code_cell(pip_and_imports),   # Cell 2 — pip install + imports
        code_cell(cell_solver1),      # Cell 3 — Solver 1: domain propagation
        code_cell(cell_solver2),      # Cell 4 — Solver 2: OR-Tools CP-SAT
        code_cell(cell_drawing),      # Cell 5 — Drawing
        code_cell(cell_state),        # Cell 6 — State
        code_cell(cell_widgets),      # Cell 7 — Widgets
        code_cell(cell_callbacks),    # Cell 8 — Callbacks
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

with open('n_queens.ipynb', 'w', encoding='utf-8') as f:
    json.dump(notebook, f, indent=1, ensure_ascii=False)

print("Created n_queens.ipynb")
