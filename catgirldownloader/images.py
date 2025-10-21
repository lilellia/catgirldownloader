import random
from pathlib import Path

import requests
from loguru import logger
from pydantic import BaseModel, Field


class User(BaseModel):
    id: str
    username: str


class ImageData(BaseModel):
    id: str
    tags: list[str]
    likes: int
    favorites: int
    original_hash: str = Field(alias="originalHash")
    nsfw: bool
    artist: str | None = None

    def download(self, dest: Path) -> Path:
        """Download the image to the given path. If the path is a directory, then it is used and a default filename is appended."""
        url = f"https://nekos.moe/image/{self.id}"
        resp = requests.get(url)

        if dest.is_dir():
            prefix = "neko-nsfw" if self.nsfw else "neko"
            dest = dest / f"{prefix}-{self.id}.png"

        dest.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"downloading id={self.id} to {dest}")
        dest.write_bytes(resp.content)
        logger.success("download successful")
        return dest


def get_random_images(*, nsfw: bool = False, number: int = 1) -> list[ImageData]:
    """Select a number of random images from the neko image repo. If `nsfw` is set to True, then all images will be nsfw."""
    base_url = f"https://nekos.moe/api/v1/random/image"
    params = {
        "number": str(number),
        "nsfw": str(nsfw).lower(),  # "false" or "true"
    }

    res = requests.get(base_url, params=params)
    res.raise_for_status()

    return [ImageData(**i) for i in res.json()["images"]]


def get_random_image(*, nsfw: bool = False) -> ImageData:
    """Select a single random image from the neko image repo."""
    image = get_random_images(nsfw=nsfw, number=1)[0]
    logger.info(f"selected {image.id=}, {image.nsfw=}")
    return image


def get_random_image_maybe_nsfw(nsfw_probability: float) -> ImageData:
    """Select a single random image with the given probability of choosing an nsfw one."""
    value = random.uniform(0, 1)
    nsfw = value < nsfw_probability
    logger.debug(f"P(nsfw={nsfw_probability}) :: {value=} so {nsfw=}")
    return get_random_image(nsfw=nsfw)
