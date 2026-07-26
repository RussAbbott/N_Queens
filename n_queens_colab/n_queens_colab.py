# ── Markdown ────────────────────────────────────────────────────────────────
MARKDOWN_CELL = """\
# N-Queens Solver

Click **&emsp;> Run all&emsp;** on the **Commands** line (the third line from the top of this page) after **&emsp;+ Code&emsp;** and **&emsp;+ Text**.

---

**Methods available**
- *In-order, recursion / generator* — assign queens row 0, 1, 2, … in order; \
constraint propagation prunes available columns at each step.
- *MRV, recursion / generator* — Minimum Remaining Values heuristic: \
always assign the queen with the fewest remaining legal columns first, \
detecting dead ends earlier.
- *OR-Tools CP-SAT* — delegates to Google's industrial-strength \
constraint-programming solver (installed automatically on first use).

---

The Github repo is available [here](https://github.com/RussAbbott/N_Queens).
"""


#@title ── N-Queens output ───────────────────────────────────────────────────────────

import ipywidgets as widgets
from IPython.display import display, clear_output
n_queens_output = widgets.Output()
display(n_queens_output)


#@title ── Utilities ─────────────────────────────────────────────────────────────────

def queens_conflict(r1, c1, r2, c2):
    """True if queens at (r1,c1) and (r2,c2) attack each other (same row, col, or diagonal)."""
    return r1 == r2 or c1 == c2 or abs(r1 - r2) == abs(c1 - c2)

def cells_attacked(row, col, n):
    """
    All board cells attacked by a queen at (row, col), excluding its own cell.
    Returns a frozenset of (r, c) pairs covering the queen's row, column, and diagonals.
    """
    attacked = set()
    # Add all cells in the same column and diagonals.
    for r in range(n):
        if r == row:
            continue
        diff = abs(r - row)
        attacked.add((r, col))                             # same column
        if col + diff < n:  attacked.add((r, col + diff))  # diagonal right
        if col - diff >= 0: attacked.add((r, col - diff))  # diagonal left
    # Add all cells in the same row.
    for c in range(n):
        if c != col: 
            attacked.add((row, c))                 # same row
    return frozenset(attacked)


#@title ── Solver 1: Backtracking search with constraint propagation ──────────────────────────────────────────────

def solve_n_queens_propagation(n, method="recursion", strategy="mrv", trace=None):
    """
    Find all solutions to the N-Queens problem using constraint propagation.

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
                     generator is exhausted.
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
        # row:          this Queen's row. Each Queen is responsible for a single row. 
        #               This is required because Queens are kept in sets.
        # avail_cols:   frozenset of columns still to try if backtracked to this queen.
        #               For unassigned queens this is the full remaining domain;
        #               for assigned queens it is the columns after the current one
        #               in sorted order (i.e. what we would try next on backtrack).
        # assigned_col: None until a column is assigned.
        # visited_cols: list of columns tried before the current assignment,
        #               most recently tried first.  Built up as the for-loop in
        #               search_propagation advances through sorted(avail_cols).
        def __init__(self, row, avail_cols=None, assigned_col=None, visited_cols=None):
            self.row = row
            self.avail_cols = avail_cols
            self.assigned_col = assigned_col
            self.visited_cols = visited_cols if visited_cols is not None else []

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
        # Snapshot this node for the trace — skip the empty initial state so the
        # first visible step always has at least one queen placed.
        if trace is not None and assigned_queens:
            trace.append({
                # Each assigned entry: (row, col, avail_cols, visited_cols)
                # avail_cols = cols still to try on backtrack; 
                # visited_cols = tried before col.
                'assigned':   [(q.row, q.assigned_col, q.avail_cols, q.visited_cols)
                               for q in assigned_queens],
                'unassigned': {q.row: q.avail_cols for q in unassigned_queens},
            })
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

            # Sort avail_cols so the iteration order is deterministic and the
            # visited_cols / remaining-cols numbers are meaningful left-to-right.
            sorted_avail = sorted(next_queen.avail_cols)
            loop_tried   = []   # cols tried so far in this loop, most recent first

            for i, col in enumerate(sorted_avail):
                current_visited_cols = loop_tried + next_queen.visited_cols
                remaining            = frozenset(sorted_avail[i + 1:])

                new_unassigned = constrain_all(unassigned_queens - {next_queen},
                                               col,
                                               next_queen.row)
                if new_unassigned is not None:
                    new_queen    = Queen(next_queen.row,
                                         avail_cols=remaining,
                                         assigned_col=col,
                                         visited_cols=current_visited_cols)
                    new_assigned = assigned_queens | {new_queen}
                    yield from search_propagation(new_unassigned, new_assigned)
                elif trace is not None:
                    # Dead end: capture the attempted placement with visited_cols/remaining
                    # so the board can show what has been tried and what remains.
                    attempted = list(assigned_queens) + [
                                Queen(next_queen.row,
                                      avail_cols=remaining,
                                      assigned_col=col,
                                      visited_cols=current_visited_cols)
                    ]
                    partial = {
                        q.row: q.constrain(col, abs(next_queen.row - q.row)).avail_cols
                        for q in unassigned_queens - {next_queen}
                    }
                    trace.append({
                        'assigned':   [(q.row, q.assigned_col, q.avail_cols, q.visited_cols)
                                       for q in attempted],
                        'unassigned': partial,
                        'dead_end':   True,
                    })

                loop_tried = [col] + loop_tried   # prepend — most recent first

    domain = frozenset(range(n))
    yielded_solutions = list(
        search_propagation({Queen(row, avail_cols=domain) for row in domain}, set()))
    return solutions if method == "recursion" else yielded_solutions


# #@title ── Solver 2: OR-Tools CP-SAT ─────────────────────────────────────────────────

# def solve_n_queens_cp(n):
#     """
#     Find all solutions to the N-Queens problem using the OR-Tools CP-SAT solver.
#     OR-Tools is installed automatically on first use if not already present.

#     A problem specification, called a Model, consists of decision variables and
#     constraints. A decision variable is a variable that can take on values from
#     a specified domain. A constraint is a relation among decision variables that
#     must hold.

#     For this problem, n decision variables represent the positions of n queens.
#     These are stored in the list queens, where queens[r] is the column of the
#     queen in row r as in the previous solutions.

#     In this problem, the only constraint type is all_different(List), which
#     requires that all decisions variables in the list assume distinct values.
#     For example, all_different(queens) requires that all the queens be different.

#     Given a problem specification, the solver uses constraint programming
#     techniques to search the solution space for valid assignments.

#     The implementation below is straightforward, but the library offers many
#     knobs to turn for performance tuning.

#     Parameters:
#         n: int
#             Number of queens (and board size).

#     Returns:
#         List[List[int]]: list of solutions, each a list of n column indices
#         where solution[r] is the column of the queen in row r.
#     """
#     from ortools.sat.python import cp_model
#     model = cp_model.CpModel()

#     # Each queens[r] is a decision variable representing the column of the queen
#     # in row r. Its domain is 0..n-1. The string "qr" is a label used in solver
#     # diagnostics.
#     queens = [model.new_int_var(0, n - 1, f"q{r}") for r in range(n)]

#     # No two queens in the same column.
#     model.add_all_different(queens)

#     # No two queens on the same diagonal. Two queens at (r1,c1) and (r2,c2)
#     # share a diagonal when |c1-c2| == |r1-r2|, i.e. when c+r or c-r is equal.
#     # Requiring all col+row values to be distinct blocks one diagonal direction,
#     # and requiring all col-row values to be distinct blocks the other.
#     model.add_all_different([queens[r] + r for r in range(n)])
#     model.add_all_different([queens[r] - r for r in range(n)])

#     solver = cp_model.CpSolver()
#     solutions = []
#     solver.parameters.enumerate_all_solutions = True

#     # CpSolverSolutionCallback is an OR-Tools class whose instances are expected
#     # to implement the on_solution_callback() method--which is called whenever a
#     # solution is found. Such an instance has access to the values of the decision
#     # variables via the value() method. Those values are the found solution, i.e.,
#     # they satisfy the specified constraints.
#     #
#     # Our SolutionCollector is a subclass of CpSolverSolutionCallback. Its
#     # on_solution_callback() method adds each found solution to the list of
#     # solutions.
#     class SolutionCollector(cp_model.CpSolverSolutionCallback):
#         def on_solution_callback(self):
#             solutions.append([self.value(queens[r]) for r in range(n)])

#     solver.solve(model, SolutionCollector())
#     return solutions


#@title ── Solver 2: Lean proof-building ─────────────────────────────────────────────

import random

class SubSol:
    """
    One sub-solution in the Lean proof-building pool.

    An axiom is a single queen with no parents.
    Every other SubSol was produced by merging two compatible parent SubSols.

    positions — frozenset of (row, col): board cells occupied by queens in this sub-solution
    exc       — frozenset of (row, col): all cells attacked by those queens (hence forbidden)
    parent_1  — SubSol | None: first  parent sub-solution (None for axioms)
    parent_2  — SubSol | None: second parent sub-solution (None for axioms)
    """
    def __init__(self, positions: frozenset, exc: frozenset,
                 parent_1=None, parent_2=None):
        self.positions = positions
        self.exc       = exc
        self.parent_1  = parent_1
        self.parent_2  = parent_2

    def can_combine(self, other: 'SubSol') -> bool:
        """True iff no queen in self conflicts with any queen in other."""
        for r1, c1 in self.positions:
            for r2, c2 in other.positions:
                if queens_conflict(r1, c1, r2, c2):
                    return False
        return True

    def merge(self, other: 'SubSol') -> 'SubSol':
        """Return a new SubSol combining self and other, recording both as parents."""
        positions = self.positions | other.positions
        exc       = (self.exc | other.exc) - positions
        return SubSol(positions, exc, parent_1=self, parent_2=other)

    def is_prunable(self, n: int) -> bool:
        """
        True if this sub-solution is a dead end: some free row or free column
        has no safe cell remaining (every intersection is excluded).
        """
        free_rows = [r for r in range(n) if not any(r == row for row, _ in self.positions)]
        free_cols = [c for c in range(n) if not any(c == col for _, col in self.positions)]
        for r in free_rows:
            if all((r, c) in self.exc for c in free_cols): return True
        for c in free_cols:
            if all((r, c) in self.exc for r in free_rows): return True
        return False


def solve_n_queens_lean(n: int, trace: list | None):
    """
    Pool-based Lean-style proof-building solver.

    The pool starts with N² axiom SubSols — one per board cell, each holding
    a single queen position.  At each step we pick two SubSols at random and
    try to merge them.  A merge is accepted when:
      - the two queen-sets are conflict-free (can_combine), and
      - the combined queen-set has not been seen before, and
      - the merged SubSol is not prunable (no row or column is fully blocked).

    Accepted merges are appended to the pool (old sub-solutions are never
    removed), so the pool grows monotonically until a complete n-queen
    SubSol is assembled or progress stalls.

    Each accepted SubSol records its two parents, building a derivation tree
    in memory.  When a solution is found, build_steps() walks that tree
    in post-order and appends one trace step per merge so the UI can replay
    the construction from the first pair up to the complete solution.

    Returns:
        (solution, trace) — solution is list[int] (col per row) or None on failure.
    """
    # Growing list of all SubSols available for combining.
    # The pool is never trimmed — old entries remain as merge candidates.
    pool: list[SubSol] = []

    # Set of position-frozensets already accepted or pruned.
    # Prevents re-exploring the same queen arrangement via different merge paths.
    seen: set[frozenset] = set()

    # ── Axioms ──────────────────────────────────────────────────────────────
    # Seed the pool with N² single-queen SubSols, one per board cell.
    # These are the "atoms" of the proof; they have no parents.
    for row in range(n):
        for col in range(n):
            cell = frozenset({(row, col)})
            exc  = cells_attacked(row, col, n)
            pool.append(SubSol(cell, exc))   # parent_1 = parent_2 = None → axiom
            seen.add(cell)

    # ── Derivation-tree traversal ────────────────────────────────────────────
    def build_steps(root_ss: SubSol) -> list[SubSol]:
        """
        Post-order DFS of the derivation tree rooted at root_ss.

        Returns every non-axiom SubSol in construction order: both parents of a
        node always appear before the node itself.  Axioms (parent_1 is None) are
        leaves and are skipped — they contribute no displayable step.

        Because two different nodes can share a parent (a sub-solution may be merged
        more than once), we deduplicate by object identity with a visited set.
        """
        result:  list[SubSol] = []
        visited: set[int]     = set()

        def dfs(ss: SubSol) -> None:
            if id(ss) in visited:
                return
            visited.add(id(ss))
            if ss.parent_1 is None:
                return               # axiom leaf — no step to record
            dfs(ss.parent_1)
            dfs(ss.parent_2)
            result.append(ss)

        dfs(root_ss)
        return result

    # ── Main merge loop ──────────────────────────────────────────────────────
    stall     = 0
    MAX_STALL = 8000   # give up after this many consecutive failed attempts
    seq       = 0      # monotone counter; each accepted merge gets seq stamped on it

    while stall < MAX_STALL:
        if len(pool) < 2:
            break

        # Pick two SubSols at random; order doesn't matter for merge().
        a, b = random.sample(pool, 2)

        if not a.can_combine(b):
            stall += 1
            continue

        merged_positions: frozenset = a.positions | b.positions
        if merged_positions in seen:
            stall += 1
            continue

        merged: SubSol = a.merge(b)   # links parent_1=a, parent_2=b
        if merged.is_prunable(n):
            seen.add(merged_positions)   # mark dead end so we skip it in future
            stall += 1
            continue

        # Merge accepted: stamp with sequence number, add to pool, reset stall.
        seq += 1
        merged.seq = seq
        seen.add(merged_positions)
        pool.append(merged)
        stall = 0

        if len(merged.positions) == n:
            # ── Solution found ───────────────────────────────────────────────
            sol: list[int] = [0] * n
            for r, c in merged.positions:
                sol[r] = c

            if trace is not None:
                # Build the chronological construction sequence from the derivation tree.
                # steps[0] is the first pair created; steps[-1] is the complete solution.
                steps: list[SubSol] = build_steps(merged)
                total = len(steps)

                # active: non-singleton SubSols that have been created but not yet
                # consumed by a larger merge.  Tracked by object identity.
                active:    list[SubSol] = []
                active_ids: set[int]   = set()

                for step_num, ss in enumerate(steps, start=1):
                    # Consume parents if they were non-singletons in the active set.
                    for parent in (ss.parent_1, ss.parent_2):
                        if id(parent) in active_ids:
                            active_ids.discard(id(parent))
                            active.remove(parent)
                    active.append(ss)
                    active_ids.add(id(ss))

                    # Grayed-out cells = union of exc from the active sub-solutions only.
                    displayed_positions: frozenset = frozenset().union(
                        *(s.positions for s in active))

                    # Pool count: non-singleton solver pool members that existed
                    # at this point in solving (seq <= current step's seq) and are
                    # still compatible with the currently displayed queens.
                    pool_count = sum(
                        1 for s in pool
                        if len(s.positions) >= 2
                        and s.seq <= ss.seq
                        and not any(
                            queens_conflict(r1, c1, r2, c2)
                            for (r1, c1) in s.positions
                            for (r2, c2) in displayed_positions
                            if (r1, c1) != (r2, c2)
                        )
                    )

                    p1_size = len(ss.parent_1.positions)
                    p2_size = len(ss.parent_2.positions)
                    result_size = len(ss.positions)
                    if step_num < total:
                        label = (
                            f'Merge of A ({p1_size}-queen) and B ({p2_size}-queen) '
                            f'→ {result_size}-queen SubSol, verified by:<br>'
                            f'&nbsp;&nbsp;a) A and B are compatible: '
                            f'no position in A attacks any position in B, and vice versa.<br>'
                            f'&nbsp;&nbsp;b) Result = A ∪ B, nonAttacking '
                            f'by the merge lemma.<br>'
                            f'<span style="color:#777">({pool_count} compatible '
                            f'sub-solutions in pool)</span>'
                        )
                    else:
                        label = (
                            f'<b>Solution found!</b>&nbsp; '
                            f'Merge of A ({p1_size}-queen) and B ({p2_size}-queen) '
                            f'→ {result_size}-queen SubSol.<br>'
                            f'&nbsp;&nbsp;a) A and B are compatible: '
                            f'no position in A attacks any position in B, and vice versa.<br>'
                            f'&nbsp;&nbsp;b) Result = A ∪ B — all {result_size} queens '
                            f'placed, nonAttacking by the merge lemma.'
                        )

                    trace.append({
                        'type':     'lean_step',
                        'active':   list(active),   # list[SubSol] currently displayed
                        'step_num': step_num,
                        'total':    total,
                        'n':        n,
                        'label':    label,
                    })

            return sol, trace

    return None, trace


#@title ── Solver 3: OR-Tools CP-SAT ─────────────────────────────────────────────────

def solve_n_queens_cp(n):
    """
    Find all solutions to the N-Queens problem using the OR-Tools CP-SAT solver.
    OR-Tools is installed automatically on first use if not already present.

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
    from ortools.sat.python import cp_model
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


#@title ── Draw the board ───────────────────────────────────────────────────────────────────

import matplotlib.pyplot as plt
import matplotlib.patches as patches

LIGHT_SQ = '#F0D9B5'
DARK_SQ  = '#B58863'
QUEEN_FG = '#1a1a2e'

def draw_board(solution, n, trace_steps=None):
    """
    Draw the chessboard.

    Normal mode (trace_steps is None):
        solution — list of column indices (solution[row] = col), or None for blank.

    Propagation trace mode (trace_steps has 'assigned'/'unassigned' keys):
        'assigned' : list of (row, col, avail_cols, visited_cols) tuples
            col          — current queen position             → ♛
            avail_cols   — cols still to try on backtrack     → green +1, +2, …
            visited_cols — previously tried cols              → blue  -1, -2, …
        Numbers appear only in rows with a placed queen.

    Lean trace mode (trace_steps has type 'lean_step'):
        active — list of SubSol objects currently active (created, not yet consumed).
        Queens within each sub-solution are connected by arcs in row order.
        Each sub-solution gets a distinct arc color.
        Grayed-out cells are those attacked by the active sub-solutions only.
    """
    fig, ax = plt.subplots(figsize=(4, 4))
    fig.patch.set_facecolor('#ecf0f1')

    queen_fs  = max(8, int(280 / n))
    number_fs = max(6, int(130 / n))

    def draw_x(r, c, color, alpha):
        ax.text(c + 0.5, n - 0.5 - r, 'X',
                ha='center', va='center',
                fontsize=number_fs, fontweight='bold',
                color=color, alpha=alpha)

    # Draw all squares first.
    for row in range(n):
        for col in range(n):
            sq_color = LIGHT_SQ if (row + col) % 2 == 0 else DARK_SQ
            ax.add_patch(patches.Rectangle((col, n - 1 - row), 1, 1, color=sq_color))

    if trace_steps is not None and trace_steps.get('type') == 'lean_step':
        # ── Lean step: chronological construction of the solution ────────────
        active = trace_steps['active']   # list[SubSol] currently active

        # Grey overlay: only cells attacked by the active sub-solutions.
        all_excluded = set().union(*(ss.exc for ss in active))
        for r, c in all_excluded:
            ax.add_patch(patches.Rectangle((c, n - 1 - r), 1, 1,
                         facecolor='#555555', alpha=0.35, zorder=2))

        # Each active sub-solution gets a color keyed to its seq number so
        # the same sub-solution keeps the same color across all display steps.
        arc_colors = ['navy', 'darkred', 'darkgreen', 'purple',
                      'darkorange', 'teal', 'saddlebrown', 'indigo']
        for ss in active:
            color = arc_colors[ss.seq % len(arc_colors)]
            sorted_positions = sorted(ss.positions, key=lambda q: q[0])
            # Arc: straight line between consecutive cell centres (c+0.5, n-0.5-r).
            for (r1, c1), (r2, c2) in zip(sorted_positions, sorted_positions[1:]):
                ax.plot([c1 + 0.5, c2 + 0.5], [n - 0.5 - r1, n - 0.5 - r2],
                        color=color, linewidth=2, alpha=0.75, zorder=3)
            for r, c in ss.positions:
                ax.text(c + 0.5, n - 0.5 - r, '♛',
                        ha='center', va='center', fontsize=queen_fs,
                        color=QUEEN_FG, zorder=4)

    elif trace_steps is not None:
        # ── Propagation trace step ───────────────────────────────────────────
        assigned  = trace_steps['assigned']    # [(row, col, avail_cols, visited_cols), ...]
        avail_map = trace_steps['unassigned']  # {row: frozenset}

        # Helper: columns attacked in `target_row` by placed queens
        # via column or diagonal only (no horizontal).
        def col_diag_attacks(target_row):
            attacked = set()
            for q_row, q_col, _, _ in assigned:
                if q_row == target_row:
                    continue
                d = abs(target_row - q_row)
                attacked.add(q_col)
                if 0 <= q_col + d < n: attacked.add(q_col + d)
                if 0 <= q_col - d < n: attacked.add(q_col - d)
            return attacked

        # Red X on eliminated cells in unassigned rows.
        for row, avail_cols in avail_map.items():
            for col in range(n):
                if col not in avail_cols:
                    draw_x(row, col, color='red', alpha=0.55)

        # Red X in assigned rows: column/diagonal attacks from other queens,
        # skipping the queen's own cell and any cell that already has a number.
        for q_row, q_col, avail, visited_cols in assigned:
            number_cells = set(avail) | set(visited_cols)
            for col in col_diag_attacks(q_row):
                if col != q_col and col not in number_cells:
                    draw_x(q_row, col, color='red', alpha=0.55)

        # Queens, future options (+k green), visited cols (-k blue) in assigned rows.
        for q_row, q_col, avail, visited_cols in assigned:
            ax.text(q_col + 0.5, n - 0.5 - q_row, '♛',
                    ha='center', va='center', fontsize=queen_fs, color=QUEEN_FG)
            for k, ac in enumerate(sorted(avail), start=1):
                ax.text(ac + 0.5, n - 0.5 - q_row, f'+{k}',
                        ha='center', va='center', fontsize=number_fs,
                        color='darkgreen')
            for k, jc in enumerate(visited_cols, start=1):
                ax.text(jc + 0.5, n - 0.5 - q_row, f'-{k}',
                        ha='center', va='center', fontsize=number_fs,
                        color='blue')

    elif solution is not None:
        for row in range(n):
            ax.text(solution[row] + 0.5, n - 0.5 - row, '♛',
                    ha='center', va='center', fontsize=queen_fs, color=QUEEN_FG)

    ax.set_xlim(0, n)
    ax.set_ylim(0, n)
    ax.set_aspect('equal')
    ax.axis('off')
    plt.tight_layout()
    plt.show()
    plt.close(fig)


#@title ── Widgets ───────────────────────────────────────────────────────────────────

# On the first run, these widgets are not yet defined. Hence the try/except.
try:
    ctrl_box.children    = ()
    narration_box.children = ()
except NameError:
    pass

n_label = widgets.Label('N:', layout=widgets.Layout(width='22px'))
n_input = widgets.BoundedIntText(
    value=8, min=1, max=20, description='',
    style={'description_width': '0px'},
    layout=widgets.Layout(width='70px'))

method_options = [
    ('In-order, recursion',  'inorder-rec'),
    ('In-order, generator',  'inorder-gen'),
    ('MRV, recursion',       'mrv-rec'),
    ('MRV, generator',       'mrv-gen'),
    ('OR-Tools CP-SAT',      'cp'),
    ('Lean proof-building',  'lean'),
]

method_label = widgets.Label('Method:', layout=widgets.Layout(width='55px', margin='0 0 0 20px'))
method_drop = widgets.Dropdown(
    options=method_options,
    value='inorder-rec',
    description='',
    style={'description_width': '0px'},
    layout=widgets.Layout(width='160px', margin='0 0 0 2px'))

solve_btn = widgets.Button(
    description='Solve', button_style='success',
    layout=widgets.Layout(width='90px'))
trace_btn = widgets.Button(
    description='Solve with Trace', button_style='warning',
    layout=widgets.Layout(width='145px'))
prev_btn  = widgets.Button(
    description='◀ Prev', button_style='',
    layout=widgets.Layout(width='100px'))
next_btn  = widgets.Button(
    description='Next ▶', button_style='',
    layout=widgets.Layout(width='100px'))
status    = widgets.Label(
    value='Enter N and Method, then press Solve or Solve with Trace.',
    layout=widgets.Layout(width='100%'))
board_out = widgets.Output()
narrative = widgets.HTML('', layout=widgets.Layout(width='100%'))

state = {'solutions': [], 'current_pos': 0, 'n': 8, 'is_tracing': False, 'trace_steps': []}

LEAN_DEFS_HTML = (
    '<div style="font-family:monospace;font-size:12px;line-height:1.8;color:#222;'
    'background:#e8f5e9;border:1px solid #aaaaaa;border-radius:6px;'
    'padding:8px 12px;margin:0 0 6px 0;">'
    '<b>Definitions and lemmas used in this proof:</b><br>'
    '<b>position:</b> a (row,&thinsp;col) pair identifying a square on the board.<br>'
    '<b>attack(p,&thinsp;q&thinsp;:&thinsp;positions):</b> p and q share a row, column, or diagonal.<br>'
    '<b>nonAttacking(S&thinsp;:&thinsp;set of positions):</b> no two distinct members of S attack each other.<br>'
    '&nbsp;&nbsp;&nbsp;&nbsp;&forall;&thinsp;p,&thinsp;q&thinsp;&isin;&thinsp;S,&nbsp;'
    'p&thinsp;&ne;&thinsp;q&nbsp;&rarr;&nbsp;&not;attack(p,&thinsp;q)<br>'
    '<b>SubSol (Sub-solution):</b> a set S of positions together with a proof that S is nonAttacking.<br>'
    '<b>Lemma (singleton):</b> For any position p, {p} is nonAttacking. A lone queen attacks nothing.<br>'
    '<b>Lemma (singleton SubSol):</b> For any position p, {p} is a SubSol.<br>'
    '<b>compatible(A,&thinsp;B&thinsp;:&thinsp;SubSols):</b> no member of A attacks any member of B and vice versa.<br>'
    '&nbsp;&nbsp;&nbsp;&nbsp;&forall;&thinsp;p&thinsp;&isin;&thinsp;A,&nbsp;'
    '&forall;&thinsp;q&thinsp;&isin;&thinsp;B,&nbsp;&not;attack(p,&thinsp;q)<br>'
    '<b>Lemma (merge):</b> If A and B are compatible SubSols, then A&thinsp;&cup;&thinsp;B is a SubSol.'
    '</div>'
)
lean_defs_box = widgets.HTML('', layout=widgets.Layout(width='410px', display='none'))


from IPython.display import Javascript, HTML

with board_out:
    clear_output(wait=True)
    draw_board(None, n_input.value)
prev_btn.button_style = ''; prev_btn.add_class('nq-nav-inactive'); prev_btn.add_class('nq-prev')
next_btn.button_style = ''; next_btn.add_class('nq-nav-inactive'); next_btn.add_class('nq-next')
status.value    = 'Enter N and Method values. Then press Solve or Solve with Trace.'
narrative.value = ''

ROW_W    = '329px'   # natural width of the N / Method row
SIDE_W   = '410px'   # right-panel width (narration + defs boxes)
FULL_W   = '830px'   # board (~400px) + gap (20px) + SIDE_W

ctrl_box = widgets.VBox([
    widgets.HBox([n_label, n_input, method_label, method_drop],
                 layout=widgets.Layout(width=ROW_W)),
    widgets.HBox([solve_btn, trace_btn],
                 layout=widgets.Layout(width=ROW_W,
                                       justify_content='space-between')),
], layout=widgets.Layout(width=FULL_W, padding='8px 12px', margin='0 0 6px 0',
                         border_radius='6px', border='1px solid #aaaaaa',
                         align_items='center'))
ctrl_box.add_class('nq-ctrl')

narration_box = widgets.VBox([
    widgets.HBox([prev_btn,
                  widgets.HTML('<div style="text-align:center">'
                               '(or left/right arrow keys)</div>',
                               layout=widgets.Layout(flex='1')),
                  next_btn],
                 layout=widgets.Layout(width='100%')),
    status,
    narrative,
], layout=widgets.Layout(width=SIDE_W, padding='8px 12px', margin='0 0 6px 0',
                         border_radius='6px', border='1px solid #aaaaaa',
                         align_items='center'))
narration_box.add_class('nq-narr')

n_queens_output.clear_output(wait=True)
with n_queens_output:
    # Inject CSS inside the Output widget's context so it reaches the widgets.
    display(HTML("""<style>
    .nq-ctrl { background-color: #d6e8f8 !important; }
    .nq-narr { background-color: #fdf6d0 !important; }
    .nq-ctrl .widget-label, .nq-ctrl .widget-readout,
    .nq-narr .widget-label, .nq-narr .widget-html-content {
        color: #222222 !important;
    }
    button.widget-button.nq-nav-inactive {
        pointer-events: none !important;
        cursor: default !important;
    }
    </style>"""))
    right_panel = widgets.VBox([narration_box, lean_defs_box],
                               layout=widgets.Layout(width=SIDE_W, gap='6px'))
    display(widgets.VBox([ctrl_box,
                          widgets.HBox([board_out, right_panel],
                                       layout=widgets.Layout(
                                           width=FULL_W, gap='20px',
                                           align_items='flex-start'))]))
    # Wire left/right arrow keys to the Prev / Next buttons.
    display(Javascript("""
    function nqKeydown(e) {
        if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
        e.preventDefault();
        var prev = document.querySelector('button.nq-prev');
        var next = document.querySelector('button.nq-next');
        if (e.key === 'ArrowLeft'  && prev) prev.click();
        if (e.key === 'ArrowRight' && next) next.click();
    }
    document.addEventListener('keydown', nqKeydown);
    """))


#@title ── Solve ─────────────────────────────────────────────────────────────────────

def do_solve(is_tracing):
    n      = n_input.value
    method = method_drop.value

    if is_tracing and method == 'cp':
        status.value    = 'Trace not available for OR-Tools — please choose a propagation method.'
        narrative.value = ''
        return
    if is_tracing and n > 6 and method != 'lean':
        status.value    = f'Trace mode: N = {n} may be very large — please set N ≤ 6.'
        narrative.value = ''
        return
    if is_tracing and n > 12 and method == 'lean':
        status.value    = f'Lean trace: N = {n} may be slow — please set N ≤ 12.'
        narrative.value = ''
        return

    trace_steps = []

    if method == 'cp':
        try:
            from ortools.sat.python import cp_model as _  # check availability
        except ImportError:
            status.value    = 'Installing OR-Tools (first use only) …'
            narrative.value = ''
            import subprocess, sys
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'ortools', '-q'],
                           capture_output=True)
        solutions = solve_n_queens_cp(n)
    elif method == 'lean':
        sol, _ = solve_n_queens_lean(n, trace_steps if is_tracing else None)
        solutions = [sol] if sol is not None else []
    else:
        strategy, m = method.split('-')          # e.g. 'mrv-rec' -> 'mrv', 'rec'
        full_method  = 'recursion' if m == 'rec' else 'generator'
        solutions = solve_n_queens_propagation(n, full_method, strategy,
                                               trace=trace_steps if is_tracing else None)

    state.update({'n': n, 'current_pos': 0, 'solutions': solutions,
                  'is_tracing': is_tracing, 'trace_steps': trace_steps})

    if is_tracing and method == 'lean' and trace_steps:
        lean_defs_box.value          = LEAN_DEFS_HTML
        lean_defs_box.layout.display = ''
    else:
        lean_defs_box.value          = ''
        lean_defs_box.layout.display = 'none'

    # Lean trace starts at step 0 (first pair); the user navigates forward to the solution.

    if is_tracing:
        c = state['current_pos']
        status.value    = step_label(c)
        narrative.value = narrative_text(c)
    elif solutions:
        status.value    = f'Solution 1 of {len(solutions)}'
        narrative.value = ''
    else:
        status.value    = f'No solutions for N = {n}'
        narrative.value = ''
    update_nav()
    refresh()

def on_solve(_):       do_solve(False)
def on_trace_solve(_): do_solve(True)

solve_btn._click_handlers.callbacks.clear()
trace_btn._click_handlers.callbacks.clear()
solve_btn.on_click(on_solve)
trace_btn.on_click(on_trace_solve)


#@title ── Explore ──────────────────────────────────────────────────────────────────


def step_label(c):
    """Status label for the current step/solution in either mode."""
    if state['is_tracing']:
        total  = len(state['trace_steps'])
        n_sols = len(state['solutions'])
        ts     = state['trace_steps'][c]
        if ts.get('type') == 'lean_step':
            return f'Step {ts["step_num"]} of {ts["total"]}'
        else:
            # Propagation trace: count fully-assigned non-dead-end steps.
            sols_so_far = sum(1 for t in state['trace_steps'][:c + 1]
                              if not t.get('dead_end') and not t['unassigned'])
        s = '' if n_sols == 1 else 's'
        return f' Step {c + 1} of {total}  ({sols_so_far} of {n_sols} solution{s})'
    else:
        total = len(state['solutions'])
        return f'Solution {c + 1} of {total}'

def narrative_text(c):
    """One-line description of the transition that led to trace step c."""
    if not state['is_tracing'] or not state['trace_steps']:
        return ''
    ts = state['trace_steps'][c]
    if ts.get('type') == 'lean_step':
        return (ts['label'] +
                '<hr style="margin:6px 0;">Definitions are in the box below.')
    curr = {row: col for row, col, _, _ in ts['assigned']}

    if not ts['unassigned'] and not ts.get('dead_end'):
        if c > 0:
            prev_c   = {row: col for row, col, _, _ in state['trace_steps'][c - 1]['assigned']}
            new_rows = set(curr) - set(prev_c)
            if new_rows:
                r = sorted(new_rows)[0]
                return f'Placing a queen in row {r + 1} at column {curr[r] + 1}. Solution found!'
        return 'Solution found!'

    if ts.get('dead_end'):
        prev_rows = (
            {row for row, *_ in state['trace_steps'][c - 1]['assigned']}
            if c > 0 else set()
        )
        new_rows = set(curr) - prev_rows
        r, col = (sorted(new_rows)[0], curr[sorted(new_rows)[0]]) if new_rows \
            else sorted(curr.items())[-1]
        return (f'Placing a queen in row {r + 1} at column {col + 1}.<br>'
                f'Dead end. At least one unassigned row has no safe positions.')

    if c == 0:
        r, col = sorted(curr.items())[0]
        return f'Placing first queen in row {r + 1} at column {col + 1}.'

    prev      = {row: col for row, col, _, _ in state['trace_steps'][c - 1]['assigned']}
    curr_rows = set(curr)
    prev_rows = set(prev)
    new_rows  = curr_rows - prev_rows
    lost_rows = prev_rows - curr_rows

    if new_rows and not lost_rows:
        r = sorted(new_rows)[0]
        return f'Placing a queen in row {r + 1} at column {curr[r] + 1}.'

    if lost_rows:
        changed = {r for r in curr_rows & prev_rows if curr[r] != prev[r]}
        if changed:
            r = sorted(changed)[0]
            return (f'Backtracking to row {r + 1}. '
                    f'Placing a queen at column {curr[r] + 1}, the next safe position.')
        if new_rows:
            r = sorted(new_rows)[0]
            return f'Backtracking — placing a queen in row {r + 1} at column {curr[r] + 1}.'
        rows_str = ', '.join(str(r + 1) for r in sorted(lost_rows))
        s = 's' if len(lost_rows) > 1 else ''
        return f'Backtracking — all options exhausted for row{s} {rows_str}.'

    # Same rows, one queen advanced to its next column at the same depth.
    changed = {r for r in curr_rows if curr.get(r) != prev.get(r)}
    if changed:
        r = sorted(changed)[0]
        return f'Row {r + 1} advances to next available column {curr[r] + 1}.'
    return ''

def refresh():
    with board_out:
        clear_output(wait=True)
        n  = state['n']
        c  = state['current_pos']
        if state['is_tracing'] and state['trace_steps']:
            draw_board(None, n, trace_steps=state['trace_steps'][c])
        else:
            sol = state['solutions']
            draw_board(sol[c] if sol else None, n)

def update_nav():
    c     = state['current_pos']
    total = len(state['trace_steps']) if state['is_tracing'] else len(state['solutions'])
    if c == 0:
        prev_btn.button_style = ''; prev_btn.add_class('nq-nav-inactive')
    else:
        prev_btn.button_style = 'info'; prev_btn.remove_class('nq-nav-inactive')
    if c == total - 1:
        next_btn.button_style = ''; next_btn.add_class('nq-nav-inactive')
    else:
        next_btn.button_style = 'info'; next_btn.remove_class('nq-nav-inactive')

def on_prev(_):
    if state['current_pos'] <= 0:
        return
    state['current_pos'] -= 1
    c = state['current_pos']
    status.value    = step_label(c)
    narrative.value = narrative_text(c)
    refresh()
    update_nav()

def on_next(_):
    total = len(state['trace_steps']) if state['is_tracing'] else len(state['solutions'])
    if state['current_pos'] >= total - 1:
        return
    state['current_pos'] += 1
    c = state['current_pos']
    status.value    = step_label(c)
    narrative.value = narrative_text(c)
    refresh()
    update_nav()

prev_btn._click_handlers.callbacks.clear()
next_btn._click_handlers.callbacks.clear()
prev_btn.on_click(on_prev)
next_btn.on_click(on_next)


#@title ── Resources ────────────────────────────────────────────────────────────────

MARKDOWN_CELL = """\
## Resources

Russ Abbott wrote the solvers; Claude Code wrote the GUI.
"""