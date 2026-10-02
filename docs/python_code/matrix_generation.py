def matrix_round(n: int, m:int)-> list[list[int]]:
    outer_m = []
    for i in range(n):
        inner_m = []
        for j in range(m):
            inner_m.append(i*m + j + 1)
        outer_m.append(inner_m)
    return outer_m

def matrix_gen(n: int, m: int) -> list[list[int]]:
    return [[i * m + j + 1 for j in range(m)] for i in range(n)]


if __name__ == "__main__":
    n, m = 5, 7
    m1 = matrix_gen(n, m)
    m2 = matrix_round(n, m)
    print(m1, m2)