import Mathlib

/-!
Lean 4 formalization of the N-Queens `SubSol` / `merge` model.

Core concepts:
  - `attack`        : two squares share a row, column, or diagonal
  - `nonAttacking`  : a set in which no two members attack each other
  - `attackedBy`    : the set of cells attacked by a set of queens
  - `SubSol`        : positions + excluded zone + nonAttacking proof
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

/-- Every square attacks itself. -/
lemma attack_self (p : Nat × Nat) : attack p p := Or.inl rfl

/-- A set of positions is nonAttacking if no two distinct members attack each other. -/
def nonAttacking (s : Finset (Nat × Nat)) : Prop :=
  ∀ p ∈ s, ∀ q ∈ s, p ≠ q → ¬ attack p q

instance (s : Finset (Nat × Nat)) : Decidable (nonAttacking s) := by
  unfold nonAttacking; infer_instance

/-- The set of all cells attacked by any queen in S. -/
def attackedBy (S : Finset (Nat × Nat)) : Set (Nat × Nat) :=
  {p | ∃ q ∈ S, attack q p}

/-- attackedBy distributes over union: f(S₁ ∪ S₂) = f(S₁) ∪ f(S₂). -/
lemma attackedBy_union (s t : Finset (Nat × Nat)) :
    attackedBy (s ∪ t) = attackedBy s ∪ attackedBy t := by
  ext p
  simp only [attackedBy, Set.mem_union, Finset.mem_union]
  constructor
  · rintro ⟨q, hq | hq, hatk⟩
    · exact Or.inl ⟨q, hq, hatk⟩
    · exact Or.inr ⟨q, hq, hatk⟩
  · rintro (⟨q, hq, hatk⟩ | ⟨q, hq, hatk⟩)
    · exact ⟨q, Or.inl hq, hatk⟩
    · exact ⟨q, Or.inr hq, hatk⟩

/--
A `SubSol` is a nonAttacking set of positions bundled with its excluded zone.
- `positions` : the queens placed so far
- `proof`     : they are jointly nonAttacking
- `exc`       : the set of cells occupied by or attacked by any queen in `positions`
- `exc_spec`  : exc equals exactly the positions union the cells they attack

This mirrors the Python `SubSol` class, which carries both `positions` and `exc`.
-/
structure SubSol where
  positions : Finset (Nat × Nat)
  proof     : nonAttacking positions
  exc       : Set (Nat × Nat)
  exc_spec  : exc = ↑positions ∪ attackedBy positions

/-- Allows writing `p ∈ s` for a `SubSol s`. -/
private def SubSol.mem (s : SubSol) (p : Nat × Nat) : Prop := p ∈ s.positions
instance : Membership (Nat × Nat) SubSol := ⟨SubSol.mem⟩

/-- Any singleton set is nonAttacking. -/
lemma singleton_nonAttacking (p : Nat × Nat) : nonAttacking {p} := by
  intro a ha b hb _
  simp only [Finset.mem_singleton] at ha hb
  subst ha; subst hb
  tauto

/--
The singleton `{p}` as a SubSol.  Its excluded zone is defined to be exactly
`↑{p} ∪ attackedBy {p}`, so `exc_spec` holds by `rfl`.
-/
def singleton_subSol (p : Nat × Nat) : SubSol where
  positions := {p}
  proof     := singleton_nonAttacking p
  exc       := ↑({p} : Finset (Nat × Nat)) ∪ attackedBy {p}
  exc_spec  := rfl

/--
Two SubSols are compatible if no member of one attacks any member of the other.
-/
def compatible (s t : SubSol) : Prop :=
  ∀ p ∈ s.positions, ∀ q ∈ t.positions, ¬ attack p q

private instance (t : SubSol) (p : Nat × Nat) :
    Decidable (∀ q ∈ t.positions, ¬ attack p q) := by infer_instance

instance (s t : SubSol) : Decidable (compatible s t) := by
  unfold compatible; infer_instance

/--
`merge` combines two compatible SubSols.  The excluded zone of the result is
`s.exc ∪ t.exc`, mirroring the Python `exc = self.exc | other.exc`.

The `exc_spec` proof uses:
  1. the parents' `exc_spec` to rewrite `s.exc` and `t.exc`
  2. `Finset.coe_union` : ↑(s ∪ t) = ↑s ∪ ↑t
  3. `attackedBy_union` : attackedBy (s ∪ t) = attackedBy s ∪ attackedBy t
  4. set algebra        : (A ∪ B) ∪ (C ∪ D) = (A ∪ C) ∪ (B ∪ D)
-/
def merge (s t : SubSol) (h : compatible s t) : SubSol where
  positions := s.positions ∪ t.positions
  proof     := by
    intro p hp q hq hpq
    simp only [Finset.mem_union] at hp hq
    rcases hp with hp | hp <;> rcases hq with hq | hq
    · exact s.proof p hp q hq hpq
    · exact h p hp q hq
    · exact fun hc => h q hq p hp (attack_symm hc)
    · exact t.proof p hp q hq hpq
  exc       := s.exc ∪ t.exc
  exc_spec  := by
    rw [s.exc_spec, t.exc_spec, Finset.coe_union, attackedBy_union]
    ext p; simp only [Set.mem_union]; tauto

/-- The union of two compatible SubSols' positions is nonAttacking. -/
lemma compatible_union_nonAttacking (s t : SubSol) (h : compatible s t) :
    nonAttacking (s.positions ∪ t.positions) :=
  (merge s t h).proof

/-- A full solution places exactly `n` queens. -/
def isSolution (n : Nat) (s : SubSol) : Prop :=
  s.positions.card = n

-- ── Excluded set ─────────────────────────────────────────────────────────────

/-- Cell `p` is excluded by SubSol `s` if it is in `s`'s stored excluded zone. -/
def inExc (s : SubSol) (p : Nat × Nat) : Prop := p ∈ s.exc

/-- Bridge: membership in exc is equivalent to being occupied or attacked. -/
lemma mem_exc_iff (s : SubSol) (p : Nat × Nat) :
    p ∈ s.exc ↔ p ∈ s.positions ∨ ∃ q ∈ s.positions, attack q p := by
  simp [s.exc_spec, attackedBy, Set.mem_union]

/--
One-sided compatibility check: no position of `t` falls in the excluded zone of `s`.
Corresponds to the Python `self.exc.isdisjoint(other.positions)`.
-/
def canCombine (s t : SubSol) : Prop :=
  ∀ p ∈ t.positions, ¬ inExc s p

/-- `canCombine s t` is equivalent to `compatible s t`. -/
theorem canCombine_iff_compatible (s t : SubSol) :
    canCombine s t ↔ compatible s t := by
  simp only [canCombine, inExc, compatible]
  constructor
  · intro h p hp q hq
    have hq_notexc : ¬ (q ∈ s.exc) := h q hq
    rw [mem_exc_iff] at hq_notexc
    push Not at hq_notexc
    exact hq_notexc.2 p hp
  · intro h q hq
    rw [mem_exc_iff]
    push Not
    exact ⟨fun hqs => (h q hqs q hq) (attack_self q),
           fun p hps => h p hps q hq⟩

/-- The excluded zone of a merge is the union of the parents' zones (definitionally). -/
lemma inExc_merge (s t : SubSol) (h : compatible s t) (p : Nat × Nat) :
    inExc (merge s t h) p ↔ inExc s p ∨ inExc t p := Iff.rfl

#print axioms merge

-- ── Sanity checks ────────────────────────────────────────────────────────────

def s1 : SubSol := singleton_subSol (0, 0)
def s2 : SubSol := singleton_subSol (1, 2)
def s3 : SubSol := singleton_subSol (0, 1)

example : compatible s1 s2 := by native_decide
#eval (merge s1 s2 (by native_decide)).positions
example : ¬ compatible s1 s3 := by native_decide
