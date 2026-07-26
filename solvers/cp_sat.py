def solve_n_queens_cp(n):
    """
    Find all solutions to the N-Queens problem using the OR-Tools CP-SAT solver.
    OR-Tools is installed automatically on first use if not already present.

    A problem specification, called a Model, consists of decision variables and
    constraints. A decision variable is a variable that can take on values from
    a specified domain. A constraint is a relation among decision variables that
    must hold.

    For this problem, n decision variables represent the positions of n queens.
    These are stored in the list queens, where queens[r] is the column of the
    queen in row r as in the previous solutions.

    In this problem, the only constraint type is all_different(List), which
    requires that all decisions variables in the list assume distinct values.
    For example, all_different(queens) requires that all the queens be different.

    Given a problem specification, the solver uses constraint programming
    techniques to search the solution space for valid assignments.

    The implementation below is straightforward, but the library offers many
    knobs to turn for performance tuning.

    Parameters:
        n: int
            Number of queens (and board size).

    Returns:
        List[List[int]]: list of solutions, each a list of n column indices
        where solution[r] is the column of the queen in row r.
    """
    from ortools.sat.python import cp_model
    model = cp_model.CpModel()

    # Each queens[r] is a decision variable representing the column of the queen
    # in row r. Its domain is 0..n-1. The string "qr" is a label used in solver
    # diagnostics.
    queens = [model.new_int_var(0, n - 1, f"q{r}") for r in range(n)]

    # No two queens in the same column.
    model.add_all_different(queens)

    # No two queens on the same diagonal. Two queens at (r1,c1) and (r2,c2)
    # share a diagonal when |c1-c2| == |r1-r2|, i.e. when c+r or c-r is equal.
    # Requiring all col+row values to be distinct blocks one diagonal direction,
    # and requiring all col-row values to be distinct blocks the other.
    model.add_all_different([queens[r] + r for r in range(n)])
    model.add_all_different([queens[r] - r for r in range(n)])

    solver = cp_model.CpSolver()
    solutions = []
    solver.parameters.enumerate_all_solutions = True

    # CpSolverSolutionCallback is an OR-Tools class whose instances are expected
    # to implement the on_solution_callback() method--which is called whenever a
    # solution is found. Such an instance has access to the values of the decision
    # variables via the value() method. Those values are the found solution, i.e.,
    # they satisfy the specified constraints.
    #
    # Our SolutionCollector is a subclass of CpSolverSolutionCallback. Its
    # on_solution_callback() method adds each found solution to the list of
    # solutions.
    class SolutionCollector(cp_model.CpSolverSolutionCallback):
        def on_solution_callback(self):
            solutions.append([self.value(queens[r]) for r in range(n)])

    solver.solve(model, SolutionCollector())
    return solutions
