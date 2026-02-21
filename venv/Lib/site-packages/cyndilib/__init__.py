import os
import sys
from pathlib import Path
if sys.version_info < (3, 9):
    import importlib_resources
else:
    import importlib.resources as importlib_resources

if sys.platform == 'win32':
    dll_dir = importlib_resources.files('cyndilib') / 'wrapper' / 'bin'
    os.add_dll_directory(dll_dir)

def get_include() -> str:
    return str(importlib_resources.files('cyndilib.wrapper.include'))


from .wrapper import *
from .audio_frame import *
from .audio_reference import AudioReference
from .finder import Source, Finder
from .framesync import FrameSync
from .metadata_frame import *
from .receiver import Receiver
from .sender import Sender
from .video_frame import *
