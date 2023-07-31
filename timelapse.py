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

def optimise_canvas_fetch(x1,y1,x2,y2,urls):
    areas = [False]*6
    
    xy11 = x1,y1
    xy12 = x1,y2
    xy21 = x2,y1
    xy22 = x2,y2
    for x,y in [xy11,xy12,xy21,xy22]:
        idx = (x+1500)//1000 + (y+1000)//1000 * 3
        areas[idx] = True

    if areas[0] and areas[2]:
        areas[1] = True
    if areas[3] and areas[5]:
        areas[4] = True
    
    optimal_urls = list(urls)
    for n,a in enumerate(areas):
        if not a:
            optimal_urls[n]=None
    return optimal_urls


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
    else:
        n_urls = list(enumerate(urls))
    
    for i,(n, urls) in enumerate(n_urls):
        n_urls[i] = (n,optimise_canvas_fetch(x1,y1,x2,y2,urls))

    print("\nFetching frames")
    part = partial(get_canvas_frame,x1=x1,y1=y1,x2=x2,y2=y2,output=output)
    total = len(n_urls)
    with Pool(16) as pool:
      list(tqdm(pool.imap(part, n_urls),total = total))
    
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
