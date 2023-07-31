#! /bin/env python3
import os

import aiohttp
import asyncio
import polars as pl
from tqdm import tqdm
        
from headers import headers

async def main():
    session = aiohttp.ClientSession(headers=headers)
    
    if os.path.exists("frames.csv"):
        fetched_timestamps = set(i[0] for i in pl.scan_csv("frames.csv").select(["timestamp"]).collect().rows())
    else:
        fetched_timestamps = set()
        with open("frames.csv", mode="w") as f:
            f.writeln("timestamp,0,1,2,3,4,5\n")

    timestamps = set(range(1689858232999,1690320893000,1000)) - fetched_timestamps
    for timestamp in tqdm(timestamps):
        post_data = {
            "operationName": "frameHistory",
            "query": "mutation frameHistory($input: ActInput!) {\n  act(input: $input) {\n    data {\n      ... on BasicMessage {\n        id\n        data {\n          ... on GetFrameHistoryResponseMessageData {\n            frames {\n              canvasIndex\n              url\n              __typename\n            }\n            __typename\n          }\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n",
            "variables": {
                "input": {
                    "actionName": "get_frame_history",
                    "GetFrameHistoryMessageData": {
                        "timestamp": timestamp
                    }
                }
            }
        }

        raw_res = await session.post(
            "https://gql-realtime-2.reddit.com/query",
            json=post_data
        )
        res = await raw_res.json()

        raw_frames = res["data"]["act"]["data"][0]["data"]["frames"]
        frames = {f["canvasIndex"]: f["url"].split("/")[-1] for f in raw_frames}
        data = {"timestamp":timestamp}
        data.update({str(i):frames[i] if i in frames else "" for i in range(6)})
        
        df = pl.from_dict(data)
        with open("frames.csv", mode="ab") as f:
            df.write_csv(f, has_header=not os.path.exists("frames.csv"))

    await session.close()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())