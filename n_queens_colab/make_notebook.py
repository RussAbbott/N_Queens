import json

with open('n_queens_colab.py', 'r', encoding='utf-8') as f:
    source = f.read()

notebook = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": (
                "# N-Queens Solver\n\n"
                "Run the cell below. Enter **N** and click **Solve**, "
                "then use **◄ Prev** / **Next ▶** to step through solutions."
            )
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": source
        }
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
