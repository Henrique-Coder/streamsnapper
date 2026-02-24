"""Mixins for stream models."""

from pathlib import Path
from time import time
from typing import Any

import ffmpeg
from yt_dlp import YoutubeDL

from ..exceptions import DownloadError
from ..logger import logger


class DownloadableStreamMixin:
    """Mixin to add download capability to streams."""

    url: str
    source_url: str | None
    youtube_format_id: str | None
    clean_title: str | None
    id: str | None
    extension: str
    media_type: str | None
    ydl_opts: dict[str, Any]

    def download(
        self,
        output_path: str | Path | None = None,
        filename: str | None = None,
        force_overwrite: bool = False,
        quiet: bool = True,
    ) -> Path:
        """
        Download this specific stream using yt-dlp's engine.

        Strategically chooses the best download method:
        If source_url and youtube_format_id are available, uses yt-dlp to download
        that specific format from the source. This is the BEST method to avoid throttling
        as yt-dlp will solve the 'n' parameter challenge freshly.

        Raises DownloadError if source_url is not available (to avoid throttling or false info).

        Args:
            output_path: Directory to save the file to. Defaults to current directory.
            filename: Specific filename.
            force_overwrite: Whether to overwrite existing files.
            quiet: Suppress stdout/stderr.

        Returns:
            Path to the downloaded file.
        """

        output_path = Path.cwd() if output_path is None else Path(output_path)

        if not output_path.exists():
            output_path.mkdir(parents=True, exist_ok=True)

        # Generate filename if not provided
        if not filename:
            if self.clean_title and self.id:
                # Format: "Clean Title [yt-ID].ext"
                if self.media_type:
                    filename = f"{self.clean_title} ({self.media_type}-only) [yt-{self.id}].{self.extension}"
                else:
                    filename = f"{self.clean_title} [yt-{self.id}].{self.extension}"
            else:
                # Fallback if metadata missing (should rarely happen if initialized correctly)
                timestamp = int(time())
                filename = f"download_{timestamp}.{self.extension}"

        # Ensure extension
        if not filename.endswith(f".{self.extension}"):
            filename = f"{filename}.{self.extension}"

        outtmpl = str(output_path / filename)

        ydl_opts: dict[str, Any] = {
            **self.ydl_opts,
            "outtmpl": outtmpl,
            "quiet": quiet,
            "no_warnings": quiet,
            "overwrites": force_overwrite,
        }

        # Strategy: Smart Download Only (Source + Format ID)
        if self.source_url and self.youtube_format_id:
            if not quiet:
                logger.info(f"Downloading format {self.youtube_format_id} from {self.source_url} to {outtmpl}...")

            # Explicitly tell yt-dlp to download exactly this format
            ydl_opts["format"] = self.youtube_format_id

            try:
                with YoutubeDL(ydl_opts) as ydl:
                    ydl.download([self.source_url])
            except Exception as e:
                raise DownloadError(f"Failed to download stream: {e}") from e

        else:
            # Fallback forbidden by user request
            raise DownloadError(
                "Cannot download stream: missing source_url or youtube_format_id. "
                "Direct URL download is disabled to prevent throttling and ensure data integrity."
            )

        return Path(outtmpl)

    @staticmethod
    def _merge_streams(video_path: Path, audio_path: Path, output_path: Path, overwrite: bool = False) -> None:
        """
        Merge video and audio streams using ffmpeg.

        Args:
            video_path: Path to video file.
            audio_path: Path to audio file.
            output_path: Path to output file.
            overwrite: Whether to overwrite existing output file.

        Raises:
            StreamSnapperError: If merge fails.
        """

        if output_path.exists() and not overwrite:
            raise DownloadError(f"Output file already exists: {output_path}")

        try:
            video = ffmpeg.input(str(video_path))
            audio = ffmpeg.input(str(audio_path))

            ffmpeg.output(
                video,
                audio,
                str(output_path),
                vcodec="copy",
                acodec="copy",
                map_metadata=0,
            ).run(overwrite_output=overwrite, quiet=True)
        except ffmpeg.Error as e:
            raise DownloadError(f"FFmpeg merge failed: {e.stderr.decode() if e.stderr else str(e)}") from e
