"""Audio-related data models."""

from pathlib import Path
from time import time
from typing import TYPE_CHECKING, Any

from orjson import dumps
from pydantic import BaseModel, Field

from ..logger import logger
from .mixins import DownloadableStreamMixin


if TYPE_CHECKING:
    from .video import VideoStream


class AudioStream(BaseModel, DownloadableStreamMixin):
    """Individual audio stream."""

    # Stream info
    url: str
    source_url: str | None = None
    codec: str | None = None
    extension: str
    clean_title: str | None = None
    id: str | None = None
    youtube_format_id: str | None = None

    # Audio properties
    bitrate: float | None = None
    sample_rate: int | None = None
    channels: int | None = None

    # Language and metadata
    language: str | None = None
    size: int | None = None
    media_type: str = "audio"
    ydl_opts: dict[str, Any] = Field(default_factory=dict, exclude=True)

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

    def download_with_video(
        self,
        video: "VideoStream",
        output_path: str | Path | None = None,
        filename: str | None = None,
        force_overwrite: bool = False,
        quiet: bool = True,
    ) -> Path:
        """
        Download audio and merge with provided video stream.

        Args:
            video: The video stream to merge with.
            output_path: Directory to save the file to. Defaults to current directory.
            filename: Specific filename.
            force_overwrite: Whether to overwrite existing files.
            quiet: Suppress stdout/stderr.

        Returns:
            Path to the merged file.
        """

        output_path = Path.cwd() if output_path is None else Path(output_path)

        if not output_path.exists():
            output_path.mkdir(parents=True, exist_ok=True)

        # Generate final filename if not provided
        if not filename:
            if self.clean_title and self.id:
                # Merge format does NOT have (audio-only) suffix
                filename = f"{self.clean_title} [yt-{self.id}].{self.extension}"
            else:
                timestamp = int(time())
                filename = f"merged_{timestamp}.{self.extension}"

        if not filename.endswith(f".{self.extension}"):
            filename = f"{filename}.{self.extension}"

        final_path = output_path / filename

        # Temporary files
        timestamp = int(time())
        video_temp = output_path / f"temp_video_{timestamp}_{video.id}.{video.extension}"
        audio_temp = output_path / f"temp_audio_{timestamp}_{self.id}.{self.extension}"

        try:
            if not quiet:
                logger.info(f"Downloading video stream to temporary file: {video_temp}")

            # Download video to temp
            video.download(
                output_path=output_path,
                filename=video_temp.name,
                force_overwrite=True,  # Temp files are always overwritten
                quiet=quiet,
            )

            if not quiet:
                logger.info(f"Downloading audio stream to temporary file: {audio_temp}")

            # Download audio to temp
            self.download(
                output_path=output_path,
                filename=audio_temp.name,
                force_overwrite=True,  # Temp files are always overwritten
                quiet=quiet,
            )

            if not quiet:
                logger.info(f"Merging streams to: {final_path}")

            # Merge
            self._merge_streams(video_temp, audio_temp, final_path, overwrite=force_overwrite)

            return final_path

        finally:
            # Cleanup temp files
            if video_temp.exists():
                video_temp.unlink()
            if audio_temp.exists():
                audio_temp.unlink()


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
