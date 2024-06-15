"""async-s3."""

import asyncio
import time
from typing import Iterable, Dict, Any, Optional, Callable
import rich_click as click
import botocore.exceptions
from async_s3.s3_bucket_objects import S3BucketObjects
from async_s3 import __version__


click.rich_click.USE_MARKDOWN = True

S3PROTO = "s3://"


def error(message: str) -> None:
    """Print an error message and exit."""
    click.secho(message, fg="red", bold=True)
    raise click.Abort()


def print_summary(objects: Iterable[Dict[str, Any]]) -> None:
    """Print a summary of the objects."""
    total_size = sum(obj["Size"] for obj in objects)
    message = (
        f"{click.style('Total objects: ', fg='green')}"
        f"{click.style(str(len(list(objects))), fg='green', bold=True)}, "
        f"{click.style('size: ', fg='green')}"
        f"{click.style(human_readable_size(total_size), fg='green', bold=True)}"
    )
    click.echo(message)


@click.group()
@click.version_option(version=__version__, prog_name="as3")
def as3() -> None:
    """Async S3."""


def list_objects_options(func: Callable[[Any], None]) -> Callable[[Any], None]:
    """Add common options to commands using list_objects."""
    func = click.argument("s3_url")(func)
    func = click.option(
        "--max-level",
        "-l",
        type=int,
        default=None,
        help="The maximum folders level to traverse in separate requests. By default traverse all levels.",
    )(func)
    func = click.option(
        "--max-folders",
        "-f",
        type=int,
        default=None,
        help="The maximum number of folders to list in one request. By default list all folders.",
    )(func)
    func = click.option(
        "--repeat",
        "-r",
        type=int,
        default=1,
        help="Repeat the operation multiple times to average elapsed time. By default repeat once.",
    )(func)
    func = click.option(
        "--parallelism",
        "-p",
        type=int,
        default=100,
        help="The maximum number of concurrent requests to AWS S3. By default 100.",
    )(func)
    func = click.option(
        "--delimiter",
        "-d",
        type=str,
        default="/",
        help="Delimiter for 'folders'. Default is '/'.",
    )(func)
    return func


@list_objects_options
@as3.command()
def ls(  # pylint: disable=too-many-arguments
    s3_url: str,
    max_level: Optional[int],
    max_folders: Optional[int],
    repeat: int,
    parallelism: int,
    delimiter: str,
) -> None:
    """
    List objects in an S3 bucket.

    Example:
    as3 ls s3://bucket/key
    """
    if not s3_url.startswith(S3PROTO):
        error("Invalid S3 URL. It should start with s3://")

    objects = list_objects(
        s3_url,
        max_level=max_level,
        max_folders=max_folders,
        repeat=repeat,
        parallelism=parallelism,
        delimiter=delimiter,
    )
    click.echo("\n".join([obj["Key"] for obj in objects]))
    print_summary(objects)


@list_objects_options
@as3.command()
def du(  # pylint: disable=too-many-arguments
    s3_url: str,
    max_level: Optional[int],
    max_folders: Optional[int],
    repeat: int,
    parallelism: int,
    delimiter: str,
) -> None:
    """
    Show count and size for objects in an S3 bucket.

    Example:
    as3 du s3://bucket/key
    """
    if not s3_url.startswith(S3PROTO):
        error("Invalid S3 URL. It should start with s3://")

    objects = list_objects(
        s3_url,
        max_level=max_level,
        max_folders=max_folders,
        repeat=repeat,
        parallelism=parallelism,
        delimiter=delimiter,
    )
    print_summary(objects)


def human_readable_size(size: float, decimal_places: int = 2) -> str:
    """Convert bytes to a human-readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"


def list_objects(  # pylint: disable=too-many-arguments
    s3_url: str,
    max_level: Optional[int] = None,
    max_folders: Optional[int] = None,
    repeat: int = 1,
    parallelism: int = 100,
    delimiter: str = "/",
) -> Iterable[Dict[str, Any]]:
    """List objects in an S3 bucket."""
    return asyncio.run(
        list_objects_async(
            s3_url,
            max_level=max_level,
            max_folders=max_folders,
            repeat=repeat,
            parallelism=parallelism,
            delimiter=delimiter,
        )
    )


async def list_objects_async(  # pylint: disable=too-many-arguments
    s3_url: str,
    max_level: Optional[int],
    max_folders: Optional[int],
    repeat: int,
    parallelism: int,
    delimiter: str,
) -> Iterable[Dict[str, Any]]:
    """List objects in an S3 bucket."""
    assert repeat > 0
    click.echo(
        f"{click.style('Listing objects in ', fg='green')}"
        f"{click.style(s3_url, fg='green', bold=True)}"
    )
    click.echo(
        f"{click.style('max_level: ', fg='green')}"
        f"{click.style(str(max_level), fg='green', bold=True)}, "
        f"{click.style('max_folders: ', fg='green')}"
        f"{click.style(str(max_folders), fg='green', bold=True)}, "
        f"{click.style(str(repeat), fg='green', bold=True)}"
        f"{click.style(' times.', fg='green')}"
    )
    bucket, key = s3_url[len(S3PROTO) :].split("/", 1)
    s3_list = S3BucketObjects(bucket, parallelism=parallelism)

    total_time = 0.0
    for _ in range(repeat):
        start_time = time.time()
        try:
            result = await s3_list.list(
                key, max_level=max_level, max_folders=max_folders, delimiter=delimiter
            )
        except botocore.exceptions.ClientError as exc:
            error(f"Error: {exc}")
        end_time = time.time()
        duration = end_time - start_time
        click.echo(
            f"{click.style('Got ', fg='green')}"
            f"{click.style(str(len(list(result))), fg='green', bold=True)} "
            f"{click.style('objects, elapsed time: ', fg='green')}"
            f"{click.style(f'{duration:.2f}', fg='green', bold=True)} "
            f"{click.style('seconds', fg='green')}"
        )
        total_time += duration
    if repeat > 1:
        click.echo(
            f"{click.style('Average time: ', fg='green')}"
            f"{click.style(f'{total_time / repeat:.2f}', fg='green', bold=True)} "
            f"{click.style('seconds', fg='green')}"
        )
    return result


if __name__ == "__main__":  # pragma: no cover
    as3()  # pylint: disable=no-value-for-parameter
