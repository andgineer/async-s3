from unittest.mock import call

import pytest
from async_s3 import S3BucketObjects


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_s3_structure",
    [
        {
            "bucket_structure_file": "bucket_keys.yml",
            "get_s3_client_function": "async_s3.s3_bucket_objects.get_s3_client",
        }
    ],
    indirect=True,
)
async def test_s3_bucket_objects_functional(mock_s3_structure):
    walker = S3BucketObjects("mock-bucket")
    keys = sorted([object["Key"] for object in await walker.list(prefix="root/")])

    expected_keys = sorted(
        [
            "root/data01/image01.png",
            "root/data01/images/img11.jpg",
            "root/data01/docs/doc12.pdf",
            "root/data01/archives/archive13a.zip",
            "root/data01/archives/archive13b.zip",
            "root/data02/report02.docx",
            "root/data02/reports/report21.docx",
            "root/data02/logs/log22.txt",
            "root/data02/scripts/script23.py",
            "root/data03/video03a.mp4",
            "root/data03/video03b.mp4",
            "root/data03/video03c.mp4",
        ]
    )

    assert sorted(keys) == sorted(expected_keys)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_s3_structure",
    [
        {
            "bucket_structure_file": "bucket_keys.yml",
            "get_s3_client_function": "async_s3.s3_bucket_objects.get_s3_client",
            "bucket_name": "mock-bucket",
        }
    ],
    indirect=True,
)
async def test_s3_bucket_objects_with_max_level(s3_client_proxy, mock_s3_structure):
    walker = S3BucketObjects("mock-bucket")

    objects = await walker.list(prefix="root/", max_level=2)
    expected_keys = {
        "root/data01/image01.png",
        "root/data01/images/img11.jpg",
        "root/data01/docs/doc12.pdf",
        "root/data01/archives/archive13a.zip",
        "root/data01/archives/archive13b.zip",
        "root/data02/report02.docx",
        "root/data02/reports/report21.docx",
        "root/data02/logs/log22.txt",
        "root/data02/scripts/script23.py",
        "root/data03/video03a.mp4",
        "root/data03/video03b.mp4",
        "root/data03/video03c.mp4",
    }
    keys = [obj["Key"] for obj in objects]
    assert set(keys) == expected_keys
    seen_keys = set()
    duplicates = [key for key in keys if key in seen_keys or seen_keys.add(key)]
    assert not duplicates, f"Found duplicate keys: {duplicates}"

    # Check calls to the S3 client
    expected_calls = [
        call.get_paginator("list_objects_v2"),
        call.get_paginator().paginate(Bucket="mock-bucket", Prefix="root/", Delimiter="/"),
        call.get_paginator("list_objects_v2"),
        call.get_paginator().paginate(Bucket="mock-bucket", Prefix="root/data01/", Delimiter="/"),
        call.get_paginator("list_objects_v2"),
        call.get_paginator().paginate(Bucket="mock-bucket", Prefix="root/data02/", Delimiter="/"),
        call.get_paginator("list_objects_v2"),
        call.get_paginator().paginate(Bucket="mock-bucket", Prefix="root/data03/", Delimiter="/"),
        call.get_paginator("list_objects_v2"),
        call.get_paginator().paginate(Bucket="mock-bucket", Prefix="root/data04/", Delimiter="/"),
        call.get_paginator("list_objects_v2"),
        call.get_paginator().paginate(Bucket="mock-bucket", Prefix="root/data01/archives/"),
        call.get_paginator("list_objects_v2"),
        call.get_paginator().paginate(Bucket="mock-bucket", Prefix="root/data01/docs/"),
        call.get_paginator("list_objects_v2"),
        call.get_paginator().paginate(Bucket="mock-bucket", Prefix="root/data01/images/"),
        call.get_paginator("list_objects_v2"),
        call.get_paginator().paginate(Bucket="mock-bucket", Prefix="root/data01/temp/"),
        call.get_paginator("list_objects_v2"),
        call.get_paginator().paginate(Bucket="mock-bucket", Prefix="root/data02/logs/"),
        call.get_paginator("list_objects_v2"),
        call.get_paginator().paginate(Bucket="mock-bucket", Prefix="root/data02/reports/"),
        call.get_paginator("list_objects_v2"),
        call.get_paginator().paginate(Bucket="mock-bucket", Prefix="root/data02/scripts/"),
    ]
    assert s3_client_proxy.calls == expected_calls


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_s3_structure",
    [
        {
            "bucket_structure_file": "bucket_keys.yml",
            "get_s3_client_function": "async_s3.s3_bucket_objects.get_s3_client",
            "bucket_name": "mock-bucket",
        }
    ],
    indirect=True,
)
async def test_s3_bucket_objects_with_max_folders(s3_client_proxy, mock_s3_structure):
    walker = S3BucketObjects("mock-bucket")

    objects = await walker.list(prefix="root/", max_folders=2)
    expected_keys = {
        "root/data01/image01.png",
        "root/data01/images/img11.jpg",
        "root/data01/docs/doc12.pdf",
        "root/data01/archives/archive13a.zip",
        "root/data01/archives/archive13b.zip",
        "root/data02/report02.docx",
        "root/data02/reports/report21.docx",
        "root/data02/logs/log22.txt",
        "root/data02/scripts/script23.py",
        "root/data03/video03a.mp4",
        "root/data03/video03b.mp4",
        "root/data03/video03c.mp4",
    }
    keys = [obj["Key"] for obj in objects]
    assert set(keys) == expected_keys
    seen_keys = set()
    duplicates = [key for key in keys if key in seen_keys or seen_keys.add(key)]
    assert not duplicates, f"Found duplicate keys: {duplicates}"

    # Check calls to the S3 client
    expected_calls = [
        call.get_paginator("list_objects_v2"),
        call.get_paginator().paginate(Bucket="mock-bucket", Prefix="root/", Delimiter="/"),
        call.get_paginator("list_objects_v2"),
        call.get_paginator().paginate(Bucket="mock-bucket", Prefix="root/data01"),
        call.get_paginator("list_objects_v2"),
        call.get_paginator().paginate(Bucket="mock-bucket", Prefix="root/data02"),
        call.get_paginator("list_objects_v2"),
        call.get_paginator().paginate(Bucket="mock-bucket", Prefix="root/data03"),
        call.get_paginator("list_objects_v2"),
        call.get_paginator().paginate(Bucket="mock-bucket", Prefix="root/data04"),
    ]
    assert s3_client_proxy.calls == expected_calls


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_s3_structure",
    [
        {
            "bucket_structure_file": "bucket_keys.yml",
            "get_s3_client_function": "async_s3.s3_bucket_objects.get_s3_client",
            "bucket_name": "mock-bucket",
        }
    ],
    indirect=True,
)
async def test_s3_bucket_objects_delimiter(s3_client_proxy, mock_s3_structure):
    walker = S3BucketObjects("mock-bucket")

    objects = await walker.list(prefix="root/", max_folders=2, delimiter="a")
    keys = [obj["Key"] for obj in objects]
    from pprint import pprint

    pprint(keys)

    expected_keys = {
        "root/data01/image01.png",
        "root/data01/images/img11.jpg",
        "root/data01/temp/",
        "root/data01/docs/doc12.pdf",
        "root/data01/archives/archive13a.zip",
        "root/data01/archives/archive13b.zip",
        "root/data02/report02.docx",
        "root/data02/reports/report21.docx",
        "root/data02/logs/log22.txt",
        "root/data02/scripts/script23.py",
        "root/data03/video03a.mp4",
        "root/data03/video03b.mp4",
        "root/data03/video03c.mp4",
        "root/data04/",
    }
    pprint(expected_keys)

    assert set(keys) == expected_keys
    seen_keys = set()
    duplicates = [key for key in keys if key in seen_keys or seen_keys.add(key)]
    assert not duplicates, f"Found duplicate keys: {duplicates}"

    # Check calls to the S3 client
    expected_calls = [
        call.get_paginator("list_objects_v2"),
        call.get_paginator().paginate(Bucket="mock-bucket", Prefix="root/", Delimiter="a"),
        call.get_paginator("list_objects_v2"),
        call.get_paginator().paginate(Bucket="mock-bucket", Prefix="root/da", Delimiter="a"),
        call.get_paginator("list_objects_v2"),
        call.get_paginator().paginate(Bucket="mock-bucket", Prefix="root/data", Delimiter="a"),
        call.get_paginator("list_objects_v2"),
        call.get_paginator().paginate(Bucket="mock-bucket", Prefix="root/data01"),
        call.get_paginator("list_objects_v2"),
        call.get_paginator().paginate(Bucket="mock-bucket", Prefix="root/data03"),
    ]
    assert s3_client_proxy.calls == expected_calls
