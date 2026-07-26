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
        # Random permutation: no row or column conflicts to start.
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

        prev_move = None   # (row, to_col) of the immediately preceding move
        seen = set()
        for _ in range(max_steps):
            steps_taken += 1
            key = tuple(queens)
            if key in seen:
                # Escape: pick the single-queen move that maximises total conflict
                # reduction across the whole board, excluding the immediately
                # preceding move (which would just cycle us back).
                att_now       = [repair_attacks(queens, r, queens[r], n) for r in range(n)]
                row           = random.choice([r for r, a in enumerate(att_now)
                                               if a == max(att_now)])
                old_col       = queens[row]
                current_total = sum(att_now) // 2
                excluded      = prev_move[1] if prev_move and prev_move[0] == row else None

                best_delta = float('-inf')
                best_cols  = []
                for col in range(n):
                    if col == old_col or col == excluded:
                        continue
                    queens[row] = col
                    new_total = sum(repair_attacks(queens, r, queens[r], n)
                                    for r in range(n)) // 2
                    queens[row] = old_col
                    delta = current_total - new_total
                    if delta > best_delta:
                        best_delta = delta; best_cols = [col]
                    elif delta == best_delta:
                        best_cols.append(col)

                if not best_cols:   # excluded was the only candidate
                    best_cols = [col for col in range(n) if col != old_col]

                queens[row] = random.choice(best_cols) if best_cols else old_col
                prev_move = (row, queens[row])
                seen.clear()
                if trace is not None and len(trace) < MAX_TRACE:
                    trace.append({
                        'type':      'repair_step',
                        'queens':    queens[:],
                        'moved_row': row,
                        'from_col':  old_col,
                        'to_col':    queens[row],
                        'restart':   restart + 1,
                        'label':     (f'<i>Cycle</i> — escape: row {row + 1}: '
                                      f'col {old_col + 1} → col {queens[row] + 1} '
                                      f'(max conflict reduction, skipping last move). '
                                      f'{conflict_summary(queens, n).capitalize()} remaining.'),
                    })
                continue
            seen.add(key)

            attacks  = [repair_attacks(queens, r, queens[r], n) for r in range(n)]
            max_att  = max(attacks)
            if max_att == 0:
                if trace is not None:
                    trace.append({
                        'type':      'repair_step',
                        'queens':    queens[:],
                        'moved_row': None,
                        'restart':   restart + 1,
                        'label':     '<b>Solution found!</b> All conflicts resolved.',
                    })
                return queens, trace, steps_taken

            # Pick randomly among most-attacked queens.
            row     = random.choice([r for r, a in enumerate(attacks) if a == max_att])
            old_col = queens[row]

            # Find the column(s) in this row that minimise attacks on this queen.
            best      = float('inf')
            best_cols = []
            for col in range(n):
                a = repair_attacks(queens, row, col, n)
                if a < best:
                    best = a; best_cols = [col]
                elif a == best:
                    best_cols.append(col)

            queens[row] = random.choice(best_cols)
            prev_move = (row, queens[row])

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

    return None, trace, steps_taken
