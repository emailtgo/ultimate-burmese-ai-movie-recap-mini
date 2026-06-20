import streamlit as st
from ui.phase1 import render_phase1
from ui.phase2 import render_phase2
from core.ai_services import GeminiService

st.set_page_config(page_title="Burmese Movie Recap Mini", layout="wide")

def main():
    st.title("🎬 Burmese AI Movie Recap Mini (Phase 1 & 2)")
    
    # Sidebar for Configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        api_key = st.text_input("Gemini API Key:", type="password")
        if api_key:
            st.session_state.api_key = api_key
            gemini = GeminiService(api_key)
            if st.button("Validate Key"):
                if gemini.validate_key():
                    st.success("API Key is Valid!")
                else:
                    st.error("Invalid API Key.")
        else:
            st.warning("Please enter Gemini API Key to proceed.")

    if "api_key" not in st.session_state or not st.session_state.api_key:
        st.info("👈 Please enter your Gemini API Key in the sidebar to start.")
        return

    # Phase Navigation
    if "current_phase" not in st.session_state:
        st.session_state.current_phase = 1

    # Render Phases
    if st.session_state.current_phase == 1:
        render_phase1()
    elif st.session_state.current_phase == 2:
        render_phase2()

if __name__ == "__main__":
    main()
