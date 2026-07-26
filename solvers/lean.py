import random
from .utilities import queens_conflict, cells_attacked


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
        """True iff no queen in self occupies or attacks any position in other."""
        return self.exc.isdisjoint(other.positions)

    def merge(self, other: 'SubSol') -> 'SubSol':
        """Return a new SubSol combining self and other, recording both as parents."""
        positions = self.positions | other.positions
        exc       = self.exc | other.exc   # own positions already in each parent's exc
        return SubSol(positions, exc, parent_1=self, parent_2=other)

    def is_prunable(self, n: int) -> bool:
        """
        True if this sub-solution is a dead end: some free row or free column
        has no safe cell remaining (every intersection is excluded).
        """
        if len(self.exc) == n * n:
            return True
        placed_rows = {row for row, _ in self.positions}
        placed_cols = {col for _, col in self.positions}
        free_rows = [r for r in range(n) if r not in placed_rows]
        free_cols = [c for c in range(n) if c not in placed_cols]
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
            exc  = cells_attacked(row, col, n) | cell   # include own position
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
