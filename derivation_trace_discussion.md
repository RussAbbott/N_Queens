# Derivation Trace: Step-Count Upper Bound Discussion
*Recorded 2026-07-23*

## Context

In the Lean proof-building N-Queens solver, a solution is found by randomly merging
sub-solutions (SubSols) until an n-queen SubSol is assembled. Each SubSol records its
two parents, forming an implicit derivation tree. The trace visualization replays
that derivation chronologically: starting from an empty board, each Next press shows
one more merge, until the full solution is displayed.

The question is: **how many display steps are there?**

---

## The Argument

### Structure of the derivation tree

Each SubSol was produced by merging exactly two parents. The n single-queen axioms
are the leaves. The complete solution is the root. So the derivation tree is a
**binary tree with n leaves**.

A standard result: any binary tree with n leaves has exactly **n − 1 internal nodes**.
Each internal node corresponds to one merge = one display step.
Therefore there are exactly **n − 1 display steps**.

### Russ's upper-bound argument (looser but valid)

After each display step, either:

(a) The "distinguished member" (the sub-solution that will grow into the final
    solution) gains at least one new cell (a merge directly into it), or

(b) A new cell is added to a non-distinguished active sub-solution, which will
    be merged into the distinguished member in a later step.

So it takes at most 2 steps to add one cell to the distinguished member.
There are n − 1 cells to add, giving an upper bound of **2(n − 1) = 2n − 2 steps**
(or 2n − 1 depending on how the initial state is counted).

This bound is valid but not tight. The tight bound is n − 1.

### Why the tree is a proper tree (not a DAG)

Could a SubSol appear as an ancestor of the solution via two different paths?
No. If SubSol X were shared between two branches that both feed into the solution,
X's queen positions would have to appear in both branches. But queens in different
branches must not conflict (otherwise `can_combine` would have rejected their
eventual merge). Two identical queen positions always conflict (same row and column),
so no queen can appear in two branches. Therefore the derivation structure is
always a proper tree, never a DAG.

### The balanced-split example

Suppose the final merge combines two n/2-queen parents:

- Steps to build left parent (n/2 leaves → n/2 − 1 internal nodes): **n/2 − 1**
- Steps to build right parent: **n/2 − 1**
- Final merge: **1**
- Total: 2(n/2 − 1) + 1 = **n − 1** ✓

(Russ initially computed n − 2 steps per parent, giving 2(n−2)+1 = 2n−3 total.
The correct per-parent count is n/2 − 1, not n − 2. The total is n − 1 either way.)

---

## Resolution (2026-07-23)

**n − 1 is correct.** Russ supplied the clean induction proof:

- Base case: a 2-cell sub-solution takes 1 step for 2 cells. ✓ (1 = 2 − 1)
- Adding one cell to a k-cell sub-solution: still k steps for k+1 cells. ✓ (k = (k+1) − 1)
- Merging a k-cell sub-solution (k−1 steps) with an m-cell sub-solution (m−1 steps):
  (k−1) + (m−1) + 1 = k+m−1 steps for k+m cells. ✓ ((k+m)−1)

The argument holds for any merge sizes, symmetric or not.
The earlier 2n−1 bound was valid but loose; n−1 is exact.

---

## Related implementation note

In `solve_n_queens_lean()`, `build_steps(root_ss)` does a post-order DFS of the
derivation tree and returns exactly n − 1 SubSols (the non-axiom internal nodes),
one per display step.
