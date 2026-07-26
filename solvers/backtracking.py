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
