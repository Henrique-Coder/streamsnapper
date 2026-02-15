"""Video-related data models."""

from datetime import datetime
from typing import Any

from orjson import dumps
from pydantic import BaseModel, Field


class VideoInformation(BaseModel):
    """Complete video information with comprehensive metadata."""

    # URLs
    source_url: str | None = None
    short_url: str | None = None
    embed_url: str | None = None
    youtube_music_url: str | None = None
    full_url: str | None = None

    # Basic video info
    id: str | None = None
    title: str | None = None
    clean_title: str | None = None
    description: str | None = None

    # Channel info
    channel_id: str | None = None
    channel_url: str | None = None
    channel_name: str | None = None
    clean_channel_name: str | None = None
    is_verified_channel: bool = False

    # Metrics
    duration: int | None = None
    view_count: int | None = None
    like_count: int | None = None
    dislike_count: int | None = None
    comment_count: int | None = None
    follow_count: int | None = None

    # Properties
    is_age_restricted: bool = False
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    chapters: list[dict[str, Any]] = Field(default_factory=list)
    is_streaming: bool = False
    upload_timestamp: int | None = None
    availability: str | None = None
    language: str | None = None

    # Media
    thumbnails: list[str] = Field(default_factory=list)
    all_thumbnails: list[str] = Field(default_factory=list)

    @property
    def upload_date(self) -> datetime | None:
        """Get upload date as datetime object."""
        if self.upload_timestamp:
            return datetime.fromtimestamp(self.upload_timestamp)
        return None

    @property
    def duration_formatted(self) -> str:
        """Get formatted duration (HH:MM:SS)."""
        if not self.duration:
            return "Unknown"

        hours = self.duration // 3600
        minutes = (self.duration % 3600) // 60
        seconds = self.duration % 60

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def to_json(self) -> str:
        """Convert to JSON string using orjson."""
        return dumps(self.model_dump(), default=str).decode("utf-8")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()


class VideoStream(BaseModel):
    """Individual video stream."""

    # Stream info
    url: str
    codec: str | None = None
    extension: str

    # Video properties
    width: int | None = None
    height: int | None = None
    framerate: float | None = None
    bitrate: float | None = None

    # Additional metadata
    quality_note: str | None = None
    is_hdr: bool = False
    is_ai_upscaled: bool = False
    size: int | None = None
    language: str | None = None
    youtube_format_id: int | None = None

    @property
    def resolution(self) -> str | None:
        """Get resolution string like '1080p'."""
        if self.height:
            return f"{self.height}p"
        return None

    @property
    def aspect_ratio(self) -> float | None:
        """Get aspect ratio (width/height)."""
        if self.width and self.height:
            return round(self.width / self.height, 2)
        return None

    @property
    def quality_score(self) -> float:
        """Calculate quality score for ranking."""
        score = 0.0

        if self.width and self.height:
            score += (self.width * self.height) / 1_000_000  # Megapixels

        if self.framerate:
            score += self.framerate / 10

        if self.bitrate:
            score += self.bitrate / 100

        if self.is_hdr:
            score += 10

        return round(score, 2)

    @property
    def is_hd(self) -> bool:
        """Check if stream is HD (>=720p)."""
        return (self.height or 0) >= 720

    @property
    def is_4k(self) -> bool:
        """Check if stream is 4K (>=2160p)."""
        return (self.height or 0) >= 2160

    def to_json(self) -> str:
        """Convert to JSON string using orjson."""
        return dumps(self.model_dump(), default=str).decode("utf-8")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()


class VideoStreamCollection(BaseModel):
    """Collection of video streams with intuitive filtering."""

    streams: list[VideoStream] = Field(default_factory=list)

    @property
    def best(self) -> VideoStream | None:
        """Get the absolute best quality stream."""
        if not self.streams:
            return None
        return max(self.streams, key=lambda s: s.quality_score)

    @property
    def worst(self) -> VideoStream | None:
        """Get the lowest quality stream."""
        if not self.streams:
            return None
        return min(self.streams, key=lambda s: s.quality_score)

    def filter(
        self,
        resolution: str | None = None,
        min_resolution: str | None = None,
        max_resolution: str | None = None,
        codec: str | None = None,
        hdr: bool | None = None,
        fps: float | None = None,
    ) -> "VideoStreamCollection":
        """
        Filter streams by various criteria.

        Returns a new VideoStreamCollection.
        """
        filtered = self.streams

        if resolution:
            target = int(resolution.replace("p", ""))
            filtered = [s for s in filtered if s.height == target]

        if min_resolution:
            target = int(min_resolution.replace("p", ""))
            filtered = [s for s in filtered if s.height and s.height >= target]

        if max_resolution:
            target = int(max_resolution.replace("p", ""))
            filtered = [s for s in filtered if s.height and s.height <= target]

        if codec:
            filtered = [s for s in filtered if s.codec and codec.lower() in s.codec.lower()]

        if hdr is not None:
            filtered = [s for s in filtered if s.is_hdr == hdr]

        if fps:
            filtered = [s for s in filtered if s.framerate == fps]

        return VideoStreamCollection(streams=sorted(filtered, key=lambda s: s.quality_score, reverse=True))

    def first(self) -> VideoStream | None:
        """Return the first stream in the collection or None."""
        return self.streams[0] if self.streams else None

    def __len__(self) -> int:
        return len(self.streams)

    def __iter__(self):
        return iter(self.streams)

    def __getitem__(self, index):
        return self.streams[index]

    def to_json(self) -> str:
        """Convert to JSON string using orjson."""
        return dumps(self.model_dump(), default=str).decode("utf-8")
