"""Data models for StreamSnapper."""

from .audio import AudioStream, AudioStreamCollection
from .subtitle import SubtitleStream, SubtitleStreamCollection
from .video import VideoInformation, VideoStream, VideoStreamCollection


__all__: list[str] = [
    "AudioStream",
    "AudioStreamCollection",
    "SubtitleStream",
    "SubtitleStreamCollection",
    "VideoInformation",
    "VideoStream",
    "VideoStreamCollection",
]
