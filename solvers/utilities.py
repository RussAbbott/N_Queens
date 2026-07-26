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
