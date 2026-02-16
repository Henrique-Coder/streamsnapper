from collections.abc import Callable
from contextlib import suppress
from enum import Enum
from json import JSONDecodeError
from locale import LC_ALL, getlocale, setlocale
from pathlib import Path
from re import sub
from typing import Any, Final
from unicodedata import normalize

from curl_cffi.requests import Session
from pydantic import BaseModel, ConfigDict, field_validator

from .logger import logger


DEFAULT_FILENAME_MAX_LENGTH: Final[int] = 100
DEFAULT_LANGUAGE_FALLBACK: Final[str] = "en-US"
DEFAULT_REQUEST_TIMEOUT: Final[int] = 5
YOUTUBE_DISLIKE_API_URL: Final[str] = "https://returnyoutubedislikeapi.com/votes"

INVALID_FILENAME_CHARS_PATTERN: Final[str] = r'[<>:"/\\|?*\0\t\n\r\v\f]'
WHITESPACE_PATTERN: Final[str] = r"\s+"


class CookieBrowser(str, Enum):
    """Supported browsers for extracting cookies."""

    CHROME = "chrome"
    FIREFOX = "firefox"
    EDGE = "edge"
    SAFARI = "safari"
    OPERA = "opera"
    BRAVE = "brave"
    CHROMIUM = "chromium"


class CookieFile(BaseModel):
    """
    Represents a cookie file with path validation.

    Validates that the provided path exists and is a file.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    path: Path

    @field_validator("path", mode="before")
    @classmethod
    def validate_path(cls, v: str | Path) -> Path:
        """
        Validate and convert path to Path object.

        Args:
            v: Path as string or Path object

        Returns:
            Validated Path object

        Raises:
            ValueError: If path is not a file
        """
        path = Path(v) if isinstance(v, str) else v

        if not path.exists():
            logger.warning(f"Cookie file does not exist: {path}")
        elif not path.is_file():
            raise ValueError(f"Cookie path is not a file: {path}")
        else:
            logger.debug(f"Cookie file initialized: {path}")

        return path

    def __str__(self) -> str:
        """Return file path as POSIX string."""
        return self.path.as_posix()


def get_value(
    data: dict[Any, Any],
    key: Any,
    fallback_keys: list[Any] | None = None,
    *,
    convert_to: Callable[..., Any] | list[Callable[..., Any]] | None = None,
    default_to: Any = None,
) -> Any:
    """
    Extract value from dictionary with fallback keys and type conversion.

    Args:
        data: The dictionary to extract value from
        key: Primary key to look for
        fallback_keys: Alternative keys if primary key fails
        convert_to: Function(s) to convert the value (keyword-only)
        default_to: Default value if extraction/conversion fails (keyword-only)

    Returns:
        Extracted and converted value or default
    """
    logger.trace(f"Extracting value for key: {key}")

    if not isinstance(data, dict):
        logger.trace(f"Data is not a dictionary, returning default: {default_to}")
        return default_to

    value = data.get(key)

    if value is None and fallback_keys:
        for fallback_key in fallback_keys:
            if fallback_key is not None:
                value = data.get(fallback_key)
                if value is not None:
                    logger.trace(f"Found value using fallback key: {fallback_key}")
                    break

    if value is None:
        logger.trace(f"No value found for key {key}, returning default: {default_to}")
        return default_to

    if convert_to is None:
        return value

    converters = [convert_to] if not isinstance(convert_to, list) else convert_to

    for converter in converters:
        with suppress(ValueError, TypeError):
            converted_value = converter(value)  # type: ignore[call-non-callable]
            converter_name = getattr(converter, "__name__", str(converter))
            logger.trace(f"Successfully converted value using {converter_name}")
            return converted_value

        converter_name = getattr(converter, "__name__", str(converter))
        logger.trace(f"Conversion failed with {converter_name}")

    logger.warning(f"All conversions failed for key {key}, returning default")
    return default_to


def sanitize_filename(text: str, max_length: int | None = DEFAULT_FILENAME_MAX_LENGTH) -> str | None:
    """
    Sanitize text for use as filename, limiting to max_length characters.

    Removes invalid characters, normalizes unicode, and truncates if necessary.

    Args:
        text: Text to sanitize
        max_length: Maximum allowed length for the filename or None for no limit

    Returns:
        Sanitized filename or None if empty after sanitization
    """
    if not text:
        logger.warning("No text provided for filename sanitization")
        return None

    logger.trace(f"Sanitizing filename from text: '{text}'")

    normalized = normalize("NFKD", text)
    ascii_text = normalized.encode("ASCII", "ignore").decode("utf-8")
    cleaned = sub(INVALID_FILENAME_CHARS_PATTERN, "", ascii_text)
    cleaned = sub(WHITESPACE_PATTERN, " ", cleaned).strip()

    if max_length and len(cleaned) > max_length:
        cutoff = cleaned[:max_length].rfind(" ")
        cleaned = cleaned[:cutoff] if cutoff != -1 else cleaned[:max_length]
        cleaned = cleaned.rstrip()

    result = cleaned or None
    logger.trace(f"Sanitized filename: '{result}' from original text: '{text}'")

    return result


def strip_whitespace(value: Any) -> str:
    """
    Strip whitespace from any value converted to string.

    Args:
        value: Value to strip

    Returns:
        Stripped string
    """
    return str(value).strip()


def format_duration(seconds: int | None) -> str:
    """
    Format duration in seconds to human readable format (HH:MM:SS).

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string (HH:MM:SS) or "Unknown" if None
    """
    if seconds is None:
        return "Unknown"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def detect_system_language(fallback: str = DEFAULT_LANGUAGE_FALLBACK) -> str:
    """
    Detect system language using the most reliable method.

    Args:
        fallback: Fallback language code if detection fails

    Returns:
        Language code in format "en-US" (fallback: "en-US")
    """
    try:
        setlocale(LC_ALL, "")
        system_locale = getlocale()[0]

        if system_locale and "_" in system_locale:
            language_code = system_locale.split(".")[0].replace("_", "-")
            logger.debug(f"Detected system language: {language_code}")
            return language_code
    except Exception as e:
        logger.warning(f"Language detection failed: {e!r}")

    logger.info(f"Using fallback language: {fallback}")
    return fallback


def filter_valid_youtube_thumbnails(thumbnails: list[str]) -> list[str]:
    """
    Filter YouTube thumbnail URLs, returning list starting from first valid thumbnail.

    Stops at first valid thumbnail found.

    Args:
        thumbnails: List of YouTube thumbnail URLs to validate

    Returns:
        List starting from first valid thumbnail, or empty list if none valid
    """
    if not thumbnails:
        return []

    with Session() as session:
        for index, url in enumerate(thumbnails):
            try:
                response = session.head(url, allow_redirects=False, timeout=DEFAULT_REQUEST_TIMEOUT)

                if response.ok:
                    logger.trace(f"First valid YouTube thumbnail found: {url}")
                    return thumbnails[index:]

                logger.trace(f"Invalid YouTube thumbnail (non-success response): {url}")
            except Exception as e:  # noqa: PERF203
                logger.trace(f"Invalid YouTube thumbnail (request exception): {url} - {e!r}")

    logger.debug("No valid YouTube thumbnails found")
    return []


def get_youtube_dislike_count(video_id: str) -> int | None:
    """
    Retrieve dislike count for YouTube video from external API.

    Args:
        video_id: YouTube video ID

    Returns:
        Dislike count as integer or None if unavailable/failed
    """
    try:
        with Session() as session:
            response = session.get(
                YOUTUBE_DISLIKE_API_URL,
                params={"videoId": video_id},
                timeout=DEFAULT_REQUEST_TIMEOUT,
            )

            if response.ok:
                with suppress(JSONDecodeError):
                    dislike_count = get_value(response.json(), "dislikes", convert_to=int)

                    if dislike_count is not None:
                        logger.trace(f"Retrieved dislike count for {video_id}: {dislike_count}")
                        return dislike_count

                    logger.trace(f"No dislike data available for video: {video_id}")
            else:
                logger.trace(f"Failed to fetch dislike count (non-success response): {video_id}")
    except Exception as e:
        logger.trace(f"Failed to fetch dislike count (request exception): {video_id} - {e!r}")

    return None
