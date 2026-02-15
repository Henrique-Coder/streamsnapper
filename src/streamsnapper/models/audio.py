"""Audio-related data models."""

from typing import Any

from orjson import dumps
from pydantic import BaseModel, Field


class AudioStream(BaseModel):
    """Individual audio stream."""

    # Stream info
    url: str
    codec: str | None = None
    extension: str

    # Audio properties
    bitrate: float | None = None
    sample_rate: int | None = None
    channels: int | None = None

    # Language and metadata
    language: str | None = None
    size: int | None = None
    youtube_format_id: int | None = None

    @property
    def quality_score(self) -> float:
        """Calculate quality score for ranking."""
        score = 0.0
        if self.bitrate:
            score += self.bitrate * 10
        if self.sample_rate:
            score += self.sample_rate / 1000
        if self.channels:
            score += self.channels * 5
        return round(score, 2)

    def to_json(self) -> str:
        """Convert to JSON string using orjson."""
        return dumps(self.model_dump(), default=str).decode("utf-8")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()


class AudioStreamCollection(BaseModel):
    """Collection of audio streams with intuitive filtering."""

    streams: list[AudioStream] = Field(default_factory=list)

    @property
    def best(self) -> AudioStream | None:
        """Get the absolute best quality stream."""
        if not self.streams:
            return None
        return max(self.streams, key=lambda s: s.quality_score)

    @property
    def worst(self) -> AudioStream | None:
        """Get the lowest quality stream."""
        if not self.streams:
            return None
        return min(self.streams, key=lambda s: s.quality_score)

    def filter(
        self,
        language: str | None = None,
        min_bitrate: float | None = None,
        codec: str | None = None,
    ) -> "AudioStreamCollection":
        """
        Filter streams by criteria.

        Returns a new AudioStreamCollection.
        """
        filtered = self.streams

        if language:
            # Simple substring match for now, can be sophisticated later
            filtered = [s for s in filtered if s.language and language.lower() in s.language.lower()]

        if min_bitrate:
            filtered = [s for s in filtered if s.bitrate and s.bitrate >= min_bitrate]

        if codec:
            filtered = [s for s in filtered if s.codec and codec.lower() in s.codec.lower()]

        return AudioStreamCollection(streams=sorted(filtered, key=lambda s: s.quality_score, reverse=True))

    def first(self) -> AudioStream | None:
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
