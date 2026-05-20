import tkinter as tk
from tkinter import messagebox
from copy import copy
from ortools.sat.python import cp_model


def solve_n_queens(n, method="recursion"):
    """
    Find all solutions to the N-Queens problem using either standard recursion 
    or a for/yield-style generator.  

    Parameters:
        n: int
            Number of queens (and board size).
        method: str
            - "recursion" accumulate solutions as a side-effect of exhausting 
              rec_gen(), a generator. Return those collected solutions.
            - "generator" find and yield solutions via rec_gen(). The rec_gen() 
              caller collects and returns the yielded solutions.

            In both cases, the space of possible solutions is explored through 
            the same recursive process.  

    Returns:
        List[List[int]]: a list of solutions, each solution is a list of 
        n column indices, where solution[r] (= solutions[i][r]) is the 
        column of the queen in row r.
    """
    # queens[r] will be the column number of the queen in row r.
    queens = [None] * n

    # In the recursion method, solutions are accumulated in the solutions
    # list as a side effect of exhausting the generator.
    solutions = []

    def is_done(row):
        return row == n

    def is_safe(row, col):
        # Check whether placing a queen at (row, col) is safe given the current
        # partial assignment in queens. We need to check only rows [0 .. row-1],
        # since these are the only rows that have been assigned so far.
        for r in range(row):
            c = queens[r]
            if c == col or abs(c - col) == abs(r - row):
                return False
        return True

    # The function rec_gen(row)() does all the work. Because it includes a yield
    # statement, Python categorizes it as a generator. But it can be used in two ways. 
    # The line "yield from rec_gen(row + 1)" does double duty. 
    #
    # o In recursive mode, rec_gen() fills the pre-defined solutions list as solutions 
    # are found. "yield from rec_gen(row + 1)" is the recursive call. All possibilities 
    # are explored through recursion. The complete list of solutions is returned to the 
    # original caller when rec_gen() terminates.
    #
    # o In generator mode, rec_gen() yields solutions to the original caller as they 
    # are found. "yield from rec_gen(row + 1)" propagates yielded solutions upward. 
    # The original caller accumulates those solutions in its own dynamically
    # constructed list. As above, all possibilities are explored through recursion.
    def rec_gen(row):
        if is_done(row):
            # When using recursion, all solutions are accumulated
            # before any are returned.
            if method == 'recursion':
                solutions.append(copy(queens))
            else: 
                # When using the generator functionality, each solution is yielded 
                # when found. The original caller accumulates them in its own list.
                # The search is still exhaustive, but results could be processed one 
                # at a time if desired.
                yield copy(queens)
        else:
            for col in range(n):
                if is_safe(row, col):
                    queens[row] = col
                    yield from rec_gen(row + 1)

    # solve_n_queens() is called by the UI whenever method is either recursion or 
    # generator.

    # If method is recursion, rec_gen() fills the pre-defined solutions list as a
    # side effect of its execution. solutions is returned when rec_gen() terminates. 
    # 
    # If method is generator, rec_gen() yields solutions as they are found. The code 
    # below uses list() to collect those solutions into a list, which is returned.

    # The complete list of solutions is returned in either case.

    # Step 1. Generate and exhaust the iterator returned by rec_gen(0). 
    # In recursion mode, this has the side effect of building the pre-defined 
    # solutions list.
    # In generator mode, this collects the yielded solutions as yielded_solutions.
    yielded_solutions = list(rec_gen(0))

    # Step 2. Return either solutions or yielded_solutions
    return solutions if method == 'recursion' else yielded_solutions


class Queen:
    def __init__(self, domain, assigned_col=None):
        self.avail_cols = frozenset(domain)
        self.assigned_col = assigned_col

    def assign(self, col):
        # Return a new Queen with col assigned and no remaining available columns.
        return Queen([], col)

    def constrain(self, col, row_distance):
        # Return a new Queen with col and both diagonals at this row_distance removed.
        return Queen(self.avail_cols - {col, col + row_distance, col - row_distance})


def solve_n_queens_propagation(n):
    """
    Find all solutions to the N-Queens problem using domain propagation.

    Each queen is represented as a Queen object whose avail_cols is pruned
    as columns are assigned. New Queen objects are created on each recursive
    call rather than mutating in place, so recursion requires no undo step.

    Parameters:
        n: int
            Number of queens (and board size).

    Returns:
        List[List[int]]: list of solutions, each a list of n column indices
        where solution[r] is the column of the queen in row r.
    """
    solutions = []

    def search(row, queens):
        """
        Given a partial assignment of cols to queens up through row - 1, finds all
        valid completions and appends them to solutions.

        Parameters:
            row: int
                The first unassigned row. All rows through row - 1 are assigned.

            queens: List[Queen]
                queens[r].assigned_col holds the assigned column for r < row.
                queens[row] is the Queen being assigned (avail_cols is non-empty).
                queens[r] for r > row are Queens yet to be assigned, with avail_cols
                pruned to reflect the current partial assignment.

        Returns: None
            Found solutions are appended to solutions, a nonlocal variable.
        """
        if row == n:
            solutions.append([q.assigned_col for q in queens])
            return

        # All the values in queens[row].avail_cols are safe to try as columns.
        for col in queens[row].avail_cols:
            new_queens = copy(queens)
            # Record the assignment in the Queen object itself.
            new_queens[row] = queens[row].assign(col)
            for r in range(row + 1, n):
                new_queens[r] = queens[r].constrain(col, r - row)
                # If no available cols after constraining, prune immediately.
                if len(new_queens[r].avail_cols) == 0:
                    break
            else:
                search(row + 1, new_queens)

    # Each Queen starts with every column available.
    search(0, [Queen(range(n)) for _ in range(n)])
    return solutions


def solve_n_queens_cp(n):
    """
    Find all solutions to the N-Queens problem using the OR-Tools CP-SAT solver.

    Models each row's queen column as an integer decision variable, then adds
    all-different constraints for columns and both diagonal directions.

    Parameters:
        n: int
            Number of queens (and board size).

    Returns:
        List[List[int]]: list of solutions, each a list of n column indices
        where solution[r] is the column of the queen in row r.
    """
    model = cp_model.CpModel()

    # Each queens[r] is a decision variable representing the column of the queen
    # in row r. Its avail_cols is 0..n-1 (any column is initially possible).
    # The string "qr" is just a label used in solver diagnostics.
    queens = [model.new_int_var(0, n - 1, f"q{r}") for r in range(n)]

    # No two queens in the same column.
    model.add_all_different(queens)

    # No two queens on the same diagonal. Two queens at (r1,c1) and (r2,c2)
    # share a diagonal when |c1-c2| == |r1-r2|, i.e. when c+r or c-r is equal.
    # Requiring all col+row values to be distinct blocks one diagonal direction,
    # and requiring all col-row values to be distinct blocks the other.
    model.add_all_different([queens[r] + r for r in range(n)])
    model.add_all_different([queens[r] - r for r in range(n)])

    solver = cp_model.CpSolver()
    solutions = []

    # CpSolverSolutionCallback is an OR-Tools hook: the solver calls
    # on_solution_callback() each time it finds a complete, valid assignment
    # during its internal search. self.value() reads the current variable values
    # at that moment (solver.value() can't be used here — the solve isn't done).
    class SolutionCollector(cp_model.CpSolverSolutionCallback):
        def on_solution_callback(self):
            solutions.append([self.value(queens[r]) for r in range(n)])

    solver.parameters.enumerate_all_solutions = True
    solver.solve(model, SolutionCollector())
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
        self.method_var = tk.StringVar(value="recursion")
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
                      "recursion", "generator", "cp", "propagation").pack(side="left")

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
        method = self.method_var.get()
        if method == "cp":
            self.solutions = solve_n_queens_cp(n)
        elif method == "propagation":
            self.solutions = solve_n_queens_propagation(n)
        else:
            self.solutions = solve_n_queens(n, method)

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
