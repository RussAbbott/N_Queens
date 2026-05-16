def solve_n_queens(n):
    solutions = []

    def is_safe(board, row, col):
        for r in range(row):
            c = board[r]
            if c == col or abs(c - col) == abs(r - row):
                return False
        return True

    def backtrack(board, row):
        if row == n:
            solutions.append(board[:])
            return
        for col in range(n):
            if is_safe(board, row, col):
                board[row] = col
                backtrack(board, row + 1)
                board[row] = -1

    backtrack([-1] * n, 0)
    return solutions


def print_board(solution, n):
    for row in range(n):
        line = ""
        for col in range(n):
            line += "Q " if solution[row] == col else ". "
        print(line)


def main():
    while True:
        try:
            n = int(input("Enter the number of queens: "))
            if n < 1:
                print("Please enter a positive integer.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a positive integer.")

    solutions = solve_n_queens(n)

    if not solutions:
        print(f"\nNo solutions exist for {n} queens.")
        return

    print(f"\nFound {len(solutions)} solution(s) for {n} queens.\n")

    for i, solution in enumerate(solutions, 1):
        print(f"Solution {i}:")
        print_board(solution, n)
        print()


if __name__ == "__main__":
    main()
