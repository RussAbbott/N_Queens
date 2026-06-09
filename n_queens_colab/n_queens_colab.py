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
                remaining       = frozenset(sorted_avail[i + 1:])

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


#@title ── Solver 2: OR-Tools CP-SAT ─────────────────────────────────────────────────

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

    Trace mode (trace_steps is a dict):
        'assigned' : list of (row, col, avail_cols, visited_cols) tuples
            col       — current queen position        → ♛
            avail_cols — frozenset of cols still to try on backtrack
                         → green +1, +2, … in sorted(avail_cols) order
            visited_cols   — list of previously tried cols, most recent first
                         → red  -1, -2, … in order

        Numbers appear only in rows with a placed queen.
        Unassigned rows show a plain board square.
    """
    fig, ax = plt.subplots(figsize=(5, 5))
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

    if trace_steps is not None:
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
    layout=widgets.Layout(width='440px'))
board_out = widgets.Output()
narrative = widgets.HTML('', layout=widgets.Layout(width='440px'))

state = {'solutions': [], 'current_pos': 0, 'n': 8, 'is_tracing': False, 'trace_steps': []}


from IPython.display import Javascript, HTML

with board_out:
    clear_output(wait=True)
    draw_board(None, n_input.value)
prev_btn.button_style = ''; prev_btn.add_class('nq-nav-inactive'); prev_btn.add_class('nq-prev')
next_btn.button_style = ''; next_btn.add_class('nq-nav-inactive'); next_btn.add_class('nq-next')
status.value    = 'Enter N and Method values. Then press Solve or Solve with Trace.'
narrative.value = ''

ROW_W    = '329px'   # natural width of the N / Method row
box_style = dict(width='490px', padding='8px 12px', margin='0 0 6px 0',
                 border_radius='6px', border='1px solid #aaaaaa',
                 align_items='center')

ctrl_box = widgets.VBox([
    widgets.HBox([n_label, n_input, method_label, method_drop],
                 layout=widgets.Layout(width=ROW_W)),
    widgets.HBox([solve_btn, trace_btn],
                 layout=widgets.Layout(width=ROW_W,
                                       justify_content='space-between')),
], layout=widgets.Layout(**box_style))
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
], layout=widgets.Layout(**box_style))
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
    display(widgets.VBox([ctrl_box, narration_box, board_out]))
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
    if is_tracing and n > 6:
        status.value    = f'Trace mode: N = {n} may be very large — please set N ≤ 6.'
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
    else:
        strategy, m = method.split('-')          # e.g. 'mrv-rec' -> 'mrv', 'rec'
        full_method  = 'recursion' if m == 'rec' else 'generator'
        solutions = solve_n_queens_propagation(n, full_method, strategy,
                                               trace=trace_steps if is_tracing else None)

    state.update({'n': n, 'current_pos': 0, 'solutions': solutions,
                  'is_tracing': is_tracing, 'trace_steps': trace_steps})

    if is_tracing:
        status.value    = step_label(0)
        narrative.value = narrative_text(0)
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
        total      = len(state['trace_steps'])
        n_sols     = len(state['solutions'])
        sols_so_far = sum(
            1 for t in state['trace_steps'][:c + 1]
            if not t.get('dead_end') and not t['unassigned']
        )
        s = '' if n_sols == 1 else 's'
        return f' Step {c + 1} of {total}  ({sols_so_far} of {n_sols} solution{s})'
    else:
        total = len(state['solutions'])
        return f'Solution {c + 1} of {total}'

def narrative_text(c):
    """One-line description of the transition that led to trace step c."""
    if not state['is_tracing'] or not state['trace_steps']:
        return ''
    ts   = state['trace_steps'][c]
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
