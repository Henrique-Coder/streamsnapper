<div align="center">

# StreamSnapper

![PyPI - Version](https://img.shields.io/pypi/v/streamsnapper?style=for-the-badge&logo=pypi&logoColor=white&color=0066cc)
![Python Versions](https://img.shields.io/pypi/pyversions/streamsnapper?style=for-the-badge&logo=python&logoColor=white&color=306998)
![License](https://img.shields.io/pypi/l/streamsnapper?style=for-the-badge&color=blue)
![Code Style](https://img.shields.io/badge/code%20style-ruff-000000.svg?style=for-the-badge)

**Intuitive, high-performance YouTube data extraction library for Python.**

[🚀 Quick Start](#-quick-start) • [📖 API Reference](#-api-reference) • [💡 Examples](#-examples)

</div>

---

## 🌟 Overview

StreamSnapper provides a clean, pythonic interface for extracting YouTube metadata and streams. It wraps `yt-dlp` with an intuitive object-oriented API, automatic quality enhancements, and robust type safety.

- **Intuitive API**: Access data via properties (`yt.streams.video.best`).
- **Smart Categorization**: Videos, audios, and subtitles are automatically sorted and filtered.
- **Modern Tech**: Built with `pydantic` v2 and `orjson` for high performance.
- **AI Detection**: Automatically detects AI-upscaled content.
- **Type Safe**: Fully typed for excellent IDE support.

## 🔧 Installation

```bash
# Using uv (Recommended)
uv add streamsnapper

# Using pip
pip install streamsnapper
```

**Requirements:** Python 3.10+

## 🚀 Quick Start

### Basic Usage

```python
from streamsnapper import YouTube

# automatic extraction on initialization
yt = YouTube("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

# Video Metadata
print(f"Title: {yt.metadata.title}")
print(f"Views: {yt.metadata.view_count}")
print(f"Duration: {yt.metadata.duration_formatted}")

# Stream Access (Automatically sorted by quality)
print(f"Best Video: {yt.streams.video.best.url}")
print(f"Best Audio: {yt.streams.audio.best.url}")
```

### Filtering Streams

StreamSnapper offers a readable fluent interface for filtering:

```python
# specific resolution
stream = yt.streams.video.filter(resolution="1080p").best

# specific codec and frame rate
stream = yt.streams.video.filter(codec="vp9", fps=60).best

# High quality audio
stream = yt.streams.audio.filter(min_bitrate=128).best
```

## 💡 Key Features

### Intelligent Thumbnails

We automatically filter and deduplicate thumbnails to give you exactly what you need:

- `yt.metadata.thumbnails`: A curated list of high-quality thumbnails (maxres, sd, hq).
- `yt.metadata.all_thumbnails`: The complete raw list of all available thumbnails.

### AI Upscaling Detection

Detects if a stream has been AI-upscaled (e.g., "1080p Premium" or similar enhancements):

```python
if stream.is_ai_upscaled:
    print("This stream is AI upscaled!")
```

### JSON Serialization

All models support high-performance JSON serialization using `orjson`:

```python
json_data = yt.metadata.to_json()
```

## 📖 API Reference

### `YouTube` Class

The main entry point.

```python
yt = YouTube(
    url="https://...",
    cookies=None,      # Optional: CookieFile or SupportedCookieBrowser
    logging=False      # Optional: Enable verbose logging
)
```

**Properties:**

- `.metadata`: `VideoInformation` object (title, id, description, stats, etc.)
- `.streams`: `Streams` object containing:
  - `.video`: `VideoStreamCollection`
  - `.audio`: `AudioStreamCollection`
  - `.subtitle`: `SubtitleStreamCollection`

### `VideoStream` Model

Represents a single video format. Key attributes:

- `url`: Direct download URL.
- `resolution`: string (e.g., "1080p").
- `codec`: string (e.g., "vp9").
- `bitrate`: float (Mbps/Kbps).
- `is_hdr`: boolean.
- `is_ai_upscaled`: boolean.

## 🛡️ Authentication (Premium/Age-Restricted)

Access private or age-restricted content using cookies:

```python
from streamsnapper import YouTube, SupportedCookieBrowser, CookieFile

# Use cookies from local Chrome browser
yt = YouTube(url, cookies=SupportedCookieBrowser.CHROME)

# Use a Netscape-formatted cookie file
yt = YouTube(url, cookies=CookieFile("cookies.txt"))
```

## 📝 License

MIT License - see [LICENSE](LICENSE) file.
