import asyncio
import functools
from collections.abc import AsyncIterator
from typing import Any, Optional

import aiobotocore.client
import aiobotocore.session
from botocore.config import Config

from async_s3.group_by_prefix import group_by_prefix

DEFAULT_PARALLELISM = 100


@functools.lru_cache
def create_session() -> aiobotocore.session.AioSession:
    """Create a session object."""
    return aiobotocore.session.get_session()


def get_s3_client() -> aiobotocore.client.AioBaseClient:
    """Get S3 client."""
    session = create_session()
    config = Config(
        retries={"max_attempts": 3, "mode": "adaptive"},
    )
    return session.create_client("s3", config=config)


class S3BucketObjects:
    def __init__(self, bucket: str, *, parallelism: int = DEFAULT_PARALLELISM) -> None:
        """Initialize the S3BucketObjects object.

        bucket: The name of the S3 bucket.
        parallelism: The maximum number of concurrent requests to AWS S3.
        """
        self._bucket = bucket
        self.semaphore = asyncio.Semaphore(parallelism)

    async def _list_objects(  # noqa: PLR0913
        self,
        s3_client: aiobotocore.client.AioBaseClient,
        prefix: str,
        current_depth: int,
        max_level: Optional[int],
        max_folders: Optional[int],
        delimiter: str,
        objects_keys: set[str],
        queue: asyncio.Queue[list[dict[str, Any]]],
        active_tasks: set[asyncio.Task[None]],
    ) -> None:
        """Emit object pages to the queue."""
        paginator = s3_client.get_paginator("list_objects_v2")
        prefixes = []

        params = {"Bucket": self._bucket, "Prefix": prefix}
        if (current_depth != -1) and (max_level is None or current_depth < max_level):
            params["Delimiter"] = delimiter

        async for page in paginator.paginate(**params):
            objects = page.get("Contents", [])
            new_keys = {
                obj["Key"]
                for obj in objects
                if not obj["Key"].endswith(delimiter) and obj["Key"] not in objects_keys
            }
            cleared_objects = [obj for obj in objects if obj["Key"] in new_keys]
            objects_keys.update(new_keys)
            await queue.put(cleared_objects)

            if "Delimiter" in params:
                prefixes.extend([prefix["Prefix"] for prefix in page.get("CommonPrefixes", [])])

        level = -1 if current_depth == -1 else current_depth + 1
        if max_folders is not None and (len(prefixes) > max_folders):
            prefixes = list(group_by_prefix(prefixes, max_folders))
            level = -1

        for folder in prefixes:
            await self.semaphore.acquire()
            try:
                task = asyncio.create_task(
                    self._list_objects(
                        s3_client,
                        folder,
                        level,
                        max_level,
                        max_folders,
                        delimiter,
                        objects_keys,
                        queue,
                        active_tasks,
                    ),
                )
            except Exception:
                self.semaphore.release()
                raise
            active_tasks.add(task)
            task.add_done_callback(lambda t: self._task_done(t, active_tasks, queue))

    async def iter(
        self,
        prefix: str = "/",
        *,
        max_level: Optional[int] = None,
        max_folders: Optional[int] = None,
        delimiter: str = "/",
    ) -> AsyncIterator[list[dict[str, Any]]]:
        """Generator that yields objects in the bucket with the given prefix.

        Yield objects by partial chunks (list of AWS S3 object dicts) as they
         are collected from AWS asynchronously.

        max_level: The maximum folders depth to traverse in separate requests.
        If None, traverse all levels.
        max_folders: The maximum number of folders to load in separate requests.
        If None, requests all folders.
        Otherwise, the folders are grouped by prefixes before loading in separate requests.
        Try to group in the given number of folders if possible.
        delimiter: The delimiter for "folders".
        """
        # if we group by prefixes, some objects may be listed multiple times
        # to avoid this, we store the keys of the objects already listed
        objects_keys: set[str] = set()

        # queue to store the objects pages from the tasks
        queue: asyncio.Queue[list[dict[str, Any]]] = asyncio.Queue()

        # set to keep track of active tasks
        active_tasks: set[asyncio.Task[None]] = set()

        async with get_s3_client() as s3_client:
            await self.semaphore.acquire()
            try:
                root_task = asyncio.create_task(
                    self._list_objects(
                        s3_client,
                        prefix,
                        0,
                        max_level,
                        max_folders,
                        delimiter,
                        objects_keys,
                        queue,
                        active_tasks,
                    ),
                )
            except Exception:
                self.semaphore.release()
                raise
            active_tasks.add(root_task)
            root_task.add_done_callback(lambda t: self._task_done(t, active_tasks, queue))

            while active_tasks:
                try:
                    page = await queue.get()
                    if page:
                        yield page
                except asyncio.QueueEmpty:
                    await asyncio.sleep(0)

    def _task_done(
        self,
        task: asyncio.Task[None],
        active_tasks: set[asyncio.Task[None]],
        queue: asyncio.Queue[list[dict[str, Any]]],
    ) -> None:
        """Callback for when a task is done."""

        async def async_task_done() -> None:
            active_tasks.discard(task)
            self.semaphore.release()
            await queue.put([])  # signal that the task is done

        asyncio.create_task(async_task_done())

    async def list(
        self,
        prefix: str = "/",
        *,
        max_level: Optional[int] = None,
        max_folders: Optional[int] = None,
        delimiter: str = "/",
    ) -> list[dict[str, Any]]:
        """List all objects in the bucket with the given prefix.

        max_level: The maximum folders depth to traverse in separate requests.
        If None, traverse all levels.
        max_folders: The maximum number of folders to load in separate requests.
        If None, requests all folders.
        Otherwise, the folders are grouped by prefixes before loading in separate requests.
        Try to group to the given `max_folders` if possible.
        delimiter: The delimiter for "folders".
        """
        objects = []
        async for objects_page in self.iter(
            prefix,
            max_level=max_level,
            max_folders=max_folders,
            delimiter=delimiter,
        ):
            objects.extend(objects_page)
        return objects
