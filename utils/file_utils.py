import os
import tempfile
import yt_dlp
from moviepy.editor import VideoFileClip
from typing import Optional, Dict

def get_video_metadata(file_path: str) -> Dict:
    """Extract basic metadata from video"""
    try:
        video = VideoFileClip(file_path)
        metadata = {
            "duration": video.duration,
            "size": os.path.getsize(file_path) / (1024 * 1024), # MB
            "fps": video.fps,
            "resolution": f"{video.w}x{video.h}"
        }
        video.close()
        return metadata
    except Exception:
        return {"duration": 0, "size": 0, "fps": 0, "resolution": "Unknown"}

def extract_audio(video_path: str) -> Optional[str]:
    """Extract audio from video file"""
    try:
        video = VideoFileClip(video_path)
        if not video.audio:
            return None
        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
        video.audio.write_audiofile(temp_audio, verbose=False, logger=None)
        video.close()
        return temp_audio
    except Exception:
        return None

def download_youtube_info(url: str) -> Optional[Dict]:
    """Get YouTube video info without downloading full video"""
    ydl_opts = {'quiet': True, 'no_warnings': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get('title'),
                "duration": info.get('duration'),
                "description": info.get('description'),
                "url": url
            }
    except Exception:
        return None
