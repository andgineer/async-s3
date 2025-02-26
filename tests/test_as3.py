from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from async_s3 import __version__
from async_s3.main import as3, list_objects_async
from click.testing import CliRunner


def test_version():
    assert __version__


def test_as3_version():
    runner = CliRunner()
    result = runner.invoke(as3, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


@pytest.fixture
def mock_list_objects_async():
    with patch("async_s3.main.list_objects_async", new_callable=AsyncMock) as mock:
        yield mock


def test_as3_ls_command(mock_list_objects_async):
    mock_list_objects_async.return_value = [
        {"Key": "file1.txt", "Size": 1234},
        {"Key": "file2.txt", "Size": 5678},
    ]

    runner = CliRunner()
    result = runner.invoke(as3, ["ls", "s3://bucket/key"])

    assert result.exit_code == 0
    assert "file1.txt" in result.output
    assert "file2.txt" in result.output


def test_as3_du_command(mock_list_objects_async):
    mock_list_objects_async.return_value = [
        {"Key": "file1.txt", "Size": 1234},
        {"Key": "file2.txt", "Size": 5678},
    ]

    runner = CliRunner()
    result = runner.invoke(as3, ["du", "s3://bucket/key"])

    assert result.exit_code == 0
    assert "Total objects: 2" in result.output
    assert "size: 6.75 KB" in result.output


def test_as3_invalid_s3_url_ls():
    runner = CliRunner()
    result = runner.invoke(as3, ["ls", "invalid_url"])

    assert result.exit_code != 0
    assert "Invalid S3 URL. It should start with s3://" in result.output


def test_as3_invalid_s3_url_du():
    runner = CliRunner()
    result = runner.invoke(as3, ["du", "invalid_url"])

    assert result.exit_code != 0
    assert "Invalid S3 URL. It should start with s3://" in result.output


async def mock_iter(pages):
    for item in pages:
        yield item


@pytest.mark.asyncio
async def test_list_objects_async_no_repeat():
    mock_result = [
        {"Key": "file1.txt", "Size": 1234},
        {"Key": "file2.txt", "Size": 5678},
    ]

    with patch("async_s3.main.S3BucketObjects") as MockS3BucketObjects:
        instance = MockS3BucketObjects.return_value
        instance.iter = MagicMock(side_effect=lambda *args, **kwargs: mock_iter([mock_result, []]))

        s3_url = "s3://bucket/key"
        max_level = 1
        max_folders = 1
        repeat = 1
        parallelism = 100
        delimiter = "/"

        result = await list_objects_async(
            s3_url, max_level, max_folders, repeat, parallelism, delimiter
        )

        assert result == mock_result
        assert instance.iter.call_count == repeat


@pytest.mark.asyncio
async def test_list_objects_async_repeat():
    mock_result = [
        {"Key": "file1.txt", "Size": 1234},
        {"Key": "file2.txt", "Size": 5678},
    ]

    with patch("async_s3.main.S3BucketObjects") as MockS3BucketObjects:
        s3_url = "s3://bucket/key"
        max_level = 1
        max_folders = 1
        repeat = 3
        parallelism = 100
        delimiter = "/"

        instance = MockS3BucketObjects.return_value
        instance.iter = MagicMock(side_effect=lambda *args, **kwargs: mock_iter([mock_result, []]))

        result = await list_objects_async(
            s3_url, max_level, max_folders, repeat, parallelism, delimiter
        )

        assert result == mock_result
        assert instance.iter.call_count == repeat
