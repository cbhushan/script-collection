"""
Rename media files using their creation datetime metadata.

This script walks through a directory of photos and videos, extracts creation
timestamps from metadata, and renames files with date-based filenames
(YYYYMMDD_HHMMSS format).

External Applications Required; these must be in PATH:
  - exiftool: Extract metadata from image and video files
    Install: apt install exiftool (Debian/Ubuntu)
  - ffprobe: Extract metadata from video files
    Install: apt install ffmpeg (Debian/Ubuntu)

Python Package Dependencies:
  - piexif: EXIF metadata extraction (optional but preferred, falls back to PIL)
  - Pillow: Image handling and EXIF reading
  - python-dateutil: Date parsing and timezone handling

Tested with Python 3.13.2.
"""
import argparse
import os
import sys
import json
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from dateutil import parser, tz
import pprint
import random
import string
import shutil

try:
    import piexif
except Exception:
    piexif = None

from PIL import Image


# Ordered list of exif tags to guess date-time
EXIF_DATE_TAGS = [
    "SubSecDateTimeOriginal",
    "SubSecCreateDate",
    "DateTimeOriginal",
    "CreationDate",
    "CreateDate",
    "MediaCreateDate",
    "DateTimeCreated",
    "DateTimeDigitized",
    "GPSDateTime",
    "DateTimeUTC",
    "DateTime",
    "SonyDateTime2",
    "SourceImageCreateTime",
]

# Ordered list of other (non-exif) tags to guess date-time
OTHER_DATE_TAGS = [
    "DateTime",
    "CreateDate",
    "CreationDate",
    "ModifyDate",
]


def randstr(length):
    # Choose characters: letters (upper/lower) and digits
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters, k=length))


def _bytes_to_str(value: Any) -> str:
    """Convert bytes or other types to UTF-8 string.

    Args:
        value: Input value (bytes, bytearray, or other type).

    Returns:
        UTF-8 decoded string, or string representation if not bytes.
    """
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", "ignore")
    return str(value)


def _parse_datetime(raw: Any) -> Optional[datetime]:
    """Parse a raw datetime string or bytes into a datetime object.

    Handles various input formats including bytes and strings, defaulting to UTC
    timezone if not specified. Specifically handles EXIF format (YYYY:MM:DD HH:MM:SS).

    Args:
        raw: Raw datetime value (string, bytes, or datetime-like object).

    Returns:
        Parsed datetime object in UTC, or None if parsing fails.
    """
    if raw is None:
        return None

    raw = _bytes_to_str(raw).strip()

    # Handle EXIF format: YYYY:MM:DD HH:MM:SS
    if len(raw) >= 19 and raw[4] == ':' and raw[7] == ':':
        try:
            # Convert YYYY:MM:DD HH:MM:SS to YYYY-MM-DD HH:MM:SS
            normalized = raw[:4] + '-' + raw[5:7] + '-' + raw[8:10] + raw[10:]
            dt = parser.parse(normalized)
            if dt.tzinfo is None:
                if raw.endswith("+00:00"):
                    dt = dt.replace(tzinfo=tz.UTC)
                else:
                    dt = dt.replace(tzinfo=tz.tzlocal())
            return dt
        except Exception:
            pass

    try:
        dt = parser.parse(raw)
    except Exception:
        return None

    if dt.tzinfo is None:
        if raw.endswith("+00:00"):
            dt = dt.replace(tzinfo=tz.UTC)
        else:
            dt = dt.replace(tzinfo=tz.tzlocal())
    return dt


def local_date_equivalent(dt: datetime) -> datetime:
    """Convert a datetime to its local date equivalent on the system.

    Converts timezone-aware datetime to the local timezone representation.
    If already naive, assumes UTC and converts to local.

    Args:
        dt: Input datetime object.

    Returns:
        Datetime object converted to the local system timezone.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz.UTC).astimezone(tz.tzlocal())
    return dt.astimezone(tz.tzlocal())


def _build_datetime_result(
    dt: datetime, raw: Optional[str] = None, source: str = "unknown", source_tag: str = 'unknown'
) -> Dict[str, Any]:
    """Build a standardized datetime result dictionary.

    Args:
        dt: Parsed datetime object.
        raw: Raw datetime string (optional).
        source: Source of the datetime (e.g., 'exiftool', 'sidecar', 'file_mtime').

    Returns:
        Dictionary with date_time_original, local_date_time, time_zone, raw, and source.
    """
    return {
        "date_time_original": dt,
        "local_date_time": local_date_equivalent(dt),
        "time_zone": dt.tzinfo.tzname(dt) if dt.tzinfo else None,
        "raw": raw,
        "source": source,
        "source_tag": source_tag,
    }

def file_times(path: str) -> Tuple[datetime, datetime]:
    """Get the earliest and modification times of a file.

    Attempts to get the birth time (creation time) if available, otherwise uses
    modification time. Returns the minimum of birth and modification times.

    Args:
        path: File path.

    Returns:
        Tuple of (earliest_time, modification_time) as datetime objects in UTC.
    """
    st = os.stat(path)
    mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
    birth = getattr(st, "st_birthtime", None)
    if birth:
        birth_dt = datetime.fromtimestamp(birth, tz=timezone.utc)
        earliest = min(birth_dt, mtime)
    else:
        earliest = mtime

    return earliest, mtime


def parse_xmp_sidecar(path: str) -> Dict[str, str]:
    """Parse datetime metadata from an XMP sidecar file.

    Extracts all date-related tags from an XMP XML file and returns them as a dict.

    Args:
        path: Path to XMP sidecar file.

    Returns:
        Dictionary mapping tag names to datetime string values. Returns empty dict if parsing fails.
    """
    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except Exception:
        return {}

    result: Dict[str, str] = {}
    for elem in root.iter():
        tag_local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        text = _bytes_to_str(elem.text or "").strip()
        if text and (tag_local in EXIF_DATE_TAGS or tag_local in ("CreateDate", "CreationDate", "DateTimeOriginal")):
            result[tag_local] = text
    return result


def run_exiftool(path: str) -> Optional[Dict[str, Any]]:
    """Run exiftool on a file and return metadata as JSON.

    Executes exiftool with JSON output format and parses the result.

    Args:
        path: File path to extract metadata from.

    Returns:
        Dictionary of metadata extracted by exiftool, or None if execution fails.
    """
    try:
        out = subprocess.check_output(["exiftool", "-json", path], stderr=subprocess.DEVNULL)
        arr = json.loads(out)
        if isinstance(arr, list) and arr:
            return arr[0]
    except Exception:
        return None
    return None


def read_exif(path: str, use_exiftool: bool = True) -> Dict[str, Any]:
    """Extract EXIF metadata from an image file using multiple methods.

    Attempts to read EXIF data using piexif first, then Pillow as fallback, and
    optionally exiftool if no date tags are found.

    Args:
        path: Path to image file.
        use_exiftool: If True, use exiftool as fallback when no date tags found. Defaults to True.

    Returns:
        Dictionary of EXIF tags with date-related metadata.
    """
    tags: Dict[str, Any] = {}
    src = None
    if piexif:
        try:
            exif_dict = piexif.load(path)
            date0 = exif_dict.get("0th", {}).get(piexif.ImageIFD.DateTime)
            date_orig = exif_dict.get("Exif", {}).get(piexif.ExifIFD.DateTimeOriginal)
            date_digit = exif_dict.get("Exif", {}).get(piexif.ExifIFD.DateTimeDigitized)
            if date_orig:
                tags["DateTimeOriginal"] = _bytes_to_str(date_orig)
            if date_digit:
                tags["DateTimeDigitized"] = _bytes_to_str(date_digit)
            if date0:
                tags["DateTime"] = _bytes_to_str(date0)

            gps_date = exif_dict.get("GPS", {}).get(piexif.GPSIFD.GPSDateStamp)
            gps_time = exif_dict.get("GPS", {}).get(piexif.GPSIFD.GPSTimeStamp)
            if gps_date and gps_time:
                try:
                    h = int(gps_time[0][0] / gps_time[0][1])
                    m = int(gps_time[1][0] / gps_time[1][1])
                    s = int(gps_time[2][0] / gps_time[2][1])
                    gd = _bytes_to_str(gps_date)
                    tags["GPSDateTime"] = f"{gd} {h:02}:{m:02}:{s:02}"
                except Exception:
                    pass
        except Exception:
            pass

    if tags:  # tags are already found
        src = 'piexif'

    else:  # Pillow fallback
        try:
            img = Image.open(path)
            raw = img._getexif() or {}
            for k, v in raw.items():
                name = Image.ExifTags.TAGS.get(k, k)
                if name in ("DateTimeOriginal", "DateTime", "DateTimeDigitized", "CreateDate"):
                    tags[name] = v
                    src = 'Pillow'
        except Exception:
            pass

    # optional exiftool fallback if no date tags
    if use_exiftool and not any(t in tags for t in ("DateTimeOriginal", "DateTime", "GPSDateTime", "CreateDate")):
        et = run_exiftool(path)
        if et:
            for key in EXIF_DATE_TAGS + OTHER_DATE_TAGS:
                if key in et and et[key]:
                    tags[key] = et[key]
                    src = 'exiftool'

            for tzkey in ("tz", "TimeZone", "Timezone", "tzSource"):
                if tzkey in et:
                    tags[tzkey] = et[tzkey]
    return tags, src


def first_date_time_from_map(tags_map: Dict[str, Any]) -> Tuple[Optional[str], Optional[datetime], Optional[str]]:
    """Extract the first valid datetime from a metadata tags dictionary.

    Searches through a priority list of date-related tags and returns the first
    one that can be parsed successfully.

    Args:
        tags_map: Dictionary of metadata tags with potential datetime values.

    Returns:
        Tuple of (tag_name, parsed_datetime, raw_value) or (None, None, None) if no valid datetime found.
    """
    for tag in EXIF_DATE_TAGS + OTHER_DATE_TAGS:
        if tag in tags_map and tags_map[tag]:
            parsed = _parse_datetime(tags_map[tag])
            if parsed:
                return tag, parsed, str(tags_map[tag])

    return None, None, None


def get_photo_created_datetime(path: str, use_exiftool: bool = True) -> Dict[str, Any]:
    """Get the creation datetime of a photo file.

    Attempts to find creation datetime by checking XMP sidecar files first, then
    EXIF metadata, and finally file modification time as fallback.

    Args:
        path: Path to photo file.
        use_exiftool: If True, use exiftool as fallback. Defaults to True.

    Returns:
        Dictionary with keys: date_time_original (datetime), local_date_time (datetime),
        time_zone (str), raw (str or None), and source (str indicating metadata source).
    """
    base = os.path.splitext(path)[0]
    for sc in (f"{path}.xmp", f"{base}.xmp"):
        if os.path.isfile(sc):
            sc_map = parse_xmp_sidecar(sc)
            tag, dt, raw = first_date_time_from_map(sc_map)
            if dt:
                return _build_datetime_result(dt, raw, "sidecar", tag)

    exif_map, src = read_exif(path, use_exiftool=use_exiftool)
    tag, dt, raw = first_date_time_from_map(exif_map)
    if dt:
        return _build_datetime_result(dt, raw, src, tag)

    # fallback file modification time
    earliest, _ = file_times(path)
    return _build_datetime_result(earliest, None, "file_mtime")


def ffprobe_creation_time(path: str) -> Optional[str]:
    """Extract creation time from a video file using ffprobe.

    Runs ffprobe to get metadata including creation_time from format tags or stream tags.

    Args:
        path: Path to video file.

    Returns:
        Creation time string from metadata, or None if not found or ffprobe fails.
    """
    try:
        out = subprocess.check_output(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", path], stderr=subprocess.DEVNULL)
        info = json.loads(out)
        candidates = []
        fmt = info.get("format", {})
        tags = fmt.get("tags", {}) if isinstance(fmt, dict) else {}

        for k in ("creation_time", "Creation_time", "create_time"):
            if k in tags:
                candidates.append(tags[k])

        for s in info.get("streams", []):
            if isinstance(s, dict):
                stags = s.get("tags", {})
                if isinstance(stags, dict) and "creation_time" in stags:
                    candidates.append(stags["creation_time"])

        return candidates[0] if candidates else None

    except Exception:
        return None


def get_video_created_datetime(path: str, use_exiftool: bool = True) -> Dict[str, Any]:
    """Get the creation datetime of a video file.

    Attempts to find creation datetime by checking ffprobe metadata first, then
    XMP sidecar files, exiftool, and finally file modification time as fallback.

    Args:
        path: Path to video file.
        use_exiftool: If True, use exiftool for metadata extraction. Defaults to True.

    Returns:
        Dictionary with keys: date_time_original (datetime), local_date_time (datetime),
        time_zone (str), raw (str or None), and source (str indicating metadata source).
    """
    raw = ffprobe_creation_time(path)
    if raw:
        dt = _parse_datetime(raw)
        if dt:
            return _build_datetime_result(dt, raw, "ffprobe", "ffprobe")

    base = os.path.splitext(path)[0]
    for sc in (f"{path}.xmp", f"{base}.xmp"):
        if os.path.isfile(sc):
            sc_map = parse_xmp_sidecar(sc)
            tag, dt, raw = first_date_time_from_map(sc_map)
            if dt:
                return _build_datetime_result(dt, raw, "sidecar", tag)

    if use_exiftool:
        et = run_exiftool(path)
        if et:
            tag, dt, raw = first_date_time_from_map(et)
            if dt:
                return _build_datetime_result(dt, raw, "exiftool", tag)


    earliest, _ = file_times(path)
    return _build_datetime_result(earliest, None, "file_mtime")


def date_based_filename(path: str, outdir: str, use_exiftool: bool = True, debug=False) -> Dict[str, Any]:
    """Uses creation datetime of a media file (photo or video) to generate date-based filename.

    Args:
        path: Path to media file (photo or video).
        outdir: Path to output directory.
        use_exiftool: If True, use exiftool as fallback. Defaults to True.
        debug: If True, date-time detection output is also printed.

    Returns:
        file_out (str): Path to output filename that is based on media creation date-time.
                        For non media files, it returns None
    """
    _, ext = os.path.splitext(path)
    ext = ext.lower()

    # Common photo extensions
    photo_extensions = {
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif",
        ".raw", ".webp", ".heic", ".ico", ".svg",
    }

    # Common video extensions
    video_extensions = {
        ".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm",
        ".m4v", ".mpg", ".mpeg", ".3gp", ".ogv", ".ts",
    }

    if ext in photo_extensions:
        dt = get_photo_created_datetime(path, use_exiftool=use_exiftool)

    elif ext in video_extensions:
        dt = get_video_created_datetime(path, use_exiftool=use_exiftool)

    else:
        if debug:
            print(
                f"[WARN] Unsupported file extension '{ext}'. "
                f"Supported photo formats: {', '.join(sorted(photo_extensions))}. "
                f"Supported video formats: {', '.join(sorted(video_extensions))}."
            )
        return None

    if debug:
        pprint.pprint(f'path={path}')
        pprint.pprint(dt)

    if dt["source"] in ("ffprobe", 'piexif', 'exiftool', 'Pillow'):
        fnbase = dt["local_date_time"].strftime('%Y%m%d_%H%M%S')

        fn_out = os.path.join(outdir, f'{fnbase}{ext}')
        if os.path.exists(fn_out):
            fn_out = os.path.join(outdir, f'{fnbase}_{randstr(5)}{ext}')

    else:  # unreliable date extraction
        if debug:
            print(f'[WARN] Date was not reliably detected: {path}')
        fn_out = None

    return fn_out


def rename_w_date_based_filename(src_dir, out_dir, actually_move=False, debug=False):
    """Rename media files using date-based filenames.

    Walks a source directory, generates destination paths based on each file's
    creation metadata, and moves the files into the output directory only if
    `actually_move=True`.

    Args:
        src_dir: Directory to scan for media files.
        out_dir: Directory to store renamed files.
        actually_move: If True, move files instead of dry-run.
        debug: If True, show debugging output for date extraction.
    """
    os.makedirs(out_dir, exist_ok=True)

    not_moved = []
    for dirpath, dirnames, filenames in os.walk(src_dir):
        for file_name in filenames:
            if debug:
                print("----------------------------------------\n")

            src_file = os.path.join(dirpath, file_name)
            dest_file = date_based_filename(src_file, out_dir, debug=debug)
            src_base, sext = os.path.splitext(os.path.basename(src_file))

            if dest_file is None:
                not_moved.append(src_file)
                print(f'SKIP - {src_file}')
                continue

                # fn_out = os.path.join(outdir, os.path.basename(path))
                # if os.path.exists(fn_out):

                #     fnbase, _ = os.path.splitext(os.path.basename(path))
                #     fn_out = os.path.join(outdir, f'{fnbase}_{randstr(5)}{ext}')

            # log
            dest_base, dext = os.path.splitext(os.path.basename(dest_file))

            cleaned_src = src_base.removeprefix("PXL_")
            cleaned_src = cleaned_src.removeprefix("VID_")
            cleaned_src = cleaned_src.removeprefix("IMG_")

            if cleaned_src.startswith(dest_base):
                prefix_str = '  '
            else:
                prefix_str = '##'

            # move / rename
            if actually_move:
                prefix_str = f'{prefix_str}   '
                shutil.move(src_file, dest_file)
            else:
                prefix_str = f'{prefix_str} (dry-run)'

            print(f'{prefix_str} {src_base}{sext} --> {dest_base}{dext}')

    # show not moved
    print(f'Following files can not be moved, due to unreliable date/time estimate:')
    pprint.pprint(not_moved)

    return not_moved


def test_w_samples():
    src_files = [
        '/mnt/data2/Pictures/to_be_renamed/20210828_113313_069.jpg',
        '/mnt/data2/Pictures/to_be_renamed/20210626_182050.jpg',
        '/mnt/data2/Pictures/to_be_renamed/PXL_20220102_212132654.mp4',
    ]

    out_dir = '/mnt/data2/tmp/try'

    for src_file in src_files:
        print('\n--------------------')
        dest_file = date_based_filename(src_file, out_dir, debug=True)

        src_base, sext = os.path.splitext(os.path.basename(src_file))
        dest_base, dext = os.path.splitext(os.path.basename(dest_file))

        if src_base.startswith(dest_base):
            prefix_str = '     '
        else:
            prefix_str = '##   '

        print(f'{prefix_str}{src_base}{sext} --> {dest_base}{dext}')


if __name__ == "__main__":
    # test_w_samples()
    # sys.exit(1)

    arg_parser = argparse.ArgumentParser(
        description="Rename media files in a source directory using date-based filenames."
    )
    arg_parser.add_argument("--src_dir", help="Source directory containing media files")
    arg_parser.add_argument("--out_dir", help="Output directory for renamed files")
    arg_parser.add_argument(
        "--actually-move",
        action="store_true",
        help="Move files instead of performing a dry run",
    )
    arg_parser.add_argument(
        "--debug",
        action="store_true",
        help="Show debugging information when datetime extraction is unreliable",
    )

    if len(sys.argv) == 1:
        arg_parser.print_help()
        sys.exit(0)

    args = arg_parser.parse_args()

    rename_w_date_based_filename(
        args.src_dir,
        args.out_dir,
        actually_move=args.actually_move,
        debug=args.debug,
    )

    if not args.actually_move:
        print('----------------------------------------------------------------')
        print('[WARN] Above output is dry-run; no files are renamed!\n' \
        'Check above name mapping and re-run the command with --actually-move flag \n'
        'for actual renaming/moving!')
        print('----------------------------------------------------------------')
