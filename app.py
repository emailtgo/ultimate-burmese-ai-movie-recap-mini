import streamlit as st
import asyncio
import os
import tempfile
from typing import List
from ai_services import AIScriptService, extract_audio_from_video

# Constants for Engine V3
MAX_RPM_PER_KEY = 9

# Page Configuration
st.set_page_config(
    page_title="🎬 Burmese AI Movie Recap Mini",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
        .main { padding-top: 2rem; }
        .stTabs [data-baseweb="tab-list"] button { font-size: 18px; font-weight: bold; }
        .header-title { text-align: center; font-size: 2.5rem; font-weight: bold; color: #FF6B6B; margin-bottom: 1rem; }
        .subheader-text { text-align: center; font-size: 1.2rem; color: #666; margin-bottom: 2rem; }
    </style>
""", unsafe_allow_html=True)

# Function to get API keys from secrets
def get_keys_from_secrets():
    keys = []
    if "GEMINI_API_KEYS" in st.secrets:
        raw_keys = st.secrets["GEMINI_API_KEYS"]
        if isinstance(raw_keys, list):
            keys.extend(raw_keys)
        elif isinstance(raw_keys, str):
            keys.extend([k.strip() for k in raw_keys.split(",") if k.strip()])
    elif "GEMINI_API_KEY" in st.secrets:
        keys.append(st.secrets["GEMINI_API_KEY"])
    return keys

# Initialize Session State
if "input_data" not in st.session_state:
    st.session_state.input_data = {
        "input_type": None,
        "video_file": None,
        "youtube_url": None,
        "script_file": None,
        "transcript": None,
        "generated_script": None
    }

if "api_keys" not in st.session_state:
    st.session_state.api_keys = {"manual_keys": []}

# ============================================================================
# SIDEBAR - SETTINGS
# ============================================================================
with st.sidebar:
    st.header("⚙️ Studio Settings")
    st.subheader("🔑 Gemini API Keys")
    
    secrets_keys = get_keys_from_secrets()
    if secrets_keys:
        st.success(f"✅ {len(secrets_keys)} API Keys loaded from Secrets")
    
    st.info("Add additional Gemini API Keys below (Optional)")
    
    gemini_input = st.text_area(
        "Enter Additional Keys (one per line)",
        height=150,
        help="Get keys from https://aistudio.google.com/app/apikey",
        key="gemini_input_area",
        value="\n".join(st.session_state.api_keys["manual_keys"])
    )
    
    st.session_state.api_keys["manual_keys"] = [k.strip() for k in gemini_input.split("\n") if k.strip()]
    all_gemini_keys = list(set(secrets_keys + st.session_state.api_keys["manual_keys"]))
    
    st.divider()
    st.info(f"**🚀 Engine Active**\n- Max RPM: {MAX_RPM_PER_KEY}")

# ============================================================================
# MAIN CONTENT
# ============================================================================
st.markdown('<div class="header-title">🎬 Burmese AI Movie Recap Mini</div>', unsafe_allow_html=True)
st.markdown('<div class="subheader-text">Powered by Gemini 3.5 Flash</div>', unsafe_allow_html=True)
st.divider()

# STEP 1: INPUT
st.header("📤 Step 1: Content Input")
tab1, tab2, tab3 = st.tabs(["📹 Local Video", "🎥 YouTube", "📄 Script"])

with tab1:
    uploaded_video = st.file_uploader("Choose a video file", type=["mp4", "mkv", "mov"])
    if uploaded_video:
        st.session_state.input_data["input_type"] = "local_video"
        st.session_state.input_data["video_file"] = uploaded_video
        st.video(uploaded_video)

with tab2:
    youtube_url = st.text_input("Enter Video URL", placeholder="https://www.youtube.com/watch?v=...")
    if youtube_url:
        st.session_state.input_data["input_type"] = "youtube_url"
        st.session_state.input_data["youtube_url"] = youtube_url
        st.success("✅ URL detected")

with tab3:
    uploaded_script = st.file_uploader("Choose a script file", type=["txt", "srt", "pdf", "docx"])
    if uploaded_script:
        st.session_state.input_data["input_type"] = "script_document"
        st.session_state.input_data["script_file"] = uploaded_script

# STEP 2: PROCESSING
st.divider()
st.header("📋 Step 2: Process & Generate Script")

input_ready = st.session_state.input_data["input_type"] is not None
keys_ready = len(all_gemini_keys) > 0

col1, col2 = st.columns(2)
with col1:
    st.write("**Input Status:** ✅ Ready" if input_ready else "⚠️ No Input")
with col2:
    st.write(f"**Gemini Keys:** ✅ {len(all_gemini_keys)} Ready" if keys_ready else "❌ No Keys Found")

if input_ready and keys_ready:
    if st.button("🚀 Start Script Generation", use_container_width=True, type="primary"):
        try:
            ai_service = AIScriptService(api_keys=all_gemini_keys, max_rpm=MAX_RPM_PER_KEY)
            
            with st.status("🎬 Processing...", expanded=True) as status:
                # 1. Handle Video to Audio if needed
                audio_path = None
                if st.session_state.input_data["input_type"] == "local_video":
                    status.update(label="🎙️ Extracting audio from video...")
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_video:
                        tmp_video.write(st.session_state.input_data["video_file"].getbuffer())
                        tmp_video_path = tmp_video.name
                    audio_path = extract_audio_from_video(tmp_video_path)
                
                # 2. Transcribe
                if audio_path:
                    status.update(label="📝 Transcribing with Gemini 3.5 Flash...")
                    transcript = asyncio.run(ai_service.transcribe_audio_gemini(audio_path))
                    st.session_state.input_data["transcript"] = transcript
                
                # 3. Generate Script or Translate SRT
                if st.session_state.input_data["input_type"] == "script_document" and \
                   st.session_state.input_data["script_file"].name.lower().endswith(".srt"):
                    
                    status.update(label="🌐 Translating SRT to Burmese...")
                    from engine.pro_dubbing_engine import ProDubbingEngine
                    dub_engine = ProDubbingEngine(api_keys=all_gemini_keys, max_rpm=MAX_RPM_PER_KEY)
                    
                    # Read SRT content
                    srt_content = st.session_state.input_data["script_file"].getvalue().decode("utf-8")
                    
                    # Translate using original engine logic with parallel workers
                    # We can specify num_workers here, e.g., 5 or based on number of keys
                    num_workers = min(10, len(all_gemini_keys) * 2) if len(all_gemini_keys) > 0 else 5
                    translation_res = asyncio.run(dub_engine.translate_script(srt_content, num_workers=num_workers))
                    st.session_state.input_data["generated_script"] = translation_res["reconstructed_srt_content"]
                else:
                    status.update(label="✍️ Writing Movie Recap Script...")
                    source_text = st.session_state.input_data["transcript"] or "Manual input placeholder"
                    script = asyncio.run(ai_service.generate_movie_recap_script(source_text))
                    st.session_state.input_data["generated_script"] = script
                
                status.update(label="✅ Script Generation Completed!", state="complete", expanded=False)
            
            st.balloons()
            
        except Exception as e:
            st.error(f"❌ An error occurred: {str(e)}")

# STEP 3: RESULTS
if st.session_state.input_data["generated_script"]:
    st.divider()
    st.header("🎁 Step 3: Final Script")
    st.text_area("Burmese Recap Script", value=st.session_state.input_data["generated_script"], height=400)
    st.download_button("📥 Download Script", st.session_state.input_data["generated_script"], "recap_script.txt")

st.divider()
st.markdown("🎬 **Burmese AI Movie Recap Mini** | Powered by Gemini 3.5 Flash")
