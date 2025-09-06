"""Tests for utility functions."""

import pytest
from unittest.mock import MagicMock
import botocore.exceptions

from async_s3.main import (
    split_s3_url,
    human_readable_size,
    validate_delimiter,
    print_summary,
    list_objects_with_progress,
)
from async_s3.group_by_prefix import find_longest_common_prefix
import click


def test_split_s3_url():
    """Test S3 URL splitting."""
    bucket, key = split_s3_url("s3://my-bucket/path/to/object")
    assert bucket == "my-bucket"
    assert key == "path/to/object"

    bucket, key = split_s3_url("s3://my-bucket/")
    assert bucket == "my-bucket"
    assert key == ""


def test_human_readable_size():
    """Test human readable size formatting."""
    assert human_readable_size(0) == "0.00 B"
    assert human_readable_size(512) == "512.00 B"
    assert human_readable_size(1024) == "1.00 KB"
    assert human_readable_size(1536) == "1.50 KB"
    assert human_readable_size(1048576) == "1.00 MB"
    assert human_readable_size(1073741824) == "1.00 GB"
    assert human_readable_size(1099511627776) == "1.00 TB"


def test_human_readable_size_precision():
    """Test human readable size with different precision."""
    assert human_readable_size(1536, 0) == "2 KB"
    assert human_readable_size(1536, 1) == "1.5 KB"
    assert human_readable_size(1536, 3) == "1.500 KB"


def test_validate_delimiter_valid():
    """Test delimiter validation with valid input."""
    ctx = MagicMock()
    param = MagicMock()

    assert validate_delimiter(ctx, param, "/") == "/"
    assert validate_delimiter(ctx, param, "-") == "-"
    assert validate_delimiter(ctx, param, "_") == "_"


def test_validate_delimiter_invalid():
    """Test delimiter validation with invalid input."""
    ctx = MagicMock()
    param = MagicMock()

    with pytest.raises(click.BadParameter):
        validate_delimiter(ctx, param, "")

    with pytest.raises(click.BadParameter):
        validate_delimiter(ctx, param, "ab")


def test_print_summary(capsys):
    """Test print summary function."""
    objects = [
        {"Key": "file1.txt", "Size": 1024},
        {"Key": "file2.txt", "Size": 2048},
    ]

    print_summary(objects)
    captured = capsys.readouterr()

    assert "Total objects: 2" in captured.out
    assert "3.00 KB" in captured.out


def test_find_longest_common_prefix_empty():
    """Test find_longest_common_prefix with empty list."""
    assert find_longest_common_prefix([]) == ""


def test_find_longest_common_prefix_single():
    """Test find_longest_common_prefix with single word."""
    assert find_longest_common_prefix(["hello"]) == "hello"


def test_find_longest_common_prefix_no_common():
    """Test find_longest_common_prefix with no common prefix."""
    assert find_longest_common_prefix(["apple", "banana", "cherry"]) == ""


def test_find_longest_common_prefix_full_match():
    """Test find_longest_common_prefix with identical strings."""
    assert find_longest_common_prefix(["test", "test", "test"]) == "test"


@pytest.mark.asyncio
async def test_list_objects_with_progress_client_error():
    """Test list_objects_with_progress handles ClientError."""
    from async_s3.s3_bucket_objects import S3BucketObjects

    s3_list = S3BucketObjects("test-bucket")

    # Mock the iter method to raise ClientError
    class MockAsyncIterator:
        def __init__(self):
            self.called = False

        def __aiter__(self):
            return self

        async def __anext__(self):
            if not self.called:
                self.called = True
                raise botocore.exceptions.ClientError(
                    {"Error": {"Code": "NoSuchBucket", "Message": "Bucket not found"}},
                    "ListObjectsV2",
                )
            raise StopAsyncIteration

    s3_list.iter = lambda *args, **kwargs: MockAsyncIterator()

    with pytest.raises(click.Abort):
        await list_objects_with_progress(s3_list, "prefix", None, None, "/")
