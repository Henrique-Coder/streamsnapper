from typing import Any

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError

from .exceptions import ScrapingError
from .logger import logger
from .models import (
    AudioStream,
    AudioStreamCollection,
    SubtitleStream,
    SubtitleStreamCollection,
    VideoInformation,
    VideoStream,
    VideoStreamCollection,
)
from .utils import (
    CookieBrowser,
    CookieFile,
    filter_valid_youtube_thumbnails,
    get_youtube_dislike_count,
    sanitize_filename,
)


class Streams:
    """Container for all media streams."""

    def __init__(
        self,
        video: VideoStreamCollection,
        audio: AudioStreamCollection,
        subtitle: SubtitleStreamCollection,
    ):
        self.video = video
        self.audio = audio
        self.subtitle = subtitle


class YouTube:
    """
    Intuitive YouTube video extractor.

    Usage:
        yt = YouTube("https://youtu.be/...")
        print(yt.metadata.title)
        print(yt.streams.video.best.url)
    """

    def __init__(
        self,
        url: str,
        cookies: CookieBrowser | CookieFile | None = None,
        logging: bool = False,
    ) -> None:
        """
        Initialize and extract data immediately.

        Args:
            url: YouTube video URL.
            cookies: Cookie source for accessing restricted content.
            logging: Enable detailed logging.
        """

        self.url = url
        self._logging = logging

        if not logging:
            logger.remove()

        self._ydl_opts: dict[str, Any] = {
            "extract_flat": False,
            "geo_bypass": True,
            "noplaylist": True,
            "age_limit": None,
            "quiet": not logging,
            "no_warnings": not logging,
            "logger": logger if logging else None,
        }

        self._configure_cookies(cookies)

        # Storage for extracted data
        self._raw_data: dict[str, Any] = {}
        self.metadata: VideoInformation = VideoInformation()
        self.streams: Streams | None = None

        # Perform extraction immediately
        self._extract()

    def _configure_cookies(self, cookies: CookieBrowser | CookieFile | None) -> None:
        if isinstance(cookies, CookieBrowser):
            self._ydl_opts["cookiesfrombrowser"] = (cookies.value, None, None, None)

            if self._logging:
                logger.info(f"Enabled cookie extraction from {cookies.value}")
        elif isinstance(cookies, CookieFile):
            self._ydl_opts["cookiefile"] = cookies.path.as_posix()

            if self._logging:
                logger.info(f"Enabled cookie file: {cookies.path}")

    def _extract(self) -> None:
        """Internal method to extract data using yt-dlp."""
        if self._logging:
            logger.info(f"Extracting data from: {self.url}")

        try:
            with YoutubeDL(self._ydl_opts) as ydl:
                self._raw_data = ydl.extract_info(self.url, download=False)
        except (DownloadError, ExtractorError, Exception) as e:
            raise ScrapingError(f"Failed to extract - {e}") from e

        self._parse_metadata()
        self._parse_streams()

    def _parse_metadata(self) -> None:
        """Parse raw data into VideoInformation."""
        data = self._raw_data
        video_id = data.get("id")

        self.metadata = VideoInformation(
            source_url=self.url,
            short_url=f"https://youtu.be/{video_id}" if video_id else None,
            embed_url=f"https://www.youtube.com/embed/{video_id}" if video_id else None,
            full_url=data.get("webpage_url") or self.url,
            id=video_id,
            title=data.get("fulltitle") or data.get("title"),
            clean_title=sanitize_filename(data.get("title") or ""),
            description=data.get("description"),
            channel_id=data.get("channel_id"),
            channel_url=data.get("channel_url"),
            channel_name=data.get("channel") or data.get("uploader"),
            clean_channel_name=sanitize_filename(data.get("channel") or ""),
            is_verified_channel=data.get("channel_is_verified", False),
            duration=data.get("duration"),
            view_count=data.get("view_count"),
            like_count=data.get("like_count"),
            comment_count=data.get("comment_count"),
            is_age_restricted=data.get("age_limit", 0) > 0,
            categories=data.get("categories", []),
            tags=data.get("tags", []),
            is_streaming=data.get("is_live", False),
            upload_timestamp=data.get("timestamp") or data.get("release_timestamp"),
        )
        # Generate candidate URLs for best thumbnails
        candidates = (
            [
                f"https://i.ytimg.com/vi/{video_id}/{quality}.jpg"
                for quality in ["maxresdefault", "sddefault", "hqdefault", "mqdefault", "default"]
            ]
            if video_id
            else []
        )

        # Filter valid thumbnails
        best_thumbnails = filter_valid_youtube_thumbnails(candidates)
        unique_urls: set[str] = {str(t.get("url")) for t in data.get("thumbnails", []) if t.get("url")}
        all_thumbnails: list[str] = sorted(unique_urls, key=lambda x: len(x))

        self.metadata.thumbnails = best_thumbnails
        self.metadata.all_thumbnails = all_thumbnails

    def _parse_streams(self) -> None:
        """Parse formats into Video, Audio, and Subtitle collections."""
        formats = self._raw_data.get("formats", [])
        subtitles = self._raw_data.get("subtitles", {})

        video_list = []
        audio_list = []

        # Stream mapping
        for f in formats:
            # Skip if no url (e.g. dash segments sometimes)
            if not f.get("url"):
                continue

            # Check if video
            if f.get("vcodec") != "none":
                video_list.append(
                    VideoStream(
                        url=f["url"],
                        source_url=self.url,
                        codec=f.get("vcodec"),
                        extension=f.get("ext", "mp4"),
                        width=f.get("width"),
                        height=f.get("height"),
                        framerate=f.get("fps"),
                        bitrate=f.get("tbr") or f.get("vbr"),
                        quality_note=f.get("format_note"),
                        is_hdr="hdr" in (f.get("format_note") or "").lower(),
                        is_ai_upscaled="ai-upscaled" in (f.get("format_note") or "").lower(),
                        size=f.get("filesize"),
                        youtube_format_id=f.get("format_id"),
                        clean_title=self.metadata.clean_title,
                        id=self.metadata.id,
                    )
                )

            # Check if audio
            if f.get("acodec") != "none" and f.get("vcodec") == "none":
                audio_list.append(
                    AudioStream(
                        url=f["url"],
                        source_url=self.url,
                        codec=f.get("acodec"),
                        extension=f.get("ext", "m4a"),
                        bitrate=f.get("abr"),
                        sample_rate=f.get("asr"),
                        channels=f.get("audio_channels"),
                        language=f.get("language"),
                        size=f.get("filesize"),
                        youtube_format_id=f.get("format_id"),
                        clean_title=self.metadata.clean_title,
                        id=self.metadata.id,
                    )
                )

        # Subtitles processing
        subtitle_list = []
        for lang_code, subs in subtitles.items():
            subtitle_list.extend(
                SubtitleStream(
                    url=sub["url"],
                    extension=sub["ext"],
                    language=lang_code,
                    language_name=sub.get("name"),
                    is_auto_generated=sub.get("name", "").lower().startswith("auto"),  # rough heuristic
                )
                for sub in subs
            )

        self.streams = Streams(
            video=VideoStreamCollection(streams=sorted(video_list, key=lambda s: s.quality_score, reverse=True)),
            audio=AudioStreamCollection(streams=sorted(audio_list, key=lambda s: s.quality_score, reverse=True)),
            subtitle=SubtitleStreamCollection(streams=subtitle_list),
        )

    def preload_dislikes(self) -> None:
        """Fetch dislike count from generic API."""
        if self.metadata and self.metadata.id:
            logger.info("Fetching dislike count...")
            self.metadata.dislike_count = get_youtube_dislike_count(self.metadata.id)
