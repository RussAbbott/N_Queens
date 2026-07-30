import random
from .utilities import queens_conflict


def repair_attacks(queens, row, col, n):
    """Number of queens (excluding row `row`) that attack cell (row, col)."""
    return sum(1 for r in range(n)
               if r != row and queens_conflict(r, queens[r], row, col))


def conflict_summary(queens, n):
    """
    Returns a short phrase describing current conflicts, e.g.
    '3 diagonal conflicts' or '1 column, 2 diagonal conflicts'.
    """
    col_conf  = sum(1 for r1 in range(n) for r2 in range(r1 + 1, n)
                    if queens[r1] == queens[r2])
    diag_conf = sum(1 for r1 in range(n) for r2 in range(r1 + 1, n)
                    if queens[r1] != queens[r2]
                    and abs(r1 - r2) == abs(queens[r1] - queens[r2]))
    if col_conf == 0 and diag_conf == 0:
        return '0 conflicts'
    parts = []
    if col_conf:  parts.append(f'{col_conf} column')
    if diag_conf: parts.append(f'{diag_conf} diagonal')
    total = col_conf + diag_conf
    s = 's' if total != 1 else ''
    return ', '.join(parts) + f' conflict{s}'


def escape_cycle(queens, attacks, max_att, prev_move, n, seen, trace, MAX_TRACE, restart):
    """
    Pick the single-queen move that maximises total conflict reduction among
    destinations not already in seen, excluding the immediately preceding move.
    Modifies queens in place.  Returns the new prev_move tuple, or None if
    every candidate destination is already in seen (caller should restart).
    """
    current_total = sum(attacks) // 2
    esc_row     = random.choice([r for r, a in enumerate(attacks) if a == max_att])
    esc_old_col = queens[esc_row]
    excluded    = prev_move[1] if prev_move and prev_move[0] == esc_row else None

    best_delta = float('-inf')
    esc_cols   = []
    for col in range(n):
        if col == esc_old_col or col == excluded:
            continue
        queens[esc_row] = col
        if tuple(queens) in seen:
            queens[esc_row] = esc_old_col
            continue
        new_total = sum(repair_attacks(queens, r, queens[r], n) for r in range(n)) // 2
        queens[esc_row] = esc_old_col
        delta = current_total - new_total
        if delta > best_delta:
            best_delta = delta; esc_cols = [col]
        elif delta == best_delta:
            esc_cols.append(col)

    if not esc_cols:
        return None  # no unseen escape exists; caller should restart

    queens[esc_row] = random.choice(esc_cols)
    if trace is not None and len(trace) < MAX_TRACE:
        trace.append({
            'type':      'repair_step',
            'queens':    queens[:],
            'moved_row': esc_row,
            'from_col':  esc_old_col,
            'to_col':    queens[esc_row],
            'restart':   restart + 1,
            'label':     (f'<i>Cycle</i> — escape: row {esc_row + 1}: '
                          f'col {esc_old_col + 1} → col {queens[esc_row] + 1} '
                          f'(max conflict reduction, skipping last move). '
                          f'{conflict_summary(queens, n).capitalize()} remaining.'),
        })
    return (esc_row, queens[esc_row])


def repair_restart(queens, n, max_steps, MAX_TRACE, trace, restart):
    """
    Run one restart of the min-conflicts repair loop.
    Modifies queens in place.
    Returns (solution, steps) where solution is the queens list on success,
    or (None, steps) if max_steps is exhausted without finding one.
    """
    prev_move    = None
    seen         = set()
    trace_states = set()
    for step in range(max_steps):
        key = tuple(queens)
        seen.add(key)

        attacks = [repair_attacks(queens, r, queens[r], n) for r in range(n)]
        max_att = max(attacks)
        if max_att == 0:
            if trace is not None:
                trace.append({
                    'type':      'repair_step',
                    'queens':    queens[:],
                    'moved_row': None,
                    'restart':   restart + 1,
                    'label':     '<b>Solution found!</b> All conflicts resolved.',
                })
            return queens, step + 1

        row     = random.choice([r for r, a in enumerate(attacks) if a == max_att])
        old_col = queens[row]

        best      = float('inf')
        best_cols = []
        for col in range(n):
            a = repair_attacks(queens, row, col, n)
            if a < best:
                best = a; best_cols = [col]
            elif a == best:
                best_cols.append(col)

        queens[row] = random.choice(best_cols)

        if tuple(queens) in seen:
            queens[row] = old_col
            prev_move = escape_cycle(queens, attacks, max_att, prev_move,
                                      n, seen, trace, MAX_TRACE, restart)
            if prev_move is None:
                break  # no unseen escape; trigger restart
            assert tuple(queens) not in trace_states, f"Duplicate after escape: {queens}"
            trace_states.add(tuple(queens))
        else:
            prev_move = (row, queens[row])
            assert tuple(queens) not in trace_states, f"Duplicate after normal move: {queens}"
            trace_states.add(tuple(queens))
            if trace is not None and len(trace) < MAX_TRACE and queens[row] != old_col:
                trace.append({
                    'type':      'repair_step',
                    'queens':    queens[:],
                    'moved_row': row,
                    'from_col':  old_col,
                    'to_col':    queens[row],
                    'restart':   restart + 1,
                    'label':     (f'Row {row + 1}: col {old_col + 1} → col {queens[row] + 1}. '
                                  f'{conflict_summary(queens, n).capitalize()} remaining.'),
                })

    return None, max_steps


def solve_n_queens_repair(n, trace=None, max_restarts=100):
    """
    Min-conflicts iterative repair solver for N-Queens.

    Starts with a random permutation (one queen per row, one per column),
    which guarantees no row or column conflicts initially — only diagonals
    need repair.  Subsequent moves may introduce column conflicts; the
    solver handles both.  Restarts with a new random permutation when
    progress stalls or a cycle is detected.

    Fast in practice: typically finds a solution in O(N) repair steps, so
    it easily handles boards with thousands of queens.

    Returns:
        (solution, trace, steps_taken)  — solution is list[int] (col per row)
        or None on failure; steps_taken counts inner-loop iterations.
    """
    max_steps   = max(1000, 5 * n)
    MAX_TRACE   = 150
    steps_taken = 0

    for restart in range(max_restarts):
        queens = list(range(n))
        random.shuffle(queens)

        if trace is not None and len(trace) < MAX_TRACE:
            trace.append({
                'type':      'repair_step',
                'queens':    queens[:],
                'moved_row': None,
                'restart':   restart + 1,
                'label':     (f'<b>Restart {restart + 1}:</b> random initial placement '
                              f'(one queen per row and column). '
                              f'{conflict_summary(queens, n).capitalize()}.'),
            })

        result, steps = repair_restart(queens, n, max_steps, MAX_TRACE, trace, restart)
        steps_taken  += steps
        if result is not None:
            return result, trace, steps_taken

    return None, trace, steps_taken
