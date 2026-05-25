try:
    from ortools.sat.python import cp_model
    _ORTOOLS = True
except ImportError:
    _ORTOOLS = False

import ipywidgets as widgets
from IPython.display import display, clear_output
import matplotlib.pyplot as plt
import matplotlib.patches as patches


# ── Solver 1: Domain propagation ──────────────────────────────────────────────

def solve_n_queens_propagation(n, method="recursion", strategy="mrv"):
    """
    Find all solutions to the N-Queens problem using domain propagation.

    Each queen is represented as a Queen object whose avail_cols is pruned
    as columns are assigned. New Queen objects are created on each recursive
    call rather than mutating in place, so no undo step is required.

    Two independent axes of variation are supported:

    strategy — controls which unassigned queen is chosen next:
        "inorder"   pick the queen with the smallest row number, i.e.
                    process rows 0, 1, 2, ... in order.  Domain propagation
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
            # avail_cols is always a frozenset for unassigned queens; the guard
            # below satisfies static analysers that flag the None default.
            return self if self.avail_cols is None else \
                Queen(self.row, self.avail_cols - {col, col + row_dist, col - row_dist})

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

    # search_propagation() is a generator function--it contains yield and
    # yield from. The yield from on the recursive call drives the exhaustive
    # search in both modes.
    #
    # o recursion mode: the base case appends to solutions; yield from recurses.
    #   No solution is ever yielded upward, but the recursive structure is fully
    #   explored as a side effect of exhausting the top-level generator.
    #
    # o generator mode: the base case yields the solution upward; yield from
    #   propagates it all the way to the list() call at the top level.
    def search_propagation(unassigned_queens, assigned_queens):
        if not unassigned_queens:
            # Base case: every queen has been assigned -- record the solution.
            sorted_queens = sorted(assigned_queens, key=lambda q: q.row)
            solution = [q.assigned_col for q in sorted_queens]
            if method == "recursion":
                solutions.append(solution)
            else:
                yield solution
        else:
            # Choose the next queen according to the selected strategy.
            key_fn = (lambda q: q.row) if strategy == "inorder" else \
                     (lambda q: len(q.avail_cols))
            next_queen = min(unassigned_queens, key=key_fn)

            for col in next_queen.avail_cols:
                new_unassigned = constrain_all(unassigned_queens - {next_queen},
                                               col,
                                               next_queen.row)
                if new_unassigned is not None:
                    new_assigned = (assigned_queens |
                                    {Queen(next_queen.row, assigned_col=col)})
                    yield from search_propagation(new_unassigned, new_assigned)

    domain = frozenset(range(n))
    yielded_solutions = list(
        search_propagation({Queen(row, avail_cols=domain) for row in domain}, set()))
    return solutions if method == "recursion" else yielded_solutions


# ── Solver 2: OR-Tools CP-SAT ─────────────────────────────────────────────────

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
    # they satisfy the specified constraints.
    #
    # Our SolutionCollector is a subclass of CpSolverSolutionCallback. Its
    # on_solution_callback() method adds each found solution to the list of
    # solutions.
    class SolutionCollector(cp_model.CpSolverSolutionCallback):
        def on_solution_callback(self):
            solutions.append([self.value(queens[r]) for r in range(n)])

    solver.solve(model, SolutionCollector())
    return solutions


# ── Drawing ───────────────────────────────────────────────────────────────────

LIGHT_SQ = '#F0D9B5'
DARK_SQ  = '#B58863'
QUEEN_FG = '#1a1a2e'

def draw_board(solution, n):
    fig, ax = plt.subplots(figsize=(5, 5))
    fig.patch.set_facecolor('#ecf0f1')
    for row in range(n):
        for col in range(n):
            color = LIGHT_SQ if (row + col) % 2 == 0 else DARK_SQ
            ax.add_patch(patches.Rectangle((col, n - 1 - row), 1, 1, color=color))
            if solution is not None and solution[row] == col:
                ax.text(col + 0.5, n - 0.5 - row, '♛',
                        ha='center', va='center',
                        fontsize=max(8, int(280 / n)),
                        color=QUEEN_FG)
    ax.set_xlim(0, n)
    ax.set_ylim(0, n)
    ax.set_aspect('equal')
    ax.axis('off')
    plt.tight_layout()
    plt.show()
    plt.close(fig)


# ── State ─────────────────────────────────────────────────────────────────────

state = {'solutions': [], 'current': 0, 'n': 8}


# ── Widgets ───────────────────────────────────────────────────────────────────

n_input = widgets.BoundedIntText(
    value=8, min=1, max=20, description='N:',
    layout=widgets.Layout(width='120px'))

_method_options = [
    ('In-order, recursion',  'inorder-rec'),
    ('In-order, generator',  'inorder-gen'),
    ('MRV, recursion',       'mrv-rec'),
    ('MRV, generator',       'mrv-gen'),
]
if _ORTOOLS:
    _method_options.append(('OR-Tools CP-SAT', 'cp'))

method_drop = widgets.Dropdown(
    options=_method_options,
    value='mrv-rec',
    description='Method:',
    layout=widgets.Layout(width='260px'))

solve_btn = widgets.Button(
    description='Solve', button_style='success',
    layout=widgets.Layout(width='90px'))
prev_btn  = widgets.Button(
    description='◀ Prev', button_style='info',
    disabled=True, layout=widgets.Layout(width='100px'))
next_btn  = widgets.Button(
    description='Next ▶', button_style='info',
    disabled=True, layout=widgets.Layout(width='100px'))
status    = widgets.Label(
    value='Enter N and press Solve',
    layout=widgets.Layout(width='250px'))
board_out = widgets.Output()


# ── Callbacks ─────────────────────────────────────────────────────────────────

def refresh():
    with board_out:
        clear_output(wait=True)
        sol = state['solutions']
        draw_board(sol[state['current']] if sol else None, state['n'])

def update_nav():
    c, total = state['current'], len(state['solutions'])
    prev_btn.disabled = c == 0
    next_btn.disabled = c == total - 1

def on_solve(_):
    n      = n_input.value
    method = method_drop.value
    if method == 'cp':
        solutions = solve_n_queens_cp(n)
    else:
        strategy, m = method.split('-')          # e.g. 'mrv-rec' -> 'mrv', 'rec'
        full_method  = 'recursion' if m == 'rec' else 'generator'
        solutions = solve_n_queens_propagation(n, full_method, strategy)
    state.update({'n': n, 'current': 0, 'solutions': solutions})
    total = len(solutions)
    if total:
        status.value = f'Solution 1 of {total}'
        prev_btn.disabled = True
        next_btn.disabled = total == 1
    else:
        status.value = f'No solutions for N = {n}'
        prev_btn.disabled = True
        next_btn.disabled = True
    refresh()

def on_prev(_):
    state['current'] -= 1
    c, total = state['current'], len(state['solutions'])
    status.value = f'Solution {c + 1} of {total}'
    update_nav()
    refresh()

def on_next(_):
    state['current'] += 1
    c, total = state['current'], len(state['solutions'])
    status.value = f'Solution {c + 1} of {total}'
    update_nav()
    refresh()

solve_btn.on_click(on_solve)
prev_btn.on_click(on_prev)
next_btn.on_click(on_next)

def show():
    display(widgets.VBox([
        widgets.HBox([n_input, method_drop, solve_btn]),
        board_out,
        widgets.HBox([prev_btn, status, next_btn])
    ]))
    with board_out:
        draw_board(None, state['n'])


# ── Layout ────────────────────────────────────────────────────────────────────

show()
