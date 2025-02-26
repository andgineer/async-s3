import asyncio
import os
import pathlib
import socket
import subprocess
import time
from unittest.mock import patch, call, MagicMock

import pytest
import yaml

import boto3
import aiobotocore
import aiobotocore.session


@pytest.fixture(scope="session", autouse=True)
def set_fake_aws_credentials():
    """Set fake AWS credentials for the test session."""
    os.environ["AWS_ACCESS_KEY_ID"] = "fake_access_key"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "fake_secret_key"
    os.environ["AWS_SESSION_TOKEN"] = "fake_session_token"
    yield


def create_s3_folder(bucket_name, structure, s3_client, parent_path=""):
    if isinstance(structure, list):
        for item in structure:
            for key, value in item.items():
                create_s3_objects(key, value, bucket_name, s3_client, parent_path)
    else:
        for key, value in structure.items():
            create_s3_objects(key, value, bucket_name, s3_client, parent_path)


def create_s3_objects(key, value, bucket_name, s3_client, parent_path):
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item == "EMPTY":
                folder_path = os.path.join(parent_path, key)
                s3_client.put_object(Bucket=bucket_name, Key=(folder_path + "/"))
            elif isinstance(item, str):
                file_path = os.path.join(parent_path, key, item)
                s3_client.put_object(Bucket=bucket_name, Key=file_path, Body="")
            elif isinstance(item, dict):
                folder_path = os.path.join(parent_path, key)
                create_s3_folder(bucket_name, item, s3_client, folder_path)
    elif isinstance(value, dict):
        folder_path = os.path.join(parent_path, key)
        create_s3_folder(bucket_name, value, s3_client, folder_path)


def wait_for_moto_server(s3_client, moto_server_process, retries=5, delay=1):
    for i in range(retries):
        try:
            s3_client.list_buckets()
            return True
        except Exception as exc:
            print(f"Attempt {i + 1}/{retries} failed: {exc}")
            stderr_output = moto_server_process.stderr.readline()
            if stderr_output:
                print(stderr_output.decode(), end="")
            time.sleep(delay)
    return False


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def fake_s3_server():
    """Starts a Moto server.

    Moto does not support mocking async clients, so we have to use fake server.

    Returns (<S3 client>, <factory for async S3 clients>).
    """
    port = get_free_port()
    moto_server_process = subprocess.Popen(
        ["moto_server", "-H", "0.0.0.0", f"-p{port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    endpoint_url = f"http://127.0.0.1:{port}"
    s3_client = boto3.client("s3", region_name="us-east-1", endpoint_url=endpoint_url)

    if not wait_for_moto_server(s3_client, moto_server_process):
        print("Failed to start the Moto server.")
        moto_server_process.terminate()
        moto_server_process.wait()
        pytest.fail("Failed to start Moto server")

    session = aiobotocore.session.get_session()
    yield (
        s3_client,
        lambda: session.create_client("s3", region_name="us-east-1", endpoint_url=endpoint_url),
    )

    # Teardown
    moto_server_process.terminate()
    moto_server_process.wait()


@pytest.fixture(scope="session")
def mock_s3_structure(request, fake_s3_server):
    s3_client, s3_async_client_factory = fake_s3_server
    HERE = pathlib.Path(__file__).parent

    # Load parameters
    bucket_structure_file = request.param.get("bucket_structure_file")
    get_s3_client_function = request.param.get("get_s3_client_function")
    bucket_name = request.param.get("bucket_name", "mock-bucket")

    with (HERE / "resources" / bucket_structure_file).open("r") as file:
        structure = yaml.safe_load(file)

    s3_client.create_bucket(Bucket=bucket_name)
    create_s3_folder(bucket_name, structure, s3_client)

    with patch(get_s3_client_function) as mock_client:
        mock_client.side_effect = s3_async_client_factory
        yield


class MockS3Client:
    def __init__(self, real_client):
        self.real_client = real_client
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def get_paginator(self, operation_name):
        self.calls.append(call.get_paginator(operation_name))
        paginator = MagicMock()
        paginator.paginate = self._mock_paginate()
        return paginator

    def _mock_paginate(self):
        async def async_generator(**kwargs):
            self.calls.append(call.get_paginator().paginate(**kwargs))
            async for result in self.real_client.get_paginator("list_objects_v2").paginate(
                **kwargs
            ):
                yield result

        return async_generator


@pytest.fixture
def s3_client_proxy(fake_s3_server, monkeypatch):
    """Record calls to the moto server.

    We use real external AWS server (moto) so we do not need mock but proxy.
    """
    _, s3_async_client_factory = fake_s3_server
    real_client = asyncio.run(s3_async_client_factory().__aenter__())
    mock_client = MockS3Client(real_client)

    monkeypatch.setattr("async_s3.s3_bucket_objects.get_s3_client", lambda: mock_client)
    yield mock_client
    asyncio.run(real_client.__aexit__(None, None, None))
