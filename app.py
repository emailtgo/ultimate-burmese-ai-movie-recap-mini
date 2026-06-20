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
        
        # Try to get API keys from st.secrets first
        api_keys = []
        secrets_keys = st.secrets.get("GEMINI_API_KEYS")
        if secrets_keys:
            if isinstance(secrets_keys, list):
                api_keys = secrets_keys
            else:
                api_keys = [k.strip() for k in str(secrets_keys).split(",") if k.strip()]
            st.success(f"✅ {len(api_keys)} Keys loaded from Secrets")
        else:
            keys_input = st.text_area("Gemini API Keys (one per line or comma-separated):", 
                                    help="Enter multiple keys to enable auto-rotation and bypass RPM limits.")
            if keys_input:
                api_keys = [k.strip() for k in keys_input.replace("\n", ",").split(",") if k.strip()]
        
        if api_keys:
            st.session_state.api_keys = api_keys
            gemini = GeminiService(api_keys)
            if st.button("Validate & Rotate Keys"):
                with st.spinner("Validating keys..."):
                    import asyncio
                    res = asyncio.run(gemini.validate_keys())
                    if res["success"]:
                        st.success(f"Validated {res['count']} / {len(api_keys)} Keys!")
                    else:
                        st.error("No valid API keys found.")
        else:
            st.warning("Please enter Gemini API Key(s) to proceed.")

    if "api_keys" not in st.session_state or not st.session_state.api_keys:
        st.info("👈 Please enter your Gemini API Key(s) in the sidebar to start.")
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
