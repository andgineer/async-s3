"""Tests for error handling scenarios."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
import botocore.exceptions
from click.testing import CliRunner

from async_s3 import S3BucketObjects
from async_s3.main import as3


class TestS3BucketObjectsErrorHandling:
    """Test error handling in S3BucketObjects."""

    @pytest.mark.asyncio
    async def test_iter_with_client_error(self):
        """Test iter method handles AWS client errors gracefully."""
        bucket = S3BucketObjects("test-bucket")

        with patch("async_s3.s3_bucket_objects.get_s3_client") as mock_client:
            # Mock client that raises error
            mock_s3 = MagicMock()
            mock_s3.__aenter__ = AsyncMock(return_value=mock_s3)
            mock_s3.__aexit__ = AsyncMock(return_value=None)

            mock_paginator = MagicMock()
            mock_s3.get_paginator.return_value = mock_paginator

            async def mock_paginate(**kwargs):
                raise botocore.exceptions.ClientError(
                    {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "ListObjectsV2"
                )

            mock_paginator.paginate = mock_paginate
            mock_client.return_value = mock_s3

            # Should not raise - errors are handled by calling code
            results = []
            try:
                async for page in bucket.iter("prefix"):
                    results.append(page)
            except botocore.exceptions.ClientError:
                pass  # Expected for this test

    @pytest.mark.asyncio
    async def test_semaphore_release_on_exception(self):
        """Test semaphore is properly released when task creation fails."""
        bucket = S3BucketObjects("test-bucket", parallelism=1)

        with patch("async_s3.s3_bucket_objects.get_s3_client") as mock_client:
            mock_s3 = MagicMock()
            mock_s3.__aenter__ = AsyncMock(return_value=mock_s3)
            mock_s3.__aexit__ = AsyncMock(return_value=None)

            # Force task creation to fail
            with patch("asyncio.create_task", side_effect=RuntimeError("Task creation failed")):
                mock_client.return_value = mock_s3

                try:
                    async for _ in bucket.iter("prefix"):
                        pass
                except RuntimeError:
                    pass

                # Semaphore should be available again
                assert bucket.semaphore._value == 1


class TestCLIErrorHandling:
    """Test CLI error handling."""

    def test_ls_invalid_url_formats(self):
        """Test various invalid S3 URL formats."""
        runner = CliRunner()

        invalid_urls = ["http://bucket/key", "ftp://bucket/key", "bucket/key", "invalid_url"]

        for url in invalid_urls:
            result = runner.invoke(as3, ["ls", url])
            assert result.exit_code != 0
            assert "Invalid S3 URL" in result.output

    def test_du_invalid_url_formats(self):
        """Test various invalid S3 URL formats for du command."""
        runner = CliRunner()

        invalid_urls = ["https://bucket/key", "bucket", "invalid_url"]

        for url in invalid_urls:
            result = runner.invoke(as3, ["du", url])
            assert result.exit_code != 0
            assert "Invalid S3 URL" in result.output

    def test_delimiter_validation_edge_cases(self):
        """Test delimiter validation with edge cases."""
        runner = CliRunner()

        # Empty delimiter
        result = runner.invoke(as3, ["ls", "s3://bucket/key", "--delimiter", ""])
        assert result.exit_code != 0
        assert "Delimiter must be exactly one" in result.output

        # Multi-character delimiter
        result = runner.invoke(as3, ["ls", "s3://bucket/key", "--delimiter", "ab"])
        assert result.exit_code != 0
        assert "Delimiter must be exactly one" in result.output


class TestAsyncResourceCleanup:
    """Test proper cleanup of async resources."""

    @pytest.mark.asyncio
    async def test_task_cleanup_on_cancellation(self):
        """Test that tasks are properly cleaned up when cancelled."""
        bucket = S3BucketObjects("test-bucket")

        with patch("async_s3.s3_bucket_objects.get_s3_client") as mock_client:
            mock_s3 = MagicMock()
            mock_s3.__aenter__ = AsyncMock(return_value=mock_s3)
            mock_s3.__aexit__ = AsyncMock(return_value=None)

            # Mock paginator that returns data slowly
            mock_paginator = MagicMock()
            mock_s3.get_paginator.return_value = mock_paginator

            async def slow_paginate(**kwargs):
                await asyncio.sleep(0.1)  # Simulate slow response
                yield {"Contents": [{"Key": "test", "Size": 100}]}

            mock_paginator.paginate = slow_paginate
            mock_client.return_value = mock_s3

            # Start iteration and cancel it
            async def run_and_cancel():
                async for _ in bucket.iter("prefix"):
                    raise asyncio.CancelledError()

            with pytest.raises(asyncio.CancelledError):
                await run_and_cancel()


@pytest.mark.asyncio
async def test_empty_bucket_handling():
    """Test handling of empty buckets."""
    bucket = S3BucketObjects("empty-bucket")

    with patch("async_s3.s3_bucket_objects.get_s3_client") as mock_client:
        mock_s3 = MagicMock()
        mock_s3.__aenter__ = AsyncMock(return_value=mock_s3)
        mock_s3.__aexit__ = AsyncMock(return_value=None)

        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator

        async def empty_paginate(**kwargs):
            # Empty bucket - no Contents or CommonPrefixes
            yield {}

        mock_paginator.paginate = empty_paginate
        mock_client.return_value = mock_s3

        results = await bucket.list("prefix")
        assert results == []
