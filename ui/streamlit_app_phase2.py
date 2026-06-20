"""
Phase 2: AI Script Generation & Editing
This module handles script generation from transcripts and provides editing capabilities
"""

import streamlit as st
from utils import extract_document_text, validate_document_file, format_duration
from ai_services import (
    transcribe_audio_whisper,
    extract_audio_from_video,
    generate_movie_recap_script,
    refine_script_with_gemini,
    translate_script,
    validate_api_keys
)
import tempfile
from pathlib import Path


def render_phase2_ui():
    """
    Render Phase 2: AI Script Generation & Editing UI
    """
    st.header("📝 Step 2: Generate AI Script")
    
    st.markdown("""
    This step will generate a professional Burmese movie recap script from your input.
    You can then edit and refine the script before proceeding to voiceover generation.
    """)
    
    # Check if input data is available
    if not st.session_state.input_data.get("input_type"):
        st.warning("⚠️ Please complete Step 1 (Upload Content) first.")
        return
    
    # Get API keys
    gemini_key = st.session_state.api_keys.get("gemini_key")
    openai_key = st.session_state.api_keys.get("openai_key")
    
    # Validate API keys
    key_validation = validate_api_keys(gemini_key, openai_key)
    
    if not key_validation["gemini_valid"]:
        st.error("❌ Gemini API key is required for script generation. Please configure it in Settings.")
        return
    
    # ========================================================================
    # STEP 2.1: EXTRACT TRANSCRIPT/TEXT
    # ========================================================================
    st.subheader("Step 2.1: Extract Content")
    
    input_type = st.session_state.input_data.get("input_type")
    transcript_text = None
    
    if input_type == "local_video":
        st.info("📹 Processing local video file...")
        video_file = st.session_state.input_data.get("video_file")
        
        if video_file:
            col1, col2 = st.columns(2)
            
            with col1:
                extraction_method = st.radio(
                    "Choose extraction method:",
                    ["Extract Audio & Transcribe", "Manual Text Input"],
                    key="video_extraction_method"
                )
            
            with col2:
                if extraction_method == "Extract Audio & Transcribe":
                    if st.button("🎙️ Extract Audio & Transcribe", use_container_width=True):
                        with st.spinner("Extracting audio from video..."):
                            # Save video to temporary file
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_video:
                                tmp_video.write(video_file.getbuffer())
                                tmp_video_path = tmp_video.name
                            
                            # Extract audio
                            audio_path = extract_audio_from_video(tmp_video_path)
                            
                            if audio_path:
                                st.success("✅ Audio extracted successfully!")
                                
                                # Transcribe audio
                                with st.spinner("Transcribing audio with Whisper AI..."):
                                    transcript_text = transcribe_audio_whisper(audio_path, openai_key)
                                    
                                    if transcript_text:
                                        st.session_state.input_data["transcript"] = transcript_text
                                        st.success("✅ Transcription completed!")
                                    else:
                                        st.error("❌ Transcription failed. Please try again.")
                else:
                    st.info("You can manually enter the video content below.")
    
    elif input_type == "youtube_url":
        st.info("🎥 YouTube video processing...")
        st.info("Note: YouTube transcript extraction will be implemented in the next update.")
        st.text_area(
            "Or paste the transcript/content here:",
            height=200,
            key="youtube_manual_input",
            placeholder="Paste the video transcript or summary here..."
        )
    
    elif input_type == "script_document":
        st.info("📄 Processing document...")
        script_file = st.session_state.input_data.get("script_file")
        
        if script_file:
            # Validate document
            is_valid, message = validate_document_file(script_file)
            
            if is_valid:
                # Extract text
                extracted_text = extract_document_text(script_file)
                
                if extracted_text:
                    st.session_state.input_data["script_text"] = extracted_text
                    st.success(f"✅ Document processed! Extracted {len(extracted_text)} characters.")
                    transcript_text = extracted_text
                else:
                    st.error("❌ Failed to extract text from document.")
            else:
                st.error(f"❌ {message}")
    
    # Get transcript from session state if available
    if not transcript_text:
        transcript_text = st.session_state.input_data.get("transcript") or \
                         st.session_state.input_data.get("script_text")
    
    # ========================================================================
    # STEP 2.2: GENERATE SCRIPT
    # ========================================================================
    st.divider()
    st.subheader("Step 2.2: Generate Script with AI")
    
    if transcript_text:
        st.markdown(f"**Content Length:** {len(transcript_text)} characters")
        
        # Display extracted content
        with st.expander("📋 View Extracted Content", expanded=False):
            st.text_area(
                "Extracted Content:",
                value=transcript_text,
                height=200,
                disabled=True
            )
        
        # Custom prompt for script generation
        st.markdown("**Optional: Customize Script Generation**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            custom_tone = st.selectbox(
                "Script Tone:",
                ["Professional", "Entertaining", "Dramatic", "Humorous", "Educational"],
                key="script_tone"
            )
        
        with col2:
            script_length = st.selectbox(
                "Script Length:",
                ["Short (2-3 min)", "Medium (5-7 min)", "Long (10+ min)"],
                key="script_length"
            )
        
        custom_prompt = st.text_area(
            "Additional Instructions (Optional):",
            placeholder="E.g., 'Focus on action scenes' or 'Emphasize character development'",
            height=100,
            key="custom_script_prompt"
        )
        
        # Generate script button
        if st.button("✨ Generate Script with Gemini AI", use_container_width=True, type="primary"):
            with st.spinner("Generating script with Gemini AI..."):
                # Get video duration if available
                video_duration = None
                if st.session_state.input_data.get("video_metadata"):
                    video_duration = st.session_state.input_data["video_metadata"].get("duration")
                
                # Generate script
                generated_script = generate_movie_recap_script(
                    transcript_or_text=transcript_text,
                    video_duration=video_duration,
                    custom_prompt=custom_prompt if custom_prompt else None,
                    api_key=gemini_key
                )
                
                if generated_script:
                    st.session_state.input_data["generated_script"] = generated_script
                    st.success("✅ Script generated successfully!")
                    
                    # Display generated script
                    st.markdown("### 📝 Generated Script")
                    st.text_area(
                        "Generated Script:",
                        value=generated_script,
                        height=300,
                        key="generated_script_display"
                    )
    else:
        st.warning("⚠️ No content available. Please extract content first.")
    
    # ========================================================================
    # STEP 2.3: SCRIPT EDITING
    # ========================================================================
    st.divider()
    st.subheader("Step 2.3: Edit & Refine Script")
    
    generated_script = st.session_state.input_data.get("generated_script")
    
    if generated_script:
        # Create tabs for different editing options
        edit_tab1, edit_tab2, edit_tab3 = st.tabs([
            "✏️ Manual Edit",
            "🤖 AI Refinement",
            "🌐 Translate"
        ])
        
        # Tab 1: Manual Edit
        with edit_tab1:
            st.markdown("Edit the script directly below:")
            
            edited_script = st.text_area(
                "Edit Script:",
                value=generated_script,
                height=300,
                key="manual_script_edit"
            )
            
            if st.button("💾 Save Edited Script", use_container_width=True):
                st.session_state.input_data["generated_script"] = edited_script
                st.success("✅ Script updated!")
        
        # Tab 2: AI Refinement
        with edit_tab2:
            st.markdown("Use AI to refine your script:")
            
            refinement_instruction = st.text_area(
                "What would you like to change?",
                placeholder="E.g., 'Make it more humorous' or 'Add more emotional depth'",
                height=150,
                key="refinement_instruction"
            )
            
            if refinement_instruction:
                if st.button("🔄 Refine Script with AI", use_container_width=True):
                    with st.spinner("Refining script with Gemini AI..."):
                        refined_script = refine_script_with_gemini(
                            original_script=generated_script,
                            refinement_instruction=refinement_instruction,
                            api_key=gemini_key
                        )
                        
                        if refined_script:
                            st.session_state.input_data["generated_script"] = refined_script
                            st.success("✅ Script refined!")
                            
                            # Display refined script
                            st.text_area(
                                "Refined Script:",
                                value=refined_script,
                                height=300,
                                disabled=True
                            )
        
        # Tab 3: Translate
        with edit_tab3:
            st.markdown("Translate script to another language:")
            
            target_language = st.selectbox(
                "Target Language:",
                {
                    "English": "en",
                    "Thai": "th",
                    "Japanese": "ja",
                    "Korean": "ko",
                    "Vietnamese": "vi",
                    "Chinese": "zh"
                },
                key="target_language"
            )
            
            if st.button("🌐 Translate Script", use_container_width=True):
                with st.spinner(f"Translating script to {target_language}..."):
                    translated_script = translate_script(
                        script=generated_script,
                        target_language=target_language,
                        api_key=gemini_key
                    )
                    
                    if translated_script:
                        st.success("✅ Script translated!")
                        
                        # Display translated script
                        st.text_area(
                            f"Translated Script ({target_language.upper()}):",
                            value=translated_script,
                            height=300,
                            disabled=True
                        )
                        
                        # Option to save translated script
                        if st.button("💾 Save Translated Script", use_container_width=True):
                            st.session_state.input_data["generated_script"] = translated_script
                            st.success("✅ Translated script saved!")
    else:
        st.info("ℹ️ Generate a script first to enable editing features.")
    
    # ========================================================================
    # DOWNLOAD SCRIPT
    # ========================================================================
    st.divider()
    
    final_script = st.session_state.input_data.get("generated_script")
    
    if final_script:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Download as TXT
            st.download_button(
                label="📥 Download as TXT",
                data=final_script,
                file_name="movie_recap_script.txt",
                mime="text/plain",
                use_container_width=True
            )
        
        with col2:
            # Download as SRT (placeholder)
            st.info("SRT format coming soon")
        
        with col3:
            # Proceed to next step
            if st.button("➡️ Proceed to Voiceover", use_container_width=True, type="primary"):
                st.success("✅ Ready for Phase 3: Audio & Voiceover Production!")
                st.info("(Next phase will be implemented soon)")


# Main execution
if __name__ == "__main__":
    # This is for testing purposes
    st.set_page_config(page_title="Phase 2 - Script Generation", layout="wide")
    
    # Initialize session state
    if "input_data" not in st.session_state:
        st.session_state.input_data = {}
    if "api_keys" not in st.session_state:
        st.session_state.api_keys = {}
    
    render_phase2_ui()
