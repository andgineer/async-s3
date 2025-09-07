"""async-s3."""

import asyncio
import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Callable, Optional

import botocore.exceptions
import rich_click as click
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn

from async_s3 import __version__
from async_s3.s3_bucket_objects import S3BucketObjects

click.rich_click.USE_MARKDOWN = True

S3PROTO = "s3://"
PROGRESS_REFRESH_INTERVAL = 0.5


@dataclass
class ListingConfig:
    """Configuration for S3 object listing operations."""

    s3_url: str
    max_level: Optional[int] = None
    max_folders: Optional[int] = None
    delimiter: str = "/"
    parallelism: int = 100
    repeat: int = 1

    @property
    def bucket(self) -> str:
        """Extract bucket name from S3 URL."""
        return split_s3_url(self.s3_url)[0]

    @property
    def key(self) -> str:
        """Extract key/prefix from S3 URL."""
        return split_s3_url(self.s3_url)[1]


def error(message: str) -> None:
    """Print an error message and exit."""
    click.secho(message, fg="red", bold=True)
    raise click.Abort()


def print_summary(objects: Iterable[dict[str, Any]]) -> None:
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


class S3ListCommand:
    """Base class for S3 listing commands."""

    def __init__(  # noqa: PLR0913
        self,
        s3_url: str,
        max_level: Optional[int],
        max_folders: Optional[int],
        repeat: int,
        parallelism: int,
        delimiter: str,
    ):
        self.config = ListingConfig(
            s3_url=s3_url,
            max_level=max_level,
            max_folders=max_folders,
            repeat=repeat,
            parallelism=parallelism,
            delimiter=delimiter,
        )

    def validate_and_execute(self) -> Iterable[dict[str, Any]]:
        """Validate S3 URL and execute listing."""
        if not self.config.s3_url.startswith(S3PROTO):
            error("Invalid S3 URL. It should start with s3://")
        return list_objects(self.config)


def list_objects_options(func: Callable[[Any], None]) -> Callable[[Any], None]:
    """Add common options to commands using list_objects."""
    func = click.argument("s3_url")(func)
    func = click.option(
        "--max-level",
        "-l",
        type=int,
        default=None,
        help=(
            "The maximum folder levels to traverse in separate requests. "
            "By default, traverse all levels."
        ),
    )(func)
    func = click.option(
        "--max-folders",
        "-f",
        type=int,
        default=None,
        help="The maximum number of folders to list in one request. By default, list all folders.",
    )(func)
    func = click.option(
        "--repeat",
        "-r",
        type=int,
        default=1,
        help=(
            "Repeat the operation multiple times to calculate average elapsed time. "
            "By default, repeat once."
        ),
    )(func)
    func = click.option(
        "--parallelism",
        "-p",
        type=int,
        default=100,
        help="The maximum number of concurrent requests to AWS S3. By default, 100.",
    )(func)
    return click.option(
        "--delimiter",
        "-d",
        type=str,
        callback=validate_delimiter,
        default="/",
        help="Delimiter for 'folders'. Default is '/'.",
    )(func)


def validate_delimiter(ctx: click.Context, param: click.Parameter, value: str) -> str:  # noqa: ARG001
    """Validate the `Delimiter` option."""
    if len(value) != 1:
        raise click.BadParameter("Delimiter must be exactly one character.")
    return value


@list_objects_options
@as3.command()
def ls(  # noqa: PLR0913
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
    cmd = S3ListCommand(s3_url, max_level, max_folders, repeat, parallelism, delimiter)
    objects = cmd.validate_and_execute()
    click.echo("\n".join([obj["Key"] for obj in objects]))
    print_summary(objects)


@list_objects_options
@as3.command()
def du(  # noqa: PLR0913
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
    cmd = S3ListCommand(s3_url, max_level, max_folders, repeat, parallelism, delimiter)
    objects = cmd.validate_and_execute()
    print_summary(objects)


def human_readable_size(size: float, decimal_places: int = 2) -> str:
    """Convert bytes to a human-readable format."""
    for _unit in ["B", "KB", "MB", "GB", "TB"]:
        bytes_in_kilo = 1024.0
        if size < bytes_in_kilo:
            break
        size /= bytes_in_kilo
    return f"{size:.{decimal_places}f} {_unit}"


def list_objects(config: ListingConfig) -> Iterable[dict[str, Any]]:
    """List objects in an S3 bucket."""
    return asyncio.run(list_objects_async(config))


async def list_objects_async(config: ListingConfig) -> Iterable[dict[str, Any]]:
    """List objects in an S3 bucket."""
    assert config.repeat > 0
    print_start_info(config)

    s3_list = S3BucketObjects(config.bucket, parallelism=config.parallelism)
    total_time = 0.0
    result: Iterable[dict[str, Any]] = []

    for attempt in range(config.repeat):
        result, duration = await list_objects_with_progress(s3_list, config)
        total_time += duration
        print_attempt_info(attempt, duration)

    if config.repeat > 1:
        print_average_time(total_time, config.repeat)

    return result


def print_start_info(config: ListingConfig) -> None:
    """Print the command parameters."""
    click.echo(
        f"{click.style('Listing objects in ', fg='yellow')}"
        f"{click.style(config.s3_url, fg='yellow', bold=True)}",
    )
    click.echo(
        f"{click.style('max_level: ', fg='yellow')}"
        f"{click.style(str(config.max_level), fg='yellow', bold=True)}, "
        f"{click.style('max_folders: ', fg='yellow')}"
        f"{click.style(str(config.max_folders), fg='yellow', bold=True)}, "
        f"{click.style('delimiter: ', fg='yellow')}"
        f"{click.style(config.delimiter, fg='yellow', bold=True)}, "
        f"{click.style('parallelism: ', fg='yellow')}"
        f"{click.style(str(config.parallelism), fg='yellow', bold=True)}, "
        f"{click.style(str(config.repeat), fg='yellow', bold=True)}"
        f"{click.style(' times.', fg='yellow')}",
    )


def split_s3_url(s3_url: str) -> tuple[str, str]:
    """Split an S3 URL into bucket and key."""
    parts = s3_url[len(S3PROTO) :].split("/", 1)
    return (parts[0], parts[1] if len(parts) > 1 else "")


async def list_objects_with_progress(
    s3_list: S3BucketObjects,
    config: ListingConfig,
) -> tuple[Iterable[dict[str, Any]], float]:
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
                config.key,
                max_level=config.max_level,
                max_folders=config.max_folders,
                delimiter=config.delimiter,
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
        f"{click.style('seconds', fg='green')}",
    )


def print_average_time(total_time: float, repeat: int) -> None:
    """Print the average elapsed time."""
    click.echo(
        f"{click.style('Average time: ', fg='yellow')}"
        f"{click.style(f'{total_time / repeat:.2f}', fg='yellow', bold=True)} "
        f"{click.style('seconds', fg='yellow')}",
    )


if __name__ == "__main__":  # pragma: no cover
    as3()  # pylint: disable=no-value-for-parameter
