import ipywidgets as widgets
from IPython.display import display, clear_output
import matplotlib.pyplot as plt
import matplotlib.patches as patches


# ── Solver ────────────────────────────────────────────────────────────────────

def solve_n_queens(n):
    solutions = []

    def is_safe(board, row, col):
        for r in range(row):
            c = board[r]
            if c == col or abs(c - col) == abs(r - row):
                return False
        return True

    def backtrack(board, row):
        if row == n:
            solutions.append(list(board))
            return
        for col in range(n):
            if is_safe(board, row, col):
                board[row] = col
                backtrack(board, row + 1)
                board[row] = -1

    backtrack([-1] * n, 0)
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

n_input   = widgets.BoundedIntText(
    value=8, min=1, max=20, description='N:',
    layout=widgets.Layout(width='120px'))
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
    n = n_input.value
    state.update({'n': n, 'current': 0, 'solutions': solve_n_queens(n)})
    total = len(state['solutions'])
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


# ── Layout ────────────────────────────────────────────────────────────────────

display(widgets.VBox([
    widgets.HBox([n_input, solve_btn]),
    board_out,
    widgets.HBox([prev_btn, status, next_btn])
]))

with board_out:
    draw_board(None, 8)
