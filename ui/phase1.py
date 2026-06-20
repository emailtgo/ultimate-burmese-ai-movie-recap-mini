import streamlit as st
import os
import tempfile
from utils.file_utils import get_video_metadata, download_youtube_info

def render_phase1():
    st.header("📍 Phase 1: Input Handling")
    
    input_type = st.radio("Select Input Source:", ["Local Video", "YouTube URL", "Document/Text"])
    
    if input_type == "Local Video":
        uploaded_file = st.file_uploader("Upload Video (MP4, MKV)", type=["mp4", "mkv", "mov"])
        if uploaded_file:
            temp_path = os.path.join(tempfile.gettempdir(), uploaded_file.name)
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            meta = get_video_metadata(temp_path)
            st.success(f"Video Loaded: {meta['duration']:.2f}s | {meta['resolution']} | {meta['size']:.2f}MB")
            
            st.session_state.input_data = {
                "type": "video",
                "path": temp_path,
                "duration": meta['duration']
            }

    elif input_type == "YouTube URL":
        url = st.text_input("Enter YouTube URL:")
        if url:
            with st.spinner("Fetching video info..."):
                info = download_youtube_info(url)
                if info:
                    st.success(f"Found: {info['title']} ({info['duration']}s)")
                    st.session_state.input_data = {
                        "type": "youtube",
                        "url": url,
                        "title": info['title'],
                        "duration": info['duration'],
                        "description": info['description']
                    }
                else:
                    st.error("Could not fetch YouTube info.")

    elif input_type == "Document/Text":
        text_input = st.text_area("Paste Transcript or Story here:")
        if text_input:
            st.session_state.input_data = {
                "type": "text",
                "content": text_input,
                "duration": None
            }

    if "input_data" in st.session_state:
        if st.button("Proceed to Phase 2 ➡️"):
            st.session_state.current_phase = 2
            st.rerun()
