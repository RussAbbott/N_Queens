import tkinter as tk
from tkinter import messagebox
from copy import copy


def solve_n_queens(n, method="backtrack"):
    board = [-1] * n

    def done(row):
        return row == n

    def is_safe(row, col):
        for r in range(row):
            c = board[r]
            if c == col or abs(c - col) == abs(r - row):
                return False
        return True

    # Tries every column for the current row; if safe, places a queen and
    # recurses to the next row. On reaching row n a complete solution has been
    # found and a snapshot of board is appended to solutions. Undoing
    # board[row] = -1 after the recursive call is the "backtrack" step that
    # lets the loop continue trying other columns.
    def backtrack(row, solutions):
        if done(row):
            # backtrack() accumulates all solutions before returning any.
            solutions.append(copy(board))
        else:
            for col in range(n):
                if is_safe(row, col):
                    board[row] = col
                    backtrack(row + 1, solutions)
                    board[row] = -1
        return solutions

    # Same logic as backtrack, but instead of appending to an external list
    # it yields each solution directly to the caller. The presence of yield
    # makes this a generator function: calling generate(row) returns a lazy
    # iterator rather than running any code immediately. yield from delegates
    # to the recursive sub-iterator, propagating each yielded value up the
    # call stack without buffering.
    def generate(row):
        if done(row):
            # generate() yields each solution as it is found.
            yield copy(board)
        else:
            for col in range(n):
                if is_safe(row, col):
                    board[row] = col
                    yield from generate(row + 1)
                    board[row] = -1

    # generate(0) returns a lazy iterator; list() drives it to completion and
    # collects every yielded board snapshot into solutions all at once.
    # backtrack(0, []) builds and returns the list via its solutions parameter,
    # so both branches simply return their result directly.
    solutions = backtrack(0, []) if method == 'backtrack' else list(generate(0))
    return solutions


class NQueensApp(tk.Tk):
    LIGHT_SQ = "#F0D9B5"
    DARK_SQ  = "#B58863"
    QUEEN_FG = "#1a1a2e"
    BG       = "#ecf0f1"
    HEADER   = "#2c3e50"

    def __init__(self):
        super().__init__()
        self.title("N-Queens Solver")
        self.resizable(False, False)
        self.configure(bg=self.BG)
        self.solutions  = []
        self.current    = 0
        self._n         = 8
        self.method_var = tk.StringVar(value="backtrack")
        self._build_ui()
        self._draw_board_only(8)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()
        self._build_canvas()
        self._build_nav()

    def _build_header(self):
        bar = tk.Frame(self, bg=self.HEADER, padx=16, pady=12)
        bar.pack(fill="x")

        tk.Label(bar, text="N-Queens Solver",
                 font=("Helvetica", 16, "bold"),
                 bg=self.HEADER, fg="white").pack(side="left")

        controls = tk.Frame(bar, bg=self.HEADER)
        controls.pack(side="right")

        tk.Label(controls, text="N =",
                 font=("Helvetica", 13),
                 bg=self.HEADER, fg="white").pack(side="left", padx=(0, 6))

        self.n_var = tk.StringVar(value="8")
        entry = tk.Entry(controls, textvariable=self.n_var,
                         width=4, font=("Helvetica", 13), justify="center")
        entry.pack(side="left", padx=(0, 10))
        entry.bind("<Return>", lambda _: self._solve())

        tk.Button(controls, text="Solve",
                  font=("Helvetica", 12, "bold"),
                  bg="#27ae60", fg="white", relief="flat",
                  padx=14, cursor="hand2",
                  command=self._solve).pack(side="left")

        tk.Label(controls, text="  Method:",
                 font=("Helvetica", 11),
                 bg=self.HEADER, fg="white").pack(side="left", padx=(12, 4))
        tk.OptionMenu(controls, self.method_var,
                      "backtrack", "generator").pack(side="left")

    def _build_canvas(self):
        outer = tk.Frame(self, bg=self.BG)
        outer.pack(padx=24, pady=20)

        self.canvas = tk.Canvas(outer, bg=self.BG, highlightthickness=0)
        self.canvas.pack()

    def _build_nav(self):
        bar = tk.Frame(self, bg=self.BG, pady=10)
        bar.pack(fill="x")

        self.prev_btn = tk.Button(
            bar, text="◀  Prev",
            font=("Helvetica", 11), bg="#3498db", fg="white",
            relief="flat", padx=14, cursor="hand2", state="disabled",
            command=self._prev)
        self.prev_btn.pack(side="left", padx=(20, 8))

        self.status = tk.Label(bar, text="Enter N and press Solve",
                               font=("Helvetica", 11),
                               bg=self.BG, fg="#555")
        self.status.pack(side="left", expand=True)

        self.next_btn = tk.Button(
            bar, text="Next  ▶",
            font=("Helvetica", 11), bg="#3498db", fg="white",
            relief="flat", padx=14, cursor="hand2", state="disabled",
            command=self._next)
        self.next_btn.pack(side="right", padx=(8, 20))

    # ── Drawing ───────────────────────────────────────────────────────────────

    def _cell_size(self, n):
        return max(38, min(80, 560 // n))

    def _draw_board_only(self, n):
        cell = self._cell_size(n)
        self.canvas.config(width=cell * n, height=cell * n)
        self.canvas.delete("all")
        for row in range(n):
            for col in range(n):
                x0, y0 = col * cell, row * cell
                fill = self.LIGHT_SQ if (row + col) % 2 == 0 else self.DARK_SQ
                self.canvas.create_rectangle(
                    x0, y0, x0 + cell, y0 + cell,
                    fill=fill, outline="")

    def _draw_board_with_queens(self, solution, n):
        cell = self._cell_size(n)
        self.canvas.config(width=cell * n, height=cell * n)
        self.canvas.delete("all")
        font_size = max(12, int(cell * 0.62))
        for row in range(n):
            for col in range(n):
                x0, y0 = col * cell, row * cell
                fill = self.LIGHT_SQ if (row + col) % 2 == 0 else self.DARK_SQ
                self.canvas.create_rectangle(
                    x0, y0, x0 + cell, y0 + cell,
                    fill=fill, outline="")
                if solution[row] == col:
                    self.canvas.create_text(
                        x0 + cell // 2, y0 + cell // 2,
                        text="♛", font=("Helvetica", font_size),
                        fill=self.QUEEN_FG)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _solve(self):
        try:
            n = int(self.n_var.get())
            if n < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid input",
                                 "Please enter a positive integer.")
            return

        self._n        = n
        self.current   = 0
        self.solutions = solve_n_queens(n, self.method_var.get())

        if not self.solutions:
            self._draw_board_only(n)
            self.status.config(text=f"No solutions exist for N = {n}")
            self.prev_btn.config(state="disabled")
            self.next_btn.config(state="disabled")
            return

        self._draw_board_with_queens(self.solutions[0], n)
        self._refresh_nav()

    def _prev(self):
        self.current -= 1
        self._draw_board_with_queens(self.solutions[self.current], self._n)
        self._refresh_nav()

    def _next(self):
        self.current += 1
        self._draw_board_with_queens(self.solutions[self.current], self._n)
        self._refresh_nav()

    def _refresh_nav(self):
        total = len(self.solutions)
        self.status.config(text=f"Solution {self.current + 1} of {total}")
        self.prev_btn.config(state="normal" if self.current > 0       else "disabled")
        self.next_btn.config(state="normal" if self.current < total-1 else "disabled")


if __name__ == "__main__":
    NQueensApp().mainloop()
