import Mathlib

/-!
Lean 4 formalization of the N-Queens `SubSol` / `merge` model.

Core concepts:
  - `attack`        : two squares share a row, column, or diagonal
  - `nonAttacking`  : a set in which no two members attack each other
  - `SubSol`        : a set of positions proven to be nonAttacking
  - `compatible`    : two SubSols with no cross-attacks
  - `merge`         : combines two compatible SubSols into one
-/

/-- Two squares attack each other if they share a row, a column, or a diagonal. -/
def attack (p q : Nat × Nat) : Prop :=
  p.1 = q.1 ∨ p.2 = q.2 ∨
  (p.1 : Int) + (p.2 : Int) = (q.1 : Int) + (q.2 : Int) ∨
  (p.1 : Int) - (p.2 : Int) = (q.1 : Int) - (q.2 : Int)

instance (p q : Nat × Nat) : Decidable (attack p q) := by
  unfold attack; infer_instance

/-- Attack is symmetric. -/
theorem attack_symm {p q : Nat × Nat} (h : attack p q) : attack q p := by
  unfold attack at *
  rcases h with h | h | h | h
  · exact Or.inl h.symm
  · exact Or.inr (Or.inl h.symm)
  · exact Or.inr (Or.inr (Or.inl h.symm))
  · exact Or.inr (Or.inr (Or.inr h.symm))

/-- Every square attacks itself (same row and column). -/
lemma attack_self (p : Nat × Nat) : attack p p := Or.inl rfl

/-- A set of positions is nonAttacking if no two distinct members attack each other. -/
def nonAttacking (s : Finset (Nat × Nat)) : Prop :=
  ∀ p ∈ s, ∀ q ∈ s, p ≠ q → ¬ attack p q

instance (s : Finset (Nat × Nat)) : Decidable (nonAttacking s) := by
  unfold nonAttacking; infer_instance

/--
A `SubSol` is a nonAttacking set of positions — the positions bundled with
the proof that they are jointly placeable.  Writing `p ∈ s` (via the
`Membership` instance below) means `p` is one of the positions in `s`.
-/
structure SubSol where
  positions : Finset (Nat × Nat)
  proof     : nonAttacking positions

/-- Allows writing `p ∈ s` for a `SubSol s`. -/
private def SubSol.mem (s : SubSol) (p : Nat × Nat) : Prop := p ∈ s.positions
instance : Membership (Nat × Nat) SubSol := ⟨SubSol.mem⟩

/-- Lemma: any singleton set is nonAttacking (a single queen attacks no other). -/
lemma singleton_nonAttacking (p : Nat × Nat) : nonAttacking {p} := by
  intro a ha b hb _
  simp only [Finset.mem_singleton] at ha hb
  subst ha; subst hb
  tauto

/-- For every position `p`, the singleton `{p}` is a valid SubSol. -/
def singleton_subSol (p : Nat × Nat) : SubSol :=
  ⟨{p}, singleton_nonAttacking p⟩

/--
Two SubSols are compatible if no member of one attacks any member of the other.
Note: if the same position appeared in both, `attack p p` would hold (same row
and column), so compatibility already rules that out.
-/
def compatible (s t : SubSol) : Prop :=
  ∀ p ∈ s.positions, ∀ q ∈ t.positions, ¬ attack p q

private instance (t : SubSol) (p : Nat × Nat) :
    Decidable (∀ q ∈ t.positions, ¬ attack p q) := by infer_instance

instance (s t : SubSol) : Decidable (compatible s t) := by
  unfold compatible; infer_instance

/--
`merge` is the key inference rule: two compatible SubSols can be joined into
one.  The proof below verifies that the union is nonAttacking.
-/
def merge (s t : SubSol) (h : compatible s t) : SubSol where
  positions := s.positions ∪ t.positions
  proof := by
    intro p hp q hq hpq
    simp only [Finset.mem_union] at hp hq
    rcases hp with hp | hp <;> rcases hq with hq | hq
    · exact s.proof p hp q hq hpq
    · exact h p hp q hq
    · exact fun hc => h q hq p hp (attack_symm hc)
    · exact t.proof p hp q hq hpq

/--
Lemma: if two SubSols are compatible, their union is nonAttacking.
(This is the central fact that justifies `merge`.)
-/
lemma compatible_union_nonAttacking (s t : SubSol) (h : compatible s t) :
    nonAttacking (s.positions ∪ t.positions) :=
  (merge s t h).proof

/-- A full solution: a SubSol that places exactly `n` queens (one per row). -/
def isSolution (n : Nat) (s : SubSol) : Prop :=
  s.positions.card = n

-- ── Excluded set ─────────────────────────────────────────────────────────────

/--
Cell `p` is excluded by SubSol `s` if it is occupied by or attacked by one of s's queens.
This is the Lean counterpart of the Python `exc` field carried by each SubSol.
-/
def inExc (s : SubSol) (p : Nat × Nat) : Prop :=
  p ∈ s.positions ∨ ∃ q ∈ s.positions, attack q p

/--
One-sided compatibility check: no position of `t` falls in the excluded zone of `s`.
Because `attack` is symmetric, checking one direction is sufficient.
This corresponds to the Python `can_combine` check `self.exc.isdisjoint(other.positions)`.
-/
def canCombine (s t : SubSol) : Prop :=
  ∀ p ∈ t.positions, ¬ inExc s p

/-- `canCombine s t` is equivalent to `compatible s t`. -/
theorem canCombine_iff_compatible (s t : SubSol) :
    canCombine s t ↔ compatible s t := by
  unfold canCombine compatible inExc
  constructor
  · intro h p hp q hq
    have hq_notexc := h q hq
    push Not at hq_notexc
    exact hq_notexc.2 p hp
  · intro h p hp
    push Not
    exact ⟨fun hps => (h p hps p hp) (attack_self p),
           fun q hqs => h q hqs p hp⟩

/-- The excluded zone of a merged SubSol is the union of the two parents' excluded zones. -/
lemma inExc_merge (s t : SubSol) (h : compatible s t) (p : Nat × Nat) :
    inExc (merge s t h) p ↔ inExc s p ∨ inExc t p := by
  simp [inExc, merge, Finset.mem_union]
  tauto

#print axioms merge

-- ── Sanity checks ────────────────────────────────────────────────────────────

def s1 : SubSol := ⟨{(0, 0)}, by native_decide⟩
def s2 : SubSol := ⟨{(1, 2)}, by native_decide⟩
def s3 : SubSol := ⟨{(0, 1)}, by native_decide⟩

example : compatible s1 s2 := by native_decide
#eval (merge s1 s2 (by native_decide)).positions
example : ¬ compatible s1 s3 := by native_decide
