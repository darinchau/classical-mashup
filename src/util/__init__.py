import os
import random
from contextlib import contextmanager
import gc
import re
from pytube import YouTube

# A little function to clear cuda cache. Put the import inside just in case we do not need torch, because torch import takes too long
def clear_cuda():
    import torch
    gc.collect()
    torch.cuda.empty_cache()

def is_ipython():
    try:
        __IPYTHON__
        return True
    except NameError:
        return False

_VIDEO_ID = re.compile(r"[A-Za-z0-9-_]{11}")

class YouTubeURL(str):
    def __new__(cls, url):
        url = url.strip()
        if _VIDEO_ID.match(url):
            yt = YouTube(f"https://www.youtube.com/watch?v={url}")
        else:
            yt = YouTube(url)
        url_id = yt.video_id
        assert url_id is not None and len(url_id) == 11 and _VIDEO_ID.match(url_id)

        return super().__new__(cls, f"https://www.youtube.com/watch?v={url_id}")

    @property
    def video_id(self):
        return self[-11:]
