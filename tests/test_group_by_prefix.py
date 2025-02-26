import random
import string
import time

import pytest
from async_s3.group_by_prefix import group_by_prefix


@pytest.mark.parametrize(
    "words, desired_group_count, expected_groups_count",
    [
        (
            [
                "apple",
                "apricot",
                "avocado",
                "banana",
                "blueberry",
                "blackberry",
                "cherry",
                "coconut",
            ],
            3,
            {"a", "b", "c"},
        ),
        (
            ["carrot", "celery", "cucumber", "cauliflower", "cabbage", "corn", "peas", "potato"],
            4,
            {"ca", "ce", "cu", "co", "p"},
        ),
        (
            ["dog", "cat", "bird", "fish", "hamster", "rabbit", "turtle", "snake"],
            2,
            {"d", "c", "b", "f", "h", "r", "t", "s"},
        ),
        (
            ["red", "orange", "yellow", "green", "blue", "indigo", "violet"],
            3,
            {"r", "o", "y", "g", "b", "i", "v"},
        ),
        (
            ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
            5,
            {"m", "t", "w", "f", "s"},
        ),
        (["12345!", "12345a", "12345b", "12345ab", "12345bc"], 3, {"12345!", "12345a", "12345b"}),
        (["0", "00", "000", "0000", "00000"], 20, {"0"}),
        (["0011", "002", "0021", "0012", "0022", "01", "012"], 3, {"001", "01", "002"}),
        (["00001", "00002", "000021", "00001", "00002", "00003"], 1, {"00001", "00002", "00003"}),
        (
            [
                "1",
                "qwerty1",
                "qwerty_asdfg0001",
                "qwerty_asdfg00012",
                "qwerty_asdfg00013",
                "qwerty_asdfg0002",
            ],
            4,
            {"qwerty_asdfg0001", "qwerty_asdfg0002", "1", "qwerty1"},
        ),
        (
            [
                "1",
                "qwerty1",
                "qwerty_asdfg0001",
                "qwerty_asdfg00012",
                "qwerty_asdfg00013",
                "qwerty_asdfg0002",
            ],
            3,
            {"qwerty1", "1", "qwerty_"},
        ),
        (
            [
                "1",
                "qwerty",
                "qwerty_asdfg0000",
                "qwerty_asdfg00001",
                "qwerty_asdfg000011",
                "qwerty_asdfg00002",
            ],
            2,
            {"1", "q"},
        ),
    ],
)
def test_group_by_prefix_cases(words, desired_group_count, expected_groups_count):
    result = group_by_prefix(words, desired_group_count)
    assert set(result) == expected_groups_count


def large_words_list_factory(words_count):
    """Generate words with a complex folder-like structure."""
    folders = ["folderA", "folderB", "folderC"]
    subfolders = ["sub1", "sub2", "sub3", "sub4"]
    num_files = words_count // (len(folders) * len(subfolders))
    files = ["file" + str(i).zfill(4) for i in range(num_files)]

    all_words = []
    for folder in folders:
        for subfolder in subfolders:
            for file in files:
                all_words.append(f"{folder}/{subfolder}/{file}")

    return all_words[:words_count]


def folder_structure_factory(words_count):
    """Generate words with different folder hierarchy."""
    folder_structure = {
        "folder001": ["nestedA", "nestedB", "nestedC"],
        "folder002": ["nestedA", "nestedB"],
        "folder003": ["nestedA", "nestedB", "nestedC", "nestedD", "nestedE"],
        "folder04": [],
    }

    all_words = []
    num_files = words_count // 10

    for folder, subfolders in folder_structure.items():
        for subfolder in subfolders:
            for _ in range(num_files):
                file_name = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
                all_words.append(f"{folder}/{subfolder}/{file_name}")

        if not subfolders:
            all_words.append(f"{folder}")

    return all_words


@pytest.mark.parametrize(
    "words_count, desired_group_count, expected_groups_count",
    [
        (100000, 10, 12),
    ],
)
def test_group_by_prefix_large_words_list(words_count, desired_group_count, expected_groups_count):
    words = large_words_list_factory(words_count)
    start = time.perf_counter()
    result = group_by_prefix(words, desired_group_count)
    end = time.perf_counter()
    print(f"{len(words)} words, execution time: {end - start}")
    assert len(result) == expected_groups_count


@pytest.mark.parametrize(
    "words_count, desired_group_count, expected_group_prefixes_count",
    [
        (10000, 11, 11),
    ],
)
def test_group_by_prefix_folder_structures(
    words_count, desired_group_count, expected_group_prefixes_count
):
    words = folder_structure_factory(words_count)
    result = group_by_prefix(words, desired_group_count)
    assert len(result) == expected_group_prefixes_count
