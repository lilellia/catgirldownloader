# catgirldownloader

A clone of the application of the same name from Nyarch Linux.

## Installation

**System Requirements:**

- Python 3 (I think this should work for any version 3.7 or later, but I've only tested it on 3.13)
- tkinter

**Installation:**

Once we're sure that our base requirements are installed, we can install the application requirements. The instructions here are with native Python *virtualenv* and *pip*, though you could use any of the ecosystem packages for managing virtual environments (*uv*, *poetry*, etc.)

```bash
$ git clone https://github.com/lilellia/catgirldownloader.git
$ cd catgirldownloader
$ python -m venv .venv           # create a virtualenv here with the name ".venv"
$ source .venv/bin/activate      # will be different on Windows, and Fish users should use .../activate.fish
(.venv) $ python -m pip install loguru pillow pydantic requests ttkbootstrap

# Now the app can be run!
(.venv) $ python ./catgirldownloader.py
```

## Configuration

There is a `config.json` file in the directory, which can be edited to change certain properties of the application. As of right now, the available keys are:

- **nsfw_probability** : a float between 0 and 1. This sets the chance that an nsfw image will be shown. There's a slider in the app window that can change this value as well, but this will be the value that's used at app launch (for the first image).
- **default_download_directory** : a string representing a directory where the images will be downloaded. By default, this is `/tmp` so that they are not permanent files and the app can be used just to view the images, as a save button is provided in the app (so you can download the images you like). However, this can be changed to any directory (perhaps `~/Pictures/catgirls`) so that every image is saved. The directory and all necessary parents will be created if they do not exist.
