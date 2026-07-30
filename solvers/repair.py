import random
from .utilities import queens_conflict


def repair_attacks(queens, row, col, n):
    """
    Count how many queens (other than the one in `row`) would attack the cell
    (row, col).  Used to evaluate candidate columns for a queen: a count of 0
    means placing the queen at col would create no new conflicts.

    Args:
        queens: list of column positions, one per row (queens[r] = col of queen in row r).
        row:    the row whose queen is being evaluated; excluded from the count.
        col:    the candidate column to test for that queen.
        n:      board size.
    """
    return sum(1 for r in range(n)
               if r != row and queens_conflict(r, queens[r], row, col))


def conflict_summary(queens, n):
    """
    Returns a short human-readable phrase describing the current conflicts, e.g.
    '3 diagonal conflicts' or '1 column, 2 diagonal conflicts'.
    Used only for trace labels.

    Args:
        queens: list of column positions, one per row.
        n:      board size.
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
    Called when the normal min-conflicts move would revisit a board state already
    in `seen`.  Tries to find an alternative move that:
      - moves a most-attacked queen (same criterion as the normal move)
      - goes to a column different from the queen's current column
      - does not undo the immediately preceding move (to avoid bouncing back)
      - leads to a board state not already in `seen`
    Among all qualifying columns, picks those that reduce total board conflicts
    the most, then chooses randomly among ties.

    Modifies queens in place.
    Returns the new prev_move tuple (esc_row, new_col), or None if every
    candidate destination is already in seen — in which case the caller should
    trigger a fresh restart.

    Args:
        queens:    list of column positions, modified in place.
        attacks:   list of per-queen attack counts for the current board, as
                   returned by repair_attacks for each row.
        max_att:   the highest attack count in `attacks`; queens with this count
                   are candidates to move.
        prev_move: (row, col) of the immediately preceding move, or None if this
                   is the first move of the restart.  Used to exclude the column
                   that would simply undo that move.
        n:         board size.
        seen:      set of board states (as tuples) visited so far in this restart.
        trace:     list to append trace steps to, or None if tracing is off.
        MAX_TRACE: maximum number of trace steps to record.
        restart:   0-based restart index, used in trace labels.
    """
    # Total conflicts across the whole board before the escape move.
    # We divide by 2 because each conflicting pair is counted twice (once per queen).
    current_total = sum(attacks) // 2

    # Pick one of the most-attacked queens as the queen to move.
    esc_row     = random.choice([r for r, a in enumerate(attacks) if a == max_att])
    esc_old_col = queens[esc_row]

    # If the immediately preceding move placed a queen in esc_row, exclude that
    # destination column.  Without this, the escape might just undo the last move
    # and send us right back to where we came from.
    excluded = prev_move[1] if prev_move and prev_move[0] == esc_row else None

    best_delta = float('-inf')
    esc_cols   = []
    for col in range(n):
        if col == esc_old_col or col == excluded:
            continue

        # Tentatively place the queen at col and check whether the resulting
        # board state has been visited before.  Restore before continuing.
        queens[esc_row] = col
        if tuple(queens) in seen:
            queens[esc_row] = esc_old_col
            continue

        # Measure how much this move reduces total board conflicts.
        new_total = sum(repair_attacks(queens, r, queens[r], n) for r in range(n)) // 2
        queens[esc_row] = esc_old_col
        delta = current_total - new_total   # positive = fewer conflicts

        if delta > best_delta:
            best_delta = delta; esc_cols = [col]
        elif delta == best_delta:
            esc_cols.append(col)

    if not esc_cols:
        # Every candidate column either was excluded or leads to a seen state.
        # Signal the caller to restart rather than spinning further.
        return None

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
    Run one restart of the min-conflicts repair loop starting from the given
    queens arrangement.  Modifies queens in place.

    Each step:
      1. Records the current board state in `seen` so we can detect revisits.
      2. Checks whether all conflicts are resolved (solution found).
      3. Picks a most-attacked queen and moves it to the column that minimises
         its attacks (the standard min-conflicts heuristic).
      4. If that move would revisit a seen state, undoes it and calls
         escape_cycle instead.  If escape_cycle cannot find an unseen
         destination, breaks out to trigger a fresh restart.

    `trace_states` is a separate set that tracks which board states have
    been recorded as move outputs.  The assertion ensures no state appears
    twice in the trace — a tighter check than `seen`, which tracks starting
    states rather than landing states.

    Returns (solution, steps) on success, or (None, steps) on failure.

    Args:
        queens:    list of column positions, modified in place.
        n:         board size.
        max_steps: maximum iterations before giving up and returning None.
        MAX_TRACE: maximum number of trace steps to record.
        trace:     list to append trace steps to, or None if tracing is off.
        restart:   0-based restart index, used in trace labels.
    """
    prev_move    = None   # (row, col) of the most recent move, used by escape_cycle
    seen         = set()  # board states we have started an iteration from
    trace_states = set()  # board states recorded as move outputs (for assertion)

    for step in range(max_steps):
        # Mark current state as visited before proposing any move.
        key = tuple(queens)
        seen.add(key)

        # Compute the number of conflicts each queen is involved in.
        attacks = [repair_attacks(queens, r, queens[r], n) for r in range(n)]
        max_att = max(attacks)

        if max_att == 0:
            # No queen is in conflict — solution found.
            if trace is not None:
                trace.append({
                    'type':      'repair_step',
                    'queens':    queens[:],
                    'moved_row': None,
                    'restart':   restart + 1,
                    'label':     '<b>Solution found!</b> All conflicts resolved.',
                })
            return queens, step + 1

        # Choose one of the most-attacked queens to move.
        row     = random.choice([r for r, a in enumerate(attacks) if a == max_att])
        old_col = queens[row]

        # Find the column(s) for this queen that minimise its attack count.
        best      = float('inf')
        best_cols = []
        for col in range(n):
            a = repair_attacks(queens, row, col, n)
            if a < best:
                best = a; best_cols = [col]
            elif a == best:
                best_cols.append(col)

        # Tentatively make the min-conflicts move.
        queens[row] = random.choice(best_cols)

        if tuple(queens) in seen:
            # The proposed move would take us to a state we've already visited.
            # Undo it and try an escape move instead.
            queens[row] = old_col
            prev_move = escape_cycle(queens, attacks, max_att, prev_move,
                                      n, seen, trace, MAX_TRACE, restart)
            if prev_move is None:
                break  # escape_cycle found no unseen destination; restart
            assert tuple(queens) not in trace_states, f"Duplicate after escape: {queens}"
            trace_states.add(tuple(queens))
        else:
            # Normal move committed.
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

    Args:
        n:            board size (number of queens and rows/columns).
        trace:        list to append trace steps to, or None to skip tracing.
        max_restarts: number of random restarts to attempt before giving up.

    Returns:
        (solution, trace, steps_taken)  — solution is list[int] (col per row)
        or None on failure; steps_taken counts inner-loop iterations across
        all restarts.
    """
    max_steps   = max(1000, 5 * n)
    MAX_TRACE   = 150
    steps_taken = 0

    for restart in range(max_restarts):
        # Fresh random permutation: one queen per row and one per column,
        # so there are no row or column conflicts at the start of each restart.
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
