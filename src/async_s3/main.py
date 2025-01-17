"""async-s3."""

import asyncio
import time
from typing import Iterable, Dict, Any, Optional, Callable, Tuple
import rich_click as click
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn
import botocore.exceptions
from async_s3.s3_bucket_objects import S3BucketObjects
from async_s3 import __version__


click.rich_click.USE_MARKDOWN = True

S3PROTO = "s3://"
PROGRESS_REFRESH_INTERVAL = 0.5


def error(message: str) -> None:
    """Print an error message and exit."""
    click.secho(message, fg="red", bold=True)
    raise click.Abort()


def print_summary(objects: Iterable[Dict[str, Any]]) -> None:
    """Print a summary of the objects."""
    total_size = sum(obj["Size"] for obj in objects)
    message = (
        f"{click.style('Total objects: ', fg='yellow')}"
        f"{click.style(f'{len(list(objects)):,}', fg='yellow', bold=True)}, "
        f"{click.style('size: ', fg='yellow')}"
        f"{click.style(human_readable_size(total_size), fg='yellow', bold=True)}"
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
        callback=validate_delimiter,
        default="/",
        help="Delimiter for 'folders'. Default is '/'.",
    )(func)
    return func


def validate_delimiter(ctx: click.Context, param: click.Parameter, value: str) -> str:  # pylint: disable=unused-argument
    """Validate the `Delimiter` option."""
    if len(value) != 1:
        raise click.BadParameter("Delimiter must be exactly one character.")
    return value


@list_objects_options
@as3.command()
def ls(  # pylint: disable=too-many-arguments,too-many-positional-arguments
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
def du(  # pylint: disable=too-many-arguments,too-many-positional-arguments
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


def list_objects(  # pylint: disable=too-many-arguments,too-many-positional-arguments
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


async def list_objects_async(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    s3_url: str,
    max_level: Optional[int],
    max_folders: Optional[int],
    repeat: int,
    parallelism: int,
    delimiter: str,
) -> Iterable[Dict[str, Any]]:
    """List objects in an S3 bucket."""
    assert repeat > 0
    print_start_info(s3_url, max_level, max_folders, delimiter, parallelism, repeat)

    bucket, key = split_s3_url(s3_url)
    s3_list = S3BucketObjects(bucket, parallelism=parallelism)
    total_time = 0.0
    result: Iterable[Dict[str, Any]] = []

    for attempt in range(repeat):
        result, duration = await list_objects_with_progress(
            s3_list, key, max_level, max_folders, delimiter
        )
        total_time += duration
        print_attempt_info(attempt, duration)

    if repeat > 1:
        print_average_time(total_time, repeat)

    return result


def print_start_info(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    s3_url: str,
    max_level: Optional[int],
    max_folders: Optional[int],
    delimiter: str,
    parallelism: int,
    repeat: int,
) -> None:
    """Print the command parameters."""
    click.echo(
        f"{click.style('Listing objects in ', fg='yellow')}"
        f"{click.style(s3_url, fg='yellow', bold=True)}"
    )
    click.echo(
        f"{click.style('max_level: ', fg='yellow')}"
        f"{click.style(str(max_level), fg='yellow', bold=True)}, "
        f"{click.style('max_folders: ', fg='yellow')}"
        f"{click.style(str(max_folders), fg='yellow', bold=True)}, "
        f"{click.style('delimiter: ', fg='yellow')}"
        f"{click.style(delimiter, fg='yellow', bold=True)}, "
        f"{click.style('parallelism: ', fg='yellow')}"
        f"{click.style(str(parallelism), fg='yellow', bold=True)}, "
        f"{click.style(str(repeat), fg='yellow', bold=True)}"
        f"{click.style(' times.', fg='yellow')}"
    )


def split_s3_url(s3_url: str) -> Iterable[str]:
    """Split an S3 URL into bucket and key."""
    return s3_url[len(S3PROTO) :].split("/", 1)


async def list_objects_with_progress(  # pylint: disable=too-many-locals
    s3_list: S3BucketObjects,
    key: str,
    max_level: Optional[int],
    max_folders: Optional[int],
    delimiter: str,
) -> Tuple[Iterable[Dict[str, Any]], float]:
    """List objects in an S3 bucket with a progress bar.

    Returns:
        (The objects, the elapsed time)
    """
    start_time = time.time()
    result = []
    total_size = 0
    last_update_time = start_time - PROGRESS_REFRESH_INTERVAL

    try:
        with Progress(
            TextColumn("[progress.description]{task.description}{task.completed:>,}"),
            BarColumn(),
            TaskProgressColumn(),
            transient=True,
        ) as progress:
            objects_bar = progress.add_task("[green]Objects: ", total=None)
            size_bar = progress.add_task("[green]Size:    ", total=None)
            async for objects_page in s3_list.iter(
                key, max_level=max_level, max_folders=max_folders, delimiter=delimiter
            ):
                result.extend(objects_page)
                page_objects_size = sum(obj["Size"] for obj in objects_page)
                total_size += page_objects_size
                current_time = time.time()
                if current_time - last_update_time >= PROGRESS_REFRESH_INTERVAL:
                    progress.update(objects_bar, advance=len(objects_page))
                    progress.update(size_bar, advance=page_objects_size)
                    last_update_time = current_time
            progress.remove_task(objects_bar)
            progress.remove_task(size_bar)
    except botocore.exceptions.ClientError as exc:
        error(f"Error: {exc}")

    end_time = time.time()
    duration = end_time - start_time
    return result, duration


def print_attempt_info(attempt: int, duration: float) -> None:
    """Print the elapsed time for an attempt."""
    click.echo(
        f"{click.style(f'({attempt + 1}) Elapsed time: ', fg='green')}"
        f"{click.style(f'{duration:.2f}', fg='green', bold=True)} "
        f"{click.style('seconds', fg='green')}"
    )


def print_average_time(total_time: float, repeat: int) -> None:
    """Print the average elapsed time."""
    click.echo(
        f"{click.style('Average time: ', fg='yellow')}"
        f"{click.style(f'{total_time / repeat:.2f}', fg='yellow', bold=True)} "
        f"{click.style('seconds', fg='yellow')}"
    )


if __name__ == "__main__":  # pragma: no cover
    as3()  # pylint: disable=no-value-for-parameter
