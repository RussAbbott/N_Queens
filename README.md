# N-Queens Solver

Solutions to the classic N-Queens problem — place N queens on an N×N chessboard so no two queens attack each other.

## Live demo (Google Colab)

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/RussAbbott/N_Queens/blob/master/n_queens_colab/n_queens_colab.ipynb)

No installation required — runs entirely in the browser.

## Solving methods

| Method | Description |
|--------|-------------|
| **In-order, recursion** | Assigns queens row 0, 1, 2, … in order; domain propagation prunes available columns at each step |
| **In-order, generator** | Same strategy, solutions yielded one at a time via `yield from` |
| **MRV, recursion** | Minimum Remaining Values heuristic — always picks the queen with fewest legal columns, detecting dead ends earlier |
| **MRV, generator** | Same strategy, generator version |
| **OR-Tools CP-SAT** | Delegates to Google's industrial-strength constraint-programming solver |

## Files

| File | Description |
|------|-------------|
| `n_queens_colab/n_queens_colab.py` | Source for the Colab notebook (ipywidgets + matplotlib UI) |
| `n_queens_colab/make_notebook.py` | Script that splits the source into cells and writes `n_queens_colab.ipynb` |
| `n_queens_colab/n_queens_colab.ipynb` | The generated Jupyter notebook |
| `n_queens_gui/n_queens.py` | Earlier GUI version |
