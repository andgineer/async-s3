import asyncio

from async_s3 import S3BucketObjects


async def main():
    objects = await S3BucketObjects("my-bucket").list("my-prefix/", max_level=2, max_folders=20)

    for obj in objects:
        print(obj["Key"])


if __name__ == "__main__":
    asyncio.run(main())
