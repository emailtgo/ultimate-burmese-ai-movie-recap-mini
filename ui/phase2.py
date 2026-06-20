import streamlit as st
import asyncio
from core.ai_services import GeminiService
from utils.file_utils import extract_audio

def render_phase2():
    st.header("📍 Phase 2: AI Script Generation")
    
    if "input_data" not in st.session_state:
        st.warning("Please complete Phase 1 first.")
        if st.button("⬅️ Back to Phase 1"):
            st.session_state.current_phase = 1
            st.rerun()
        return

    gemini = GeminiService(st.session_state.api_key)
    input_data = st.session_state.input_data

    st.subheader("Step 1: Content Extraction")
    
    if "transcript" not in st.session_state:
        if st.button("Extract Content / Transcribe"):
            with st.spinner("Processing..."):
                if input_data["type"] == "video":
                    audio_path = extract_audio(input_data["path"])
                    if audio_path:
                        transcript = asyncio.run(gemini.transcribe_audio(audio_path))
                        st.session_state.transcript = transcript
                    else:
                        st.error("Could not extract audio from video.")
                elif input_data["type"] == "youtube":
                    # For simplicity in this version, we use the description if no transcript
                    st.session_state.transcript = input_data["description"]
                elif input_data["type"] == "text":
                    st.session_state.transcript = input_data["content"]
            st.rerun()

    if "transcript" in st.session_state:
        st.text_area("Extracted Content:", st.session_state.transcript, height=150)
        
        st.subheader("Step 2: Script Generation")
        if st.button("Generate Burmese Recap Script ✨"):
            with st.spinner("Generating script with Gemini..."):
                script = asyncio.run(gemini.generate_script(st.session_state.transcript, input_data.get("duration")))
                st.session_state.generated_script = script
            st.rerun()

    if "generated_script" in st.session_state:
        st.subheader("Step 3: Edit & Refine")
        edited_script = st.text_area("Final Script (Burmese):", st.session_state.generated_script, height=300)
        st.session_state.generated_script = edited_script
        
        col1, col2 = st.columns(2)
        with col1:
            refine_inst = st.text_input("Refinement Instruction (e.g., 'Make it funnier'):")
            if st.button("Refine AI Script"):
                with st.spinner("Refining..."):
                    new_script = asyncio.run(gemini.refine_script(st.session_state.generated_script, refine_inst))
                    st.session_state.generated_script = new_script
                st.rerun()
        
        with col2:
            st.download_button("Download Script (.txt)", st.session_state.generated_script, file_name="recap_script.txt")

    if st.button("⬅️ Start Over"):
        for key in ["input_data", "transcript", "generated_script"]:
            if key in st.session_state: del st.session_state[key]
        st.session_state.current_phase = 1
        st.rerun()
