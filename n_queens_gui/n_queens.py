from ortools.sat.python import cp_model
import tkinter as tk
from tkinter import messagebox


#  ---------------------------------------------------------------------------------
# SECTION: solve_n_queens using domain propagation.

def solve_n_queens_propagation(n, method="recursion", strategy="mrv"):
    """
    Find all solutions to the N-Queens problem using domain propagation.

    Each queen is represented as a Queen object whose avail_cols is pruned
    as columns are assigned. New Queen objects are created on each recursive
    call rather than mutating in place, so no undo step is required.

    Two independent axes of variation are supported:

    strategy — controls which unassigned queen is chosen next:
        "inorder"   pick the queen with the smallest row number, i.e.
                    process rows 0, 1, 2, … in order.  Domain propagation
                    still prunes future queens' available columns at every
                    step, so this is strictly better than a plain safety
                    check at assignment time.
        "mrv"       pick the queen with the fewest remaining available
                    columns (Minimum Remaining Values heuristic).  This
                    tends to detect dead ends earlier and reduces the
                    search tree further.

    method — controls how solutions are collected:
        "recursion"  solutions are accumulated as a side effect in the
                     pre-defined solutions list and returned when the
                     generator is fully exhausted.
        "generator"  each solution is yielded as it is found and
                     propagated upward via yield from; the caller
                     collects them with list().

    Parameters:
        n: int
            Number of queens (and board size).
        method: str
            "recursion" or "generator" (default "recursion").
        strategy: str
            "inorder" or "mrv" (default "mrv").

    Returns:
        List[List[int]]: list of solutions, each a list of n column indices
        where solution[r] is the column of the queen in row r.
    """
    class Queen:
        # Since Queens are kept in sets, each needs a row variable to identify it.
        # avail_cols is a frozenset of available columns, or None if assigned.
        # assigned_col is None until a column is assigned.
        def __init__(self, row, avail_cols=None, assigned_col=None):
            self.row = row
            self.avail_cols = avail_cols
            self.assigned_col = assigned_col

        def constrain(self, col, row_dist):
            # Return a new Queen with col and both diagonals at row_dist removed.
            return Queen(self.row, self.avail_cols - {col, col + row_dist, col - row_dist})

    def constrain_all(queens, col, pivot_row):
        # Apply col assignment to all queens, returning None on the first failure.
        constrained_queens = set()
        for q in queens:
            constrained = q.constrain(col, abs(pivot_row - q.row))
            if not constrained.avail_cols:
                return None
            constrained_queens.add(constrained)
        return constrained_queens

    # In recursion mode, solutions are accumulated here as a side effect.
    solutions = []

    # search_propagation() is a generator function (it contains yield/yield from).
    # The yield from on the recursive call drives the exhaustive search in both modes.
    #
    # o recursion mode: the base case appends to solutions; yield from recurses.
    #   No solution is ever yielded upward, but the recursive structure is fully
    #   explored as a side effect of exhausting the top-level generator.
    #
    # o generator mode: the base case yields the solution upward; yield from
    #   propagates it all the way to the list() call at the top level.
    def search_propagation(unassigned_queens, assigned_queens):
        if not unassigned_queens:
            # Base case: every queen has been assigned — record the solution.
            sorted_queens = sorted(assigned_queens, key=lambda q: q.row)
            solution = [q.assigned_col for q in sorted_queens]
            if method == "recursion":
                solutions.append(solution)
            else:
                yield solution
        else:
            # Choose the next queen according to the selected strategy.
            if strategy == "inorder":
                next_queen = min(unassigned_queens, key=lambda q: q.row)
            else:  # "mrv": pick the queen with the fewest remaining columns
                next_queen = min(unassigned_queens, key=lambda q: len(q.avail_cols))
            for col in next_queen.avail_cols:
                new_unassigned = constrain_all(
                    unassigned_queens - {next_queen},
                    col, next_queen.row)
                if new_unassigned is not None:
                    new_assigned = assigned_queens | {
                        Queen(next_queen.row, assigned_col=col)}
                    yield from search_propagation(new_unassigned, new_assigned)

    domain = frozenset(range(n))
    yielded_solutions = list(
        search_propagation({Queen(row, avail_cols=domain) for row in domain}, set()))
    return solutions if method == "recursion" else yielded_solutions

# END: solve_n_queens using domain propagation with the MRV heuristic.
# ---------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------
# SECTION: solve_n_queens using the OR-Tools CP-SAT solver.

def solve_n_queens_cp(n):
    """
    Find all solutions to the N-Queens problem using the OR-Tools CP-SAT solver.

    A problem specification, called a Model, consists of decision variables and 
    constraints. A decision variable is a variable that can take on values from 
    a specified domain. A constraint is a relation among decision variables that 
    must hold.
    
    For this problem, n decision variables represent the positions of n queens.
    These are stored in the list queens, where queens[r] is the column of the 
    queen in row r as in the previous solutions.
    
    In this problem, the only constraint type is all_different(List), which
    requires that all decisions variables in the list assume distinct values.
    For example, all_different(queens) requires that all the queens be different.
    
    Given a problem specification, the solver uses constraint programming 
    techniques to search the solution space for valid assignments.
   
    The implementation below is straightforward, but the library offers many 
    knobs to turn for performance tuning.

    Parameters:
        n: int
            Number of queens (and board size).

    Returns:
        List[List[int]]: list of solutions, each a list of n column indices
        where solution[r] is the column of the queen in row r.
    """
    model = cp_model.CpModel()

    # Each queens[r] is a decision variable representing the column of the queen
    # in row r. Its domain is 0..n-1. The string "qr" is a label used in solver 
    # diagnostics.
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
    solver.parameters.enumerate_all_solutions = True

    # CpSolverSolutionCallback is an OR-Tools class whose instances are expected
    # to implement the on_solution_callback() method--which is called whenever a
    # solution is found. Such an instance has access to the values of the decision 
    # variables via the value() method. Those values are the found solution, i.e., 
    # they satisfy the specified  constraints. 
    # 
    # Our SolutionCollector is a subclass of CpSolverSolutionCallback. Its
    # on_solution_callback() method adds each found solution to the list of 
    # solutions.
    class SolutionCollector(cp_model.CpSolverSolutionCallback):
        def on_solution_callback(self):
            solutions.append([self.value(queens[r]) for r in range(n)])

    solver.solve(model, SolutionCollector())
    return solutions

# END: solve_n_queens using the OR-Tools CP-SAT solver.
# ---------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------
# SECTION: IO/tcl code for the N-Queens application. 
# This code is independent of the solution method.

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
        self.method_var = tk.StringVar(value="inorder-rec")
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
        method_menu = tk.OptionMenu(controls, self.method_var,
                                    "inorder-rec", "inorder-gen",
                                    "mrv-rec", "mrv-gen",
                                    "cp")
        method_menu["menu"].insert_separator(2)  # after inorder-gen
        method_menu["menu"].insert_separator(5)  # after mrv-gen
        method_menu.pack(side="left")

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
        else:
            strategy, m = method.split("-")   # e.g. "inorder-rec" → "inorder", "rec"
            full_method  = "recursion" if m == "rec" else "generator"
            self.solutions = solve_n_queens_propagation(n, full_method, strategy)

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
