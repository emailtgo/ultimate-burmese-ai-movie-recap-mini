"""
Utility functions for Ultimate Burmese AI Movie Recap Studio
Handles file validation, metadata extraction, and document processing
"""

import os
import tempfile
from pathlib import Path
from typing import Optional, Dict, Tuple
import streamlit as st

try:
    from moviepy.editor import VideoFileClip
except ImportError:
    VideoFileClip = None

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    from docx import Document
except ImportError:
    Document = None


# ============================================================================
# VIDEO UTILITIES
# ============================================================================

def get_video_metadata(video_file) -> Optional[Dict]:
    """
    Extract metadata from video file (duration, resolution, fps)
    
    Args:
        video_file: Streamlit uploaded file object
        
    Returns:
        Dictionary with video metadata or None if extraction fails
    """
    if VideoFileClip is None:
        st.error("MoviePy is not installed. Cannot extract video metadata.")
        return None
    
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
            tmp_file.write(video_file.getbuffer())
            tmp_path = tmp_file.name
        
        # Extract metadata using moviepy
        clip = VideoFileClip(tmp_path)
        
        metadata = {
            "duration": clip.duration,
            "width": clip.w,
            "height": clip.h,
            "fps": clip.fps,
            "resolution": f"{clip.w}x{clip.h}",
            "aspect_ratio": clip.w / clip.h if clip.h > 0 else None,
            "file_size_mb": video_file.size / (1024 * 1024)
        }
        
        clip.close()
        
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        
        return metadata
    
    except Exception as e:
        st.error(f"Error extracting video metadata: {str(e)}")
        return None


def validate_video_file(video_file) -> Tuple[bool, str]:
    """
    Validate uploaded video file
    
    Args:
        video_file: Streamlit uploaded file object
        
    Returns:
        Tuple of (is_valid, message)
    """
    # Check file size (500MB limit)
    max_size_mb = 500
    file_size_mb = video_file.size / (1024 * 1024)
    
    if file_size_mb > max_size_mb:
        return False, f"File size ({file_size_mb:.2f}MB) exceeds limit ({max_size_mb}MB)"
    
    # Check file extension
    valid_extensions = [".mp4", ".mkv", ".mov"]
    file_ext = Path(video_file.name).suffix.lower()
    
    if file_ext not in valid_extensions:
        return False, f"Invalid file format. Supported: {', '.join(valid_extensions)}"
    
    return True, "Video file is valid"


# ============================================================================
# DOCUMENT UTILITIES
# ============================================================================

def extract_text_from_pdf(pdf_file) -> Optional[str]:
    """
    Extract text from PDF file
    
    Args:
        pdf_file: Streamlit uploaded PDF file
        
    Returns:
        Extracted text or None if extraction fails
    """
    if PyPDF2 is None:
        st.error("PyPDF2 is not installed. Cannot extract text from PDF.")
        return None
    
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        
        for page in pdf_reader.pages:
            text += page.extract_text()
        
        return text.strip() if text else None
    
    except Exception as e:
        st.error(f"Error extracting text from PDF: {str(e)}")
        return None


def extract_text_from_docx(docx_file) -> Optional[str]:
    """
    Extract text from DOCX file
    
    Args:
        docx_file: Streamlit uploaded DOCX file
        
    Returns:
        Extracted text or None if extraction fails
    """
    if Document is None:
        st.error("python-docx is not installed. Cannot extract text from DOCX.")
        return None
    
    try:
        doc = Document(docx_file)
        text = ""
        
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        
        return text.strip() if text else None
    
    except Exception as e:
        st.error(f"Error extracting text from DOCX: {str(e)}")
        return None


def extract_text_from_txt(txt_file) -> Optional[str]:
    """
    Extract text from TXT file
    
    Args:
        txt_file: Streamlit uploaded TXT file
        
    Returns:
        Extracted text or None if extraction fails
    """
    try:
        text = txt_file.read().decode("utf-8")
        return text.strip() if text else None
    
    except Exception as e:
        st.error(f"Error reading TXT file: {str(e)}")
        return None


def extract_text_from_srt(srt_file) -> Optional[str]:
    """
    Extract text from SRT (subtitle) file
    Removes timestamps and returns only the subtitle text
    
    Args:
        srt_file: Streamlit uploaded SRT file
        
    Returns:
        Extracted text (without timestamps) or None if extraction fails
    """
    try:
        content = srt_file.read().decode("utf-8")
        lines = content.split("\n")
        
        text_lines = []
        for line in lines:
            # Skip empty lines and timestamp lines
            line = line.strip()
            if line and not line[0].isdigit() and "-->" not in line:
                text_lines.append(line)
        
        return " ".join(text_lines).strip() if text_lines else None
    
    except Exception as e:
        st.error(f"Error extracting text from SRT: {str(e)}")
        return None


def extract_document_text(document_file) -> Optional[str]:
    """
    Extract text from any supported document format
    
    Args:
        document_file: Streamlit uploaded file
        
    Returns:
        Extracted text or None if extraction fails
    """
    file_ext = Path(document_file.name).suffix.lower()
    
    if file_ext == ".pdf":
        return extract_text_from_pdf(document_file)
    elif file_ext == ".docx":
        return extract_text_from_docx(document_file)
    elif file_ext == ".txt":
        return extract_text_from_txt(document_file)
    elif file_ext == ".srt":
        return extract_text_from_srt(document_file)
    else:
        st.error(f"Unsupported file format: {file_ext}")
        return None


def validate_document_file(document_file) -> Tuple[bool, str]:
    """
    Validate uploaded document file
    
    Args:
        document_file: Streamlit uploaded file
        
    Returns:
        Tuple of (is_valid, message)
    """
    # Check file size (50MB limit)
    max_size_mb = 50
    file_size_mb = document_file.size / (1024 * 1024)
    
    if file_size_mb > max_size_mb:
        return False, f"File size ({file_size_mb:.2f}MB) exceeds limit ({max_size_mb}MB)"
    
    # Check file extension
    valid_extensions = [".pdf", ".docx", ".txt", ".srt"]
    file_ext = Path(document_file.name).suffix.lower()
    
    if file_ext not in valid_extensions:
        return False, f"Invalid file format. Supported: {', '.join(valid_extensions)}"
    
    return True, "Document file is valid"


# ============================================================================
# URL UTILITIES
# ============================================================================

def validate_youtube_url(url: str) -> Tuple[bool, str]:
    """
    Validate YouTube URL format
    
    Args:
        url: URL string to validate
        
    Returns:
        Tuple of (is_valid, message)
    """
    youtube_domains = ["youtube.com", "youtu.be", "youtube.co.kr"]
    
    if any(domain in url for domain in youtube_domains):
        return True, "Valid YouTube URL"
    else:
        return False, "Invalid YouTube URL. Please enter a valid YouTube link."


# ============================================================================
# CLEANUP UTILITIES
# ============================================================================

def cleanup_temp_files(temp_dir: Optional[str] = None):
    """
    Clean up temporary files
    
    Args:
        temp_dir: Temporary directory path to clean up
    """
    if temp_dir and os.path.exists(temp_dir):
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Error cleaning up temporary files: {str(e)}")


# ============================================================================
# FORMATTING UTILITIES
# ============================================================================

def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to HH:MM:SS format
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in bytes to human-readable format
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        Formatted file size string
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    
    return f"{size_bytes:.2f} TB"
