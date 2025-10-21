import json
import shutil
import tkinter as tk
from argparse import ArgumentParser
from dataclasses import dataclass
from os import PathLike
from pathlib import Path
from tkinter.filedialog import asksaveasfilename
from typing import IO, Literal, Protocol, Self

import ttkbootstrap as ttkb
from PIL import Image, ImageTk
from loguru import logger

import catgirldownloader

CANVAS_WIDTH = 1280
CANVAS_HEIGHT = 720


class ConfigOverrideNamespace(Protocol):
    nsfw_probability: float | None
    auto_refresh_delay: float | None
    nsfw_download_dir: Path | None
    sfw_download_dir: Path | None


@dataclass
class Config:
    nsfw_probability: float
    auto_refresh_delay: float
    default_download_directory: dict[Literal["sfw", "nsfw"], Path]

    @classmethod
    def from_file(cls, filepath: Path) -> Self:
        data = json.loads(filepath.read_text())

        # reinterpret the default_download_directory keys as Path objects
        dl_dir = data["default_download_directory"]
        data["default_download_directory"] = {
            "sfw": Path(dl_dir["sfw"]),
            "nsfw": Path(dl_dir["nsfw"])
        }

        return cls(**data)
    
    def update_from(self, args: ConfigOverrideNamespace) -> None:
        if (p := args.nsfw_probability) is not None:
            self.nsfw_probability = p
        
        if (r := args.auto_refresh_delay) is not None:
            self.auto_refresh_delay = r
        
        if (n := args.nsfw_download_dir) is not None:
            self.default_download_directory["nsfw"] = n 
        
        if (s := args.sfw_download_dir) is not None:
            self.default_download_directory["sfw"] = s


class App(ttkb.Frame):
    def __init__(self, master, config: Config):
        super().__init__(master)
        self.config = config

        grid_kw = dict(sticky="NSEW", padx=5, pady=5)

        # set up controls panel
        self.controls_frame = ttkb.Frame(self)

        self.refresh_button = ttkb.Button(self.controls_frame, text="Refresh", command=self.refresh)
        self.refresh_button.grid(row=0, column=0, rowspan=2, **grid_kw)

        self.open_image_button = ttkb.Button(self.controls_frame, text="Open Image",
                                             command=self.open_image_in_system_application)
        self.open_image_button.grid(row=0, column=1, rowspan=2, **grid_kw)

        self.save_image_button = ttkb.Button(self.controls_frame, text="Save Image",
                                             command=self.save_image)
        self.save_image_button.grid(row=0, column=2, rowspan=2, **grid_kw)

        self.setvar("nsfw-probability", f"{config.nsfw_probability * 100:.0f}")
        self.nsfw_scale = ttkb.Scale(self.controls_frame, orient=ttkb.HORIZONTAL, from_=0, to=100,
                                     value=config.nsfw_probability * 100,
                                     command=self.update_nsfw_scale, bootstyle="danger")
        self.nsfw_scale_label = ttkb.Label(self.controls_frame, width=20,
                                           text=f"P(nsfw image) = {config.nsfw_probability:.0%}")
        self.nsfw_scale_label.grid(row=0, column=3, **grid_kw)
        self.nsfw_scale.grid(row=0, column=4, **grid_kw)

        self.setvar("auto-refresh-delay", f"{config.auto_refresh_delay:.1f}")
        self.auto_refresh_scale = ttkb.Scale(self.controls_frame, orient=ttkb.HORIZONTAL, from_=0, to=10,
                                             value=config.auto_refresh_delay,
                                             command=self.update_auto_refresh_delay, bootstyle="info")
        self.auto_refresh_scale_label = ttkb.Label(self.controls_frame, width=20,
                                                   text=f"Auto Refresh (sec) = {config.auto_refresh_delay:.1f}")
        self.auto_refresh_scale_label.grid(row=1, column=3, **grid_kw)
        self.auto_refresh_scale.grid(row=1, column=4, **grid_kw)

        if config.auto_refresh_delay != 0:
            self._auto_refresh_func = self.after(self.current_auto_refresh_delay, self.refresh)
        else:
            self._auto_refresh_func = None

        self.controls_frame.pack()

        # set up info display
        self.info_display = ttkb.Frame(self)
        self.info_text = ttkb.StringVar(self.info_display)
        ttkb.Label(self.info_display, textvariable=self.info_text).pack()
        self.info_display.pack()

        # set up canvas
        self._filename = self._image = None
        self.canvas = ttkb.Canvas(self, width=CANVAS_WIDTH, height=CANVAS_HEIGHT)
        self.canvas.pack()
        self.refresh()

        # other
        self.master.bind("<F5>", self.refresh)
        self.pack()

    @staticmethod
    def load_image(fp: str | bytes | PathLike[str] | PathLike[bytes] | IO[bytes], *, max_height: int | None = None,
                   max_width: int | None, preserve_aspect_ratio: bool = True) -> ImageTk.PhotoImage:
        """Load the given image from file, scale it to fit within the given dimensions, and convert it to be used in tkinter.
        If `preserve_aspect_ratio` is False, then the resulting image will be exactly the given dimensions but may be stretched or squished."""
        img = Image.open(fp)

        scales: list[float] = []

        if max_height is not None:
            scales.append(max_height / img.height)

        if max_width is not None:
            scales.append(max_width / img.width)

        if scales:
            scale = min(scales)
            size = round(img.width * scale), round(img.height * scale)
            img = img.resize(size)

        return ImageTk.PhotoImage(img)

    @property
    def current_nsfw_probability(self) -> float:
        return float(self.getvar("nsfw-probability")) / 100.0

    @current_nsfw_probability.setter
    def current_nsfw_probability(self, probability: float):
        self.setvar("nsfw-probability", f"{probability * 100:.0f}")
        self.nsfw_scale_label.configure(text=f"P(nsfw image) = {probability:.0%}")

    def update_nsfw_scale(self, percentage_str: str) -> None:
        self.current_nsfw_probability = float(percentage_str) / 100.0

    @property
    def current_auto_refresh_delay(self) -> int:
        return round(float(self.getvar("auto-refresh-delay")) * 1000)

    @current_auto_refresh_delay.setter
    def current_auto_refresh_delay(self, milliseconds: float):
        if self._auto_refresh_func is not None:
            self.after_cancel(self._auto_refresh_func)
            self._auto_refresh_func = None

        logger.debug(f"setting auto refresh to {milliseconds / 1000:.2}s")
        seconds = milliseconds / 1000.0
        self.setvar("auto-refresh-delay", f"{seconds:.2f}")
        self.auto_refresh_scale_label.configure(text=f"Auto Refresh (sec) = {seconds:.2f}")

        if milliseconds != 0:
            self._auto_refresh_func = self.after(round(milliseconds), self.refresh)
        else:
            self._auto_refresh_func = None

    def update_auto_refresh_delay(self, seconds_str: str) -> None:
        self.current_auto_refresh_delay = float(seconds_str) * 1000

    def refresh(self, _: tk.Event | None = None):
        # select a new image
        p = float(self.getvar("nsfw-probability")) / 100.0
        image = catgirldownloader.get_random_image_maybe_nsfw(nsfw_probability=p)

        # download the image
        key = "nsfw" if image.nsfw else "sfw"
        self._filename = image.download(dest=self.config.default_download_directory[key])

        # place the image
        self._image = img = self.load_image(self._filename, max_height=CANVAS_HEIGHT, max_width=CANVAS_WIDTH)
        self.canvas.create_image(CANVAS_WIDTH // 2, CANVAS_HEIGHT // 2, anchor=ttkb.CENTER, image=img)

        # update the info display
        info_components = dict(nsfw=image.nsfw, id=image.id, artist=image.artist, filename=self._filename)
        self.info_text.set("・".join(f"{k}={v}" for k, v in info_components.items()))

        if self._auto_refresh_func is not None:
            self.after_cancel(self._auto_refresh_func)
            self._auto_refresh_func = None

        if self.current_auto_refresh_delay != 0:
            self._auto_refresh_func = self.after(self.current_auto_refresh_delay, self.refresh)

    def open_image_in_system_application(self, _: tk.Event | None = None) -> None:
        Image.open(self._filename).show()

    def save_image(self, _: tk.Event | None = None) -> None:
        dest = asksaveasfilename(defaultextension=".png", initialdir=Path.cwd(), initialfile=self._filename.name)
        shutil.copyfile(self._filename, dest)


def main():
    parser = ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-c", "--config-file", type=Path, default=Path(__file__).parent / "config.json")

    # allow command line override of config file
    parser.add_argument("-n", "--nsfw-probability", type=float, help="the probability (0 to 1) that a chosen image will be tagged as nsfw")
    parser.add_argument("-r", "--auto-refresh-delay", type=float, help="delay (in seconds) for auto-generation (use 0 to disable auto-generation)")
    parser.add_argument("-N", "--nsfw-download-dir", type=Path, help="path to download nsfw images")
    parser.add_argument("-S", "--sfw-download-dir", type=Path, help="path to download sfw images")

    args = parser.parse_args()

    if args.verbose:
        logger.level("DEBUG")
    else:
        logger.level("INFO")

    config = Config.from_file(args.config_file)
    config.update_from(args)
    app = App(ttkb.Window("catgirldownloader", themename="darkly"), config=config)
    app.mainloop()


if __name__ == "__main__":
    main()
