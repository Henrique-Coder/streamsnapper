"""Subtitle-related data models."""

from typing import Any

from orjson import dumps
from pydantic import BaseModel, Field


class SubtitleStream(BaseModel):
    """Individual subtitle stream."""

    # Stream info
    url: str
    extension: str
    language: str | None = None
    language_name: str | None = None
    is_auto_generated: bool = False

    @property
    def is_manual(self) -> bool:
        """Check if subtitle is manually created (not auto-generated)."""

        return not self.is_auto_generated

    def to_json(self) -> str:
        """Convert to JSON string using orjson."""

        return dumps(self.model_dump(), default=str).decode("utf-8")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""

        return self.model_dump()


class SubtitleStreamCollection(BaseModel):
    """Collection of subtitle streams with intuitive filtering."""

    streams: list[SubtitleStream] = Field(default_factory=list)

    @property
    def best(self) -> SubtitleStream | None:
        """Get the best available subtitle (prefers manual over auto-generated)."""

        if not self.streams:
            return None

        # Manual first
        manual = [s for s in self.streams if s.is_manual]

        if manual:
            return manual[0]

        # Then auto
        return self.streams[0]

    def filter(
        self,
        language: str | None = None,
        manual_only: bool = False,
        extension: str | None = None,
    ) -> "SubtitleStreamCollection":
        """
        Filter subtitles by criteria.

        Returns a new SubtitleStreamCollection.
        """

        filtered = self.streams

        if language:
            filtered = [s for s in filtered if s.language and language.lower() in s.language.lower()]
        if manual_only:
            filtered = [s for s in filtered if s.is_manual]
        if extension:
            filtered = [s for s in filtered if s.extension.lower() == extension.lower()]

        return SubtitleStreamCollection(streams=filtered)

    def first(self) -> SubtitleStream | None:
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
