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
- *Iterative Repair* — min-conflicts local search: starts with a random \
permutation (one queen per row and column) and repeatedly moves the \
most-attacked queen to the column that minimises diagonal conflicts. \
Finds solutions for very large boards (N = 500+) in seconds.

---

The Github repo is available [here](https://github.com/RussAbbott/N_Queens).
"""


#@title ── N-Queens output ───────────────────────────────────────────────────────────

import ipywidgets as widgets
from IPython.display import display, clear_output
n_queens_output = widgets.Output()
display(n_queens_output)


#@title ── Setup ───────────────────────────────────────────────

import sys, os
try:
    import google.colab
    if not os.path.exists('N_Queens'):
        os.system('git clone https://github.com/RussAbbott/N_Queens.git -q')
    if 'N_Queens' not in sys.path:
        sys.path.insert(0, 'N_Queens')
except ImportError:
    pass   # running locally — ensure the N_Queens repo root is in sys.path


#@title ── Imports ──────────────────────────────────────────────

from solvers.backtracking import solve_n_queens_propagation
from solvers.lean         import solve_n_queens_lean
from solvers.cp_sat       import solve_n_queens_cp
from solvers.repair       import solve_n_queens_repair


#@title ── Draw the board ───────────────────────────────────────────────────────────────────

import matplotlib.pyplot as plt
import matplotlib.patches as patches

LIGHT_SQ    = '#F0D9B5'
DARK_SQ     = '#B58863'
QUEEN_FG    = '#1a1a2e'
MAX_BOARD_N = 24   # above this N, switch to compact scatter display

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
    if n > MAX_BOARD_N:
        # ── Compact scatter mode: chessboard cells too small to read ──────────
        fig, ax = plt.subplots(figsize=(4, 4))
        fig.patch.set_facecolor('#ecf0f1')
        ax.set_facecolor('#dfe6e9')
        ax.set_xlim(-0.5, n - 0.5)
        ax.set_ylim(-0.5, n - 0.5)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title(f'N = {n}  (one dot per queen)', fontsize=8, pad=3, color='#333')
        dot_s = max(2, 400 // n)

        if trace_steps is not None and trace_steps.get('type') == 'repair_step':
            queens    = trace_steps['queens']
            moved_row = trace_steps.get('moved_row')
            from_col  = trace_steps.get('from_col')
            to_col    = trace_steps.get('to_col')
            # Former conflict lines + faded dot — drawn first, behind everything.
            if moved_row is not None and from_col is not None:
                for r in range(n):
                    if r == moved_row:
                        continue
                    c = queens[r]
                    if c == from_col or abs(r - moved_row) == abs(c - from_col):
                        ax.plot([from_col, c], [n - 1 - moved_row, n - 1 - r],
                                color='#dd2222', linewidth=0.3, alpha=0.25, zorder=2)
                ax.scatter([from_col], [n - 1 - moved_row],
                           c=[QUEEN_FG], s=dot_s, alpha=0.25, zorder=3, linewidths=0)
            # Current conflict lines.
            for r1 in range(n):
                for r2 in range(r1 + 1, n):
                    c1, c2 = queens[r1], queens[r2]
                    if c1 == c2 or abs(r1 - r2) == abs(c1 - c2):
                        ax.plot([c1, c2], [n - 1 - r1, n - 1 - r2],
                                color='#dd2222', linewidth=0.5, alpha=0.35, zorder=3)
            # All current queens in black.
            dot_cols = [queens[r] for r in range(n)]
            dot_rows = [n - 1 - r for r in range(n)]
            ax.scatter(dot_cols, dot_rows, c=[QUEEN_FG], s=dot_s, zorder=4, linewidths=0)
            # Green arrow from former to new position.
            if moved_row is not None and from_col is not None:
                ax.annotate('',
                    xy=(to_col, n - 1 - moved_row),
                    xytext=(from_col, n - 1 - moved_row),
                    arrowprops=dict(arrowstyle='->', color='#00aa00',
                                   lw=1.0, mutation_scale=10),
                    zorder=5)
        elif solution is not None:
            cols = [solution[r] for r in range(n)]
            rows = [n - 1 - r  for r in range(n)]
            ax.scatter(cols, rows, c=[QUEEN_FG], s=dot_s, zorder=4, linewidths=0)

        plt.tight_layout()
        plt.show()
        plt.close(fig)
        return

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

    elif trace_steps is not None and trace_steps.get('type') == 'repair_step':
        # ── Repair trace step ────────────────────────────────────────────────
        queens    = trace_steps['queens']
        moved_row = trace_steps.get('moved_row')
        from_col  = trace_steps.get('from_col')
        to_col    = trace_steps.get('to_col')
        # Former conflict lines + faded queen — drawn first, behind everything.
        if moved_row is not None and from_col is not None:
            for r in range(n):
                if r == moved_row:
                    continue
                c = queens[r]
                if c == from_col or abs(r - moved_row) == abs(c - from_col):
                    ax.plot([from_col + 0.5, c + 0.5],
                            [n - 0.5 - moved_row, n - 0.5 - r],
                            color='#dd2222', linewidth=0.8, alpha=0.25, zorder=2)
            ax.text(from_col + 0.5, n - 0.5 - moved_row, '♛',
                    ha='center', va='center', fontsize=queen_fs,
                    color=QUEEN_FG, alpha=0.25, zorder=3)
        # Current conflict lines.
        for r1 in range(n):
            for r2 in range(r1 + 1, n):
                c1, c2 = queens[r1], queens[r2]
                if c1 == c2 or abs(r1 - r2) == abs(c1 - c2):
                    ax.plot([c1 + 0.5, c2 + 0.5], [n - 0.5 - r1, n - 0.5 - r2],
                            color='#dd2222', linewidth=1.5, alpha=0.6, zorder=3)
        # All current queens in black.
        for row in range(n):
            ax.text(queens[row] + 0.5, n - 0.5 - row, '♛',
                    ha='center', va='center', fontsize=queen_fs, color=QUEEN_FG, zorder=4)
        # Green arrow from former to new position.
        if moved_row is not None and from_col is not None:
            ax.annotate('',
                xy=(to_col + 0.5, n - 0.5 - moved_row),
                xytext=(from_col + 0.5, n - 0.5 - moved_row),
                arrowprops=dict(arrowstyle='->', color='#00aa00',
                               lw=1.5, mutation_scale=15),
                zorder=5)

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
    value=8, min=1, max=500, description='',
    style={'description_width': '0px'},
    layout=widgets.Layout(width='70px'))

method_options = [
    ('In-order, recursion',  'inorder-rec'),
    ('In-order, generator',  'inorder-gen'),
    ('MRV, recursion',       'mrv-rec'),
    ('MRV, generator',       'mrv-gen'),
    ('OR-Tools CP-SAT',      'cp'),
    ('Lean proof-building',  'lean'),
    ('Iterative Repair',     'repair'),
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
                                           width=FULL_W,
                                           justify_content='center',
                                           gap='20px',
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
    if is_tracing and n > 6 and method not in ('lean', 'repair'):
        status.value    = f'Trace mode: N = {n} may be very large — please set N ≤ 6.'
        narrative.value = ''
        return
    if is_tracing and n > 12 and method == 'lean':
        status.value    = f'Lean trace: N = {n} may be slow — please set N ≤ 12.'
        narrative.value = ''
        return
    if is_tracing and n > 40 and method == 'repair':
        status.value    = f'Repair trace: N = {n} — please set N ≤ 40 for trace mode.'
        narrative.value = ''
        return

    trace_steps  = []
    repair_steps = None

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
    elif method == 'repair':
        sol, _, repair_steps = solve_n_queens_repair(n, trace=trace_steps if is_tracing else None)
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
        if method == 'repair' and not is_tracing:
            status.value = f'Solution found in {repair_steps} steps'
        else:
            status.value = f'Solution 1 of {len(solutions)}'
        narrative.value = ''
    else:
        if method == 'repair':
            status.value = f'No solution found after {repair_steps} steps'
        else:
            status.value = f'No solutions for N = {n}'
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
        if ts.get('type') == 'repair_step':
            return f'Step {c + 1} of {total}'
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
    if ts.get('type') == 'repair_step':
        return ts.get('label', '')
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


#@title ── Benchmark: Iterative Repair — run ────────────────────────────────────────────────

import numpy as np
import time

# Schedule: (n, trials) pairs.
# Dense for small N (erratic, interesting), sparser for large N (O(N) story).
BM_SCHEDULE = (
    [(n, 100) for n in range(4, 51)]         # 4–50,   step 1,  100 trials
  + [(n,  50) for n in range(55, 151, 5)]    # 55–150, step 5,   50 trials
  + [(n,  10) for n in (200, 300, 500)]      # large N, spot checks
)

bm_data = {}   # {n: [step_counts]}  — survives to the plot cell

def run_benchmark():
    t0           = time.time()
    total_trials = sum(t for _, t in BM_SCHEDULE)
    done         = 0
    try:
        for n, trials in BM_SCHEDULE:
            steps_list = []
            for _ in range(trials):
                _, _, s = solve_n_queens_repair(n)
                steps_list.append(s)
                done += 1
            bm_data[n] = steps_list
            elapsed = time.time() - t0
            pct     = 100 * done / total_trials
            eta     = elapsed / pct * (100 - pct) if pct > 0 else 0
            print(f'N={n:4d}  mean={np.mean(steps_list):8.1f}  '
                  f'std={np.std(steps_list):7.1f}  '
                  f'min={min(steps_list):6d}  max={max(steps_list):6d}  '
                  f'[{pct:5.1f}%  ETA {eta:.0f}s]', flush=True)
    except KeyboardInterrupt:
        print('\nStopped early — the plot cell will use data collected so far.')
    print(f'\nDone: {len(bm_data)} N-values in {time.time() - t0:.1f}s')

print('Call run_benchmark() to start.\n'
      'Interrupt with Ctrl-C at any time; partial results still plot.\n')


#@title ── Benchmark: Iterative Repair — plot ───────────────────────────────────────────────

import matplotlib.pyplot as plt
import numpy as np

if not bm_data:
    print('Run the benchmark cell first.')
else:
    ns    = np.array(sorted(bm_data))
    means = np.array([np.mean(bm_data[n]) for n in ns])
    stds  = np.array([np.std(bm_data[n])  for n in ns])

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    fig.suptitle('Iterative Repair (Min-Conflicts) — empirical step counts', fontsize=13)

    # ── Top: raw step counts ──────────────────────────────────────────────────
    ax1.fill_between(ns, np.maximum(0, means - stds), means + stds,
                     alpha=0.20, color='steelblue', label='±1σ')
    ax1.plot(ns, means, color='steelblue', linewidth=1.5, label='mean')

    large = ns >= 100
    if large.sum() >= 2:
        c = np.polyfit(ns[large], means[large], 1)
        ax1.plot(ns, np.polyval(c, ns), '--', color='firebrick', linewidth=1,
                 label=f'linear fit (N≥100):  {c[0]:.2f}·N + {c[1]:.0f}')

    ax1.set(xlabel='N  (board size)', ylabel='Steps', title='Total steps to solution')
    ax1.legend(fontsize=9)
    ax1.set_xlim(ns[0], ns[-1])
    ax1.set_ylim(bottom=0)
    ax1.grid(True, alpha=0.3)

    # ── Bottom: steps / N (shows O(N) convergence) ────────────────────────────
    ax2.fill_between(ns,
                     np.maximum(0, means - stds) / ns,
                     (means + stds) / ns,
                     alpha=0.20, color='darkorange')
    ax2.plot(ns, means / ns, color='darkorange', linewidth=1.5, label='mean steps / N')
    if large.sum() >= 2:
        ax2.axhline(c[0], color='firebrick', linestyle='--', linewidth=1,
                    label=f'asymptote ≈ {c[0]:.2f}  (slope of linear fit above)')

    ax2.set(xlabel='N  (board size)', ylabel='Steps / N',
            title='Steps per queen — converges toward a constant for large N')
    ax2.legend(fontsize=9)
    ax2.set_xlim(ns[0], ns[-1])
    ax2.set_ylim(bottom=0)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()
    plt.close(fig)


#@title ── Resources ────────────────────────────────────────────────────────────────

MARKDOWN_CELL = """\
## Resources

Russ Abbott wrote the solvers; Claude Code wrote the GUI.
"""