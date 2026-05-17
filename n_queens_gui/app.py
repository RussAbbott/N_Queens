import tkinter as tk
from tkinter import messagebox
from copy import copy
from ortools.sat.python import cp_model


def solve_n_queens(n, method="backtrack"):
    """
    Find all solutions to the N-Queens problem using backtracking.

    Parameters:
        n: int
            Number of queens (and board size).
        method: str
            "backtrack" to accumulate solutions via explicit undo steps;
            "generator" to find solutions via a Python generator internally.
            The difference between the two methods is about how the search 
            is structured internally, not about when results are delivered 
            to the caller. Both return the complete list of solutions.

    Returns:
        List[List[int]]: list of solutions, each a list of n column indices
        where solution[r] is the column of the queen in row r.
    """
    # queens[r] is the column of the queen in row r — the same role as the
    # decision variable queens[r] in the CP version.
    queens = [-1] * n

    def done(row):
        return row == n

    def is_safe(row, col):
        for r in range(row):
            c = queens[r]
            if c == col or abs(c - col) == abs(r - row):
                return False
        return True

    # Tries every column for the current row; if safe, places a queen and
    # recurses to the next row. On reaching row n a complete solution has been
    # found and a snapshot of queens is appended to solutions. Undoing
    # queens[row] = -1 after the recursive call is the "backtrack" step that
    # lets the loop continue trying other columns.
    def backtrack(row, solutions):
        if done(row):
            # backtrack() accumulates all solutions before returning any.
            solutions.append(copy(queens))
        else:
            for col in range(n):
                if is_safe(row, col):
                    queens[row] = col
                    backtrack(row + 1, solutions)
                    queens[row] = -1
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
            yield copy(queens)
        else:
            for col in range(n):
                if is_safe(row, col):
                    queens[row] = col
                    yield from generate(row + 1)
                    queens[row] = -1

    # generate(0) returns a lazy iterator; list() drives it to completion and
    # collects every yielded board snapshot into solutions all at once.
    # backtrack(0, []) builds and returns the list via its solutions parameter,
    # so both branches simply return their result directly.
    if method == 'backtrack':
        return backtrack(0, [])
    elif method == 'generator':
        return list(generate(0))
    else:
        raise ValueError(f"Unknown method: {method}")


class Queen:
    def __init__(self, domain):
        self.avail_cols = frozenset(domain)

    def constrain(self, col, row_distance):
        # Return a new Queen with col and both diagonals at this row_distance removed.
        return Queen(self.avail_cols - {col, col + row_distance, col - row_distance})


def solve_n_queens_propagation(n):
    """
    Find all solutions to the N-Queens problem using domain propagation.

    Each queen is represented as a Queen object whose avail_cols is pruned
    as columns are assigned. New Queen objects are created on each recursive
    call rather than mutating in place, so backtracking requires no undo step.

    Parameters:
        n: int
            Number of queens (and board size).

    Returns:
        List[List[int]]: list of solutions, each a list of n column indices
        where solution[r] is the column of the queen in row r.
    """
    solutions = []

    def search(row, queens, assignment):
        """
        Given a partial assignment of cols to queens up through row - 1, finds all
        valid completions of the given partial assignment and appends them to solutions.
        The partial assignment is given by the three parameters.

        Parameters:
            row: int;
                the first unassigned row.
                All rows through row - 1 are assigned.

            queens: List[Queen]
                a list of Queen objects. Each queen's avail_cols has been pruned
                to reflect the current partial assignment.
                queens[i] is the Queen object for row i if not yet assigned; it is None
                if row[i] is already assigned.

            assignment: List[int]
                the current partial assignment of columns to queens.
                queens and assignment are parallel lists:
                assignment[i] is -1 if row i is not yet assigned;  it is the
                column assigned for row[i] if already assigned.

                In other words:
                -- queens[:row] are all None.;
                -- assignment[:row] are the columns assigned to those queens;

                -- queens[row] is the Queen being assigned;
                -- assignment[row] is its assignment

                -- queens[row+1:] are the Queens yet to be assigned;
                -- assignment[row+1] are all -1 since they are unassigned.

        Returns: None
            The found solutions are appended to solutions, a nonlocal variable.

        Operation
            Since all cols in queen.avail_cols are currently valid, search iterates
            through all of them. For each col, that column is assigned to the current
            assignment by appending it to the assignment list.
            search() also runs constrain() on the remaining unassigned queens to
            remove col from their avail_cols.

            If constrain() leaves a queen with an empty avail_cols, search() returns
            immediately and backtracks.
            On the other hand, if a queen has remaining avail_cols, search() recurses
            to the next row with the updated partial assignment.

            When row == n, an assignment has been completed. It is appended to solutions.
        """
        if row == n:
            solutions.append(assignment[:])
            return

        # All the values in queens[row].avail_cols are  safe to try as columns.
        for col in queens[row].avail_cols:
            # queens up to but not including queens[row] have been assigned 
            # and are None. They are irrelevant.
            #
            # queens[row] is the queen being assigned; it is set to None
            # in new_queens, since after assignment, it too is irrelevant.
            #
            # queens[row+1:] are the queens yet to be assigned. They must
            # be constrained by the assignment to queens[row]. Even though they
            # are set in new_queens to be pointers to the same Queen objects 
            # in queens, they will be replaced by new Queen objects when 
            # constrain() is run on them.
            new_queens = copy(queens)
            new_queens[row] = None
            for r in range(row + 1, n):
                new_queens[r] = queens[r].constrain(col, r - row)
                if len(new_queens[r].avail_cols) == 0:  # No available cols. Prune immediately
                    break
            else:
                assignment[row] = col
                search(row + 1, new_queens, assignment)

    # Each Queen starts with every column available.
    search(0, [Queen(range(n)) for _ in range(n)], [-1] * n)
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
                      "backtrack", "generator", "cp", "propagation").pack(side="left")

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
