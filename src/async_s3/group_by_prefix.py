def group_by_prefix(words: list[str], desired_group_count: int) -> list[str]:  # noqa: C901
    """Groups words by prefixes to create a desired number of word groups.

    Try to create the desired number of groups if possible.
    """
    words.sort()

    common_prefix = find_longest_common_prefix(words)
    common_prefix_length = len(common_prefix)
    prefix_groups = {}  # {prefix: (start_index, count, can_split)}

    for i, s in enumerate(words):
        if len(s) <= common_prefix_length:
            prefix_groups = {s: [0, len(words), True]}
            break
        prefix = common_prefix + s[common_prefix_length]
        if prefix not in prefix_groups:
            prefix_groups[prefix] = [i, 1, True]
        else:
            prefix_groups[prefix][1] += 1

    def split_prefix_groups(groups: dict[str, list[int]]) -> dict[str, list[int]]:
        new_groups = {}
        for prefix, (start_index, count, can_split) in groups.items():
            if not can_split or count < max(2, (len(words) // desired_group_count)):
                new_groups[prefix] = [start_index, count, False]
                continue

            subgroups = {}
            can_further_split = True
            for i in range(start_index, start_index + count):
                s = words[i]
                if len(prefix) < len(s):
                    new_prefix = prefix + s[len(prefix)]
                else:
                    can_further_split = False
                    break  # A string with the length of the group prefix prevents splitting
                if new_prefix not in subgroups:
                    subgroups[new_prefix] = [i, 1, True]
                else:
                    subgroups[new_prefix][1] += 1

            if can_further_split and len(subgroups) < count:
                new_groups.update(subgroups)
            else:
                new_groups[prefix] = [start_index, count, False]

        return new_groups

    while len(prefix_groups) < desired_group_count and any(
        can_split for _, _, can_split in prefix_groups.values()
    ):
        prefix_groups = split_prefix_groups(prefix_groups)

    return list(prefix_groups.keys())


def find_longest_common_prefix(words: list[str]) -> str:
    """Finds the longest common prefix among a list of words."""
    if not words:
        return ""

    def is_common_prefix(length: int) -> bool:
        prefix = words[0][:length]
        return all(s.startswith(prefix) for s in words)

    min_length = min(len(s) for s in words)

    low, high = 0, min_length
    while low <= high:
        mid = (low + high) // 2
        if is_common_prefix(mid):
            low = mid + 1
        else:
            high = mid - 1

    return words[0][: (low + high) // 2]
