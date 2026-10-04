def target_by_bruteforce(nums: list[int], target: int) -> list[int]:
    final_list = []
    n = len(nums)

    for left_pointer in range(n):
        for right_pointer in range(left_pointer + 1, n):
            if nums[left_pointer] + nums[right_pointer] == target:
                final_list.append((left_pointer, right_pointer))

    return final_list


def target_by_sort(nums: list[int], target: int) -> list[tuple[int, int]]:
    result_list = []
    indexed_nums = [(num, i) for i, num in enumerate(nums)]
    indexed_nums.sort(key=lambda x: x[0])

    left_pointer = 0
    right_pointer = len(indexed_nums) - 1

    while left_pointer < right_pointer:
        current_sum = indexed_nums[left_pointer][0] + indexed_nums[right_pointer][0]
        if current_sum == target:
            result_list.append(
                (indexed_nums[left_pointer][1], indexed_nums[right_pointer][1])
            )
            left_pointer += 1
            right_pointer -= 1
        elif current_sum < target:
            left_pointer += 1
        else:
            right_pointer -= 1

    return result_list


def target_by_hashmap(nums: list[int], target: int) -> list[int]:
    result_list = []
    seen = {}
    for i, current_num in enumerate(nums):
        delta = target - current_num
        if delta in seen:
            result_list.append((seen[delta], i))
        seen[current_num] = i

    return result_list

if __name__ == "__main__":
    nums = [2, 7, 11, 15, 3, 8, 1]
    # result = target_by_bruteforce(nums, 9)
    # result = target_by_sort(nums, 9)
    result = target_by_hashmap(nums, 9)
    print(result)
