#! /bin/env python3
import argparse
from functools import partial
from io import BytesIO
from multiprocessing import Pool
import os
import shutil

import ffmpeg
from PIL import Image
import polars as pl
import requests
from tqdm import tqdm

def get_canvas_frame(urls,x1,y1,x2,y2,output):
    frames = []
    n_image,frame_urls = urls
    base_url = "https://garlic-bread.reddit.com/media/canvas-images/full-frame"
    for n,filename in enumerate(frame_urls):
        if filename:
            res = requests.get(f"{base_url}/{n}/{filename}")
            frames.append(Image.open(BytesIO(res.content)))
        else:
            frames.append(None)
    canvas = Image.new('RGB', (3000,2000), (255, 255, 255))
    for n,f in enumerate(frames):
        if f:
            canvas.paste(f, ((n%3)*1000, (n//3)*1000))
    
    frame = canvas.crop((x1+1500, y1+1000, x2+1500+1, y2+1000+1))
    frame.save(f"{output}/images/{n_image:06}.png")

def timelapse(x1,y1,x2,y2,urls,frameskip,framerate,scale,output,keep):
    if not os.path.exists(f"{output}/images/"):
        os.makedirs(f"{output}/images/")
    elif not keep:
        shutil.rmtree(f"{output}/images/")
        os.makedirs(f"{output}/images/")
    
    if keep:
        n_urls = []
        for n,urls in enumerate(urls):
            if not os.path.exists(f"{output}/images/{n:06}.png"):
                n_urls.append((n,urls))
        total = len(n_urls)
    else:
        n_urls = enumerate(urls)
        total = len(urls)

    print("\nFetching frames")
    part = partial(get_canvas_frame,x1=x1,y1=y1,x2=x2,y2=y2,output=output)
    with Pool(16) as pool:
      list(tqdm(pool.imap(part, n_urls),total=total))
    
    print("\nMerging video")
    stream = ffmpeg.input(f"{output}/images/%06d.png")
    stream = ffmpeg.filter(stream, 'fps', fps=framerate, round='up')
    if scale != 1:
        stream = ffmpeg.filter(stream, 'scale', f"iw*{scale}",f"ih*{scale}",**{"flags":"neighbor"} )
    stream = ffmpeg.output(stream,f"{output}/timelapse.mp4",**{"c:v":"libx264"},pix_fmt="yuv420p")
    if os.path.exists(f"{output}/timelapse.mp4"):
        os.remove(f"{output}/timelapse.mp4")
    ffmpeg.run(stream)


def fix_coords(x1,y1,x2,y2):
    if x1 > x2:
        x1, x2 = x2, x1
    if y1 > y2:
        y1, y2 = y2, y1
    if x1 < -1500:
        x1 = -1500
    if y1 < -1000:
        y1 = -1000
    if x2 > 1499:
        x2 = 1499
    if y2 > 999:
        y2 = 999
    return x1,y1,x2,y2

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("top", type=int,
                        help="Top canvas coordinates")
    parser.add_argument("left", type=int,
	                    help="Left canvas coordinates")
    parser.add_argument("bottom", type=int,
                        help="Bottom canvas coordinates")
    parser.add_argument("right", type=int,
	                    help="Right canvas coordinates")
    
    parser.add_argument("--start",default = 1689858232999, type=int,
	                    help="Timestamp of the first frame")
    parser.add_argument("--end",default = 1690320892999, type=int,
	                    help="Timestamp of the last frame")
    
    parser.add_argument("--framerate",default=60, type=int,
                        help="Framerate of the video")
    parser.add_argument("--frameskip",default=60, type=int,
                        help="Seconds skipped in between r/place canvas frames")
    parser.add_argument("--scale",default=1, type=int,
                        help="Scale of the video output")
    
    parser.add_argument("--out", default="./output",
                        help="Output directory for the images and video")
    parser.add_argument("--keep", action='store_true',
                        help="Continue from where it died")
    parser.set_defaults(keep=False)
    
    args = parser.parse_args()

    x1,y1,x2,y2 = fix_coords(args.top,args.left,args.bottom,args.right)

    if args.start < 1689858232999:
        args.start = 1689858232999
    if args.end > 1690320892999:
        args.end = 1690320892999

    # My scraper got blocked before I could scrape all of
    # the seconds in the canvas history.
    # I currently have only the urls of 72% the seconds.
    # Therefore, seconds between frames should be a multiple
    # of 2 or 5, as I was able to scrape all of those.

    # If you are able to scrape the missing ones, please open a PR.
    if args.frameskip<2:
        args.frameskip = 2
    if args.frameskip%2 and args.frameskip%5:
        args.frameskip = (args.frameskip//2)*2
    args.start = args.start - (args.start - 1689858232999)%10000

    print("Processing timestamps")
    df = pl.read_csv("frames.csv")
    frames_urls = []
    for timestamp in tqdm(range(args.start,args.end+1,args.frameskip*1000)):
        row = df.filter(pl.any_horizontal(pl.col("timestamp") == timestamp))
        frames_urls.append(row.drop("timestamp").rows()[0])

    timelapse(x1, y1, x2, y2, frames_urls, args.frameskip, args.framerate,args.scale, args.out, args.keep)


if __name__ == "__main__":
    main()
