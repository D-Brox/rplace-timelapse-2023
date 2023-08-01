# Reddit r/place 2023 Timelapse Video Maker

**Easily make HD Timelapse videos of Reddit's r/place 2023**

This set of scripts scrapes both the urls and the images from r/place 2023 to make custom timelapse videos.


## Timelapse

1. Install the python dependencies with `python -m pip install -r requirements.txt`. Make sure you also have `ffmpeg` installed.
2. Get the top-left and bottom-right coordinates of the area you want on the video.
3. Get the start and end timestamps. They can be found on the r/place `url`, after the `&ts=`, when looking at the canvas.
4. Choose the framerate of the video (fps) and the frameskip (seconds passed between each frame). Multiplying both numbers gives us the number of real-life seconds each second on the video represents. By default each second in the video is 1 hour (3600 seconds).

### Usage
```
usage: timelapse.py [-h] [--start START] [--end END] [--framerate FRAMERATE] [--frameskip FRAMESKIP] [--scale SCALE] [--out OUT]
                    left top right bottom

positional arguments:
  left                  left canvas coordinates
  top                   top canvas coordinates
  right                 right canvas coordinates
  bottom                bottom canvas coordinates

optional arguments:
  -h, --help            show this help message and exit
  --start START         timestamp of the first frame
  --end END             timestamp of the last frame
  --framerate FRAMERATE
                        framerate of the video
  --frameskip FRAMESKIP
                        seconds skipped in between r/place canvas frames
  --scale SCALE         scale of the video output
  --out OUT             output directory for the images and video
  --keep                continue from where the process died         
```

## Scraper

The scraper fetchs the endpoints of each second of the r/place canvas history. In case you want to recreate the `frames.csv` file, you can follow the following steps:

1. Open the r/place canvas history.
2. Open your browser's devtools using `Ctrl`+`Alt`+`I`
3. Open the `network` tab and search `query`
4. Scroll the timeline bar on the page. There should appear several internet request.
5. Click on any of the request with the method POST. It will open a menu that shows the request headers.
6. Copy the token in the header `authorization`. It should start with `ey`.
7. Paste the token on `headers.py` and run `python scraper.py`
