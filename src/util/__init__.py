import os
import random
from contextlib import contextmanager
import gc
import re
from pytube import YouTube
from .url import YouTubeURL
from typing import LiteralString

# A little function to clear cuda cache. Put the import inside just in case we do not need torch, because torch import takes too long
def clear_cuda():
    import torch
    gc.collect()
    torch.cuda.empty_cache()

def is_ipython():
    try:
        __IPYTHON__ # type: ignore
        return True
    except NameError:
        return False
