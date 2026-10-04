def merge_by_pointers(nums1: list[int], m: int, nums2: list[int], n: int) -> None:
    pointer_nums1 = m - 1
    pointer_nums2 = n - 1
    last_pointer_nums1 = m + n - 1

    while pointer_nums1 >= 0 and pointer_nums2 >= 0:
        if nums1[pointer_nums1] > nums2[pointer_nums2]:
            nums1[last_pointer_nums1] = nums1[pointer_nums1]
            pointer_nums1 -= 1
        else:
            nums1[last_pointer_nums1] = nums2[pointer_nums2]
            pointer_nums2 -= 1
        last_pointer_nums1 -= 1

    # Если в nums2 остались элементы — дописываем их
    while pointer_nums2 >= 0:
        nums1[last_pointer_nums1] = nums2[pointer_nums2]
        pointer_nums2 -= 1
        last_pointer_nums1 -= 1


if __name__ == "__main__":
    nums1 = [1, 2, 3, 5, 0, 0, 0, 0]
    nums2 = [5, 6, 7, 8]
    merge_by_pointers(nums1, 3, nums2, 4)
    print(nums1)  # [1, 2, 3, 4, 5, 6, 7, 8]
