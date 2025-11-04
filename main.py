import streamlit as st
import requests
import PyPDF2
from docx import Document
import io
import os
import json
import time
from dotenv import load_dotenv
from document_processor import DocumentProcessor
import sounddevice as sd
import numpy as np
import soundfile as sf

import threading
import queue
import tempfile
from faster_whisper import WhisperModel

# ==========================
# PAGE CONFIGURATION
# ==========================
st.set_page_config(
    page_title="LectureBuddies - Educational Platform",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================
# SESSION STATE INITIALIZATION
# ==========================
def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        # Login/Auth
        "authenticated": False,
        "current_user": None,
        "current_page": "dashboard",

        # Chatbot & Summarization
        "messages": [],
        "uploaded_files": [],
        "document_contents": {},
        "chat_model": "llama-3.1-8b-instant",
        "chat_temperature": 0.7,

        # Quiz Generator
        "quiz_output": None,
        "num_questions": 5,
        "difficulty": "Medium",
        "quiz_model": "llama-3.1-8b-instant",
        "quiz_temperature": 0.7,

        # Live Lecture Recording
        "rec_thread": None,
        "audio_queue": None,
        "recording": False,
        "transcript": "",
        "partial_transcript": "",
        "chunks_saved": [],

        # Dashboard
        "selected_feature": None
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()

# ==========================
# LOAD API KEY
# ==========================
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

# ==========================
# GLOBAL STYLING - LECTUREBUDDIES THEME
# ==========================
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');

    /* Prevent scrolling on login page only */
    .login-page body, .login-page html {
        overflow-y: hidden !important;
        height: 100vh !important;
    }

    /* Main App Styling */
    .stApp {
        font-family: 'Poppins', sans-serif;
        background-color: #f5f7fa;
    }

    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Main Title */
    .main-title {
        text-align: center;
        font-size: 42px;
        font-weight: 800;
        background: linear-gradient(90deg, #4e54c8, #8f94fb, #4e54c8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 8px;
        font-family: 'Poppins', sans-serif;
    }

    /* Tagline */
    .tagline {
        text-align: center;
        font-size: 16px;
        color: #666;
        margin-bottom: 15px;
        font-family: 'Poppins', sans-serif;
    }

    /* Gradient Line */
    hr.gradient {
        border: none;
        height: 3px;
        background: linear-gradient(90deg, #4e54c8, #8f94fb, #4e54c8);
        border-radius: 50px;
        margin: 15px auto;
        max-width: 400px;
    }

    /* ==============================================
       TOP NAVBAR - Modern WordPress Style
       ============================================== */
    .top-navbar {
        background: white;
        padding: 12px 30px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        border-bottom: 1px solid #e0e7ff;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: -20px -30px 20px -30px;
        position: sticky;
        top: 0;
        z-index: 100;
    }

    .brand-section {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .brand-logo {
        font-size: 24px;
        font-weight: 800;
        background: linear-gradient(135deg, #4e54c8, #8f94fb);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .brand-name {
        font-size: 18px;
        font-weight: 700;
        color: #2c3e50;
        font-family: 'Poppins', sans-serif;
    }

    .nav-right {
        display: flex;
        align-items: center;
        gap: 15px;
    }

    .user-info {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 6px 15px;
        border-radius: 25px;
        background: linear-gradient(135deg, #f8f9ff, #e8ecff);
        border: 1px solid #e0e7ff;
    }

    .user-avatar {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background: linear-gradient(135deg, #4e54c8, #8f94fb);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 700;
        font-size: 14px;
    }

    .user-name {
        font-weight: 600;
        color: #4e54c8;
        font-size: 14px;
    }

    .nav-icon-btn {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background: #f5f7fa;
        border: 1px solid #e0e7ff;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.3s ease;
        color: #4e54c8;
        font-size: 18px;
    }

    .nav-icon-btn:hover {
        background: linear-gradient(135deg, #4e54c8, #8f94fb);
        color: white;
        transform: translateY(-2px);
    }

    /* ==============================================
       SIDEBAR - Modern WordPress Style
       ============================================== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #f8f9ff 100%);
        border-right: 1px solid #e0e7ff;
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: 20px;
    }

    .sidebar-section {
        padding: 10px 0;
    }

    .sidebar-title {
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #9ca3af;
        padding: 0 20px;
        margin-bottom: 12px;
    }

    /* Sidebar Button Styling */
    [data-testid="stSidebar"] button {
        width: 100% !important;
        text-align: left !important;
        padding: 8px 15px !important;
        margin: 1px 0 !important;
        border-radius: 8px !important;
        background: transparent !important;
        border: none !important;
        color: #4b5563 !important;
        font-weight: 500 !important;
        font-size: 12px !important;
        transition: all 0.3s ease !important;
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
        white-space: nowrap !important;
        min-height: 32px !important;
    }

    [data-testid="stSidebar"] button:hover {
        background: linear-gradient(135deg, #4e54c8, #8f94fb) !important;
        color: white !important;
        transform: translateX(5px);
    }

    /* ==============================================
       LOGIN/SIGNUP PAGES - WordPress Style
       ============================================== */
    .login-container {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 80vh;
        padding: 40px 20px;
    }

    .login-box-wrapper {
        background: white;
        padding: 45px 40px;
        border-radius: 16px;
        box-shadow: 0 10px 50px rgba(78, 84, 200, 0.12);
        max-width: 420px;
        width: 100%;
    }

    .login-header {
        text-align: center;
        margin-bottom: 30px;
    }

    .login-title {
        font-size: 32px;
        font-weight: 700;
        color: #4e54c8;
        margin-bottom: 8px;
        font-family: 'Poppins', sans-serif;
    }

    .login-subtitle {
        font-size: 15px;
        color: #667eea;
        font-weight: 400;
        font-family: 'Poppins', sans-serif;
    }

    /* Input Field Styling */
    .login-input-wrapper {
        margin-bottom: 20px;
    }

    .login-label {
        display: block;
        font-size: 14px;
        font-weight: 600;
        color: #374151;
        margin-bottom: 8px;
        font-family: 'Poppins', sans-serif;
    }

    /* Override Streamlit input styling */
    .stTextInput > div > div > input,
    .stTextInput > div > input {
        border: 2px solid #e5e7eb !important;
        border-radius: 10px !important;
        padding: 12px 16px !important;
        font-size: 15px !important;
        font-family: 'Poppins', sans-serif !important;
        transition: all 0.3s ease !important;
        height: auto !important;
        width: 100% !important;
        background: #f9fafb !important;
    }

    .stTextInput > div > div > input:focus,
    .stTextInput > div > input:focus {
        border-color: #667eea !important;
        outline: none !important;
        box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1) !important;
        background: white !important;
    }

    /* Modern Button Styling */
    .stButton > button {
        width: 100% !important;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        font-weight: 600 !important;
        font-size: 15px !important;
        padding: 9px 12px !important;
        border: none !important;
        border-radius: 10px !important;
        cursor: pointer !important;
        transition: all 0.3s ease !important;
        font-family: 'Poppins', sans-serif !important;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3) !important;
        margin-top: 10px !important;
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4) !important;
    }

    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 5px;
        background-color: #f3f4f6;
        border-radius: 12px;
        padding: 6px;
        margin-bottom: 30px;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        font-family: 'Poppins', sans-serif;
        font-weight: 600;
        font-size: 14px;
        padding: 10px 20px;
        transition: all 0.3s ease;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
    }

    /* Links Styling */
    .login-links {
        text-align: center;
        margin-top: 25px;
        padding-top: 25px;
        border-top: 1px solid #e5e7eb;
        font-family: 'Poppins', sans-serif;
    }

    .login-link {
        color: #667eea;
        text-decoration: none;
        font-size: 14px;
        font-weight: 500;
        transition: color 0.3s ease;
    }

    .login-link:hover {
        color: #764ba2;
        text-decoration: underline;
    }

    /* ==============================================
       DASHBOARD CONTENT STYLING
       ============================================== */
    .dashboard-header {
        background: linear-gradient(135deg, #f8f9ff, #e8ecff);
        padding: 30px;
        border-radius: 16px;
        border: 1px solid #d1d9ff;
        margin-bottom: 30px;
        box-shadow: 0 4px 15px rgba(78, 84, 200, 0.08);
    }

    .welcome-text {
        color: #4e54c8;
        font-size: 28px;
        font-weight: 700;
        margin-bottom: 12px;
        font-family: 'Poppins', sans-serif;
    }

    .welcome-subtitle {
        color: #666;
        font-size: 16px;
        font-family: 'Poppins', sans-serif;
    }

    .feature-card {
        background: white;
        padding: 24px;
        border-radius: 16px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 2px 10px rgba(0,0,0,0.04);
        margin: 8px 0;
        transition: all 0.3s ease;
        height: 100%;
    }

    .feature-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 25px rgba(78, 84, 200, 0.12);
        border-color: #d1d9ff;
    }

    .feature-title {
        color: #4e54c8;
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 8px;
        font-family: 'Poppins', sans-serif;
    }

    .feature-description {
        color: #6b7280;
        font-size: 13px;
        font-family: 'Poppins', sans-serif;
        margin-bottom: 12px;
    }

    /* Chat Styling */
    .user-message {
        text-align: right;
        margin: 10px 0;
    }

    .user-bubble {
        display: inline-block;
        background: linear-gradient(135deg, #4e54c8, #8f94fb);
        color: white;
        padding: 12px 18px;
        border-radius: 18px 18px 4px 18px;
        max-width: 70%;
        font-family: 'Poppins', sans-serif;
        font-size: 14px;
        box-shadow: 0 4px 12px rgba(78, 84, 200, 0.2);
    }

    .assistant-message {
        margin: 10px 0;
        color: #202123;
    }

    .assistant-bubble {
        background: white;
        padding: 12px 18px;
        border-radius: 18px 18px 18px 4px;
        max-width: 70%;
        border: 1px solid #e5e7eb;
        font-family: 'Poppins', sans-serif;
        font-size: 14px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }

    /* Quiz Styling */
    .quiz-container {
        background: linear-gradient(135deg, #f8f9ff, #e8ecff);
        padding: 20px;
        border-radius: 16px;
        border: 1px solid #d1d9ff;
        margin-top: 10px;
        box-shadow: 0 4px 15px rgba(78, 84, 200, 0.1);
        max-height: 60vh;
        overflow-y: auto;
    }

    /* Coming Soon Styling */
    .coming-soon {
        text-align: center;
        padding: 80px 40px;
        background: linear-gradient(135deg, #f8f9ff, #e8ecff);
        border-radius: 20px;
        border: 2px dashed #d1d9ff;
    }

    .coming-soon-icon {
        font-size: 72px;
        margin-bottom: 24px;
    }

    .coming-soon-title {
        color: #4e54c8;
        font-size: 28px;
        font-weight: 700;
        margin-bottom: 12px;
        font-family: 'Poppins', sans-serif;
    }

    .coming-soon-text {
        color: #6b7280;
        font-size: 16px;
        font-family: 'Poppins', sans-serif;
    }

    /* Demo Button Styling */
    .demo-button {
        margin-top: 15px;
    }

    /* Input Labels Styling */
    label {
        font-weight: 600 !important;
        font-size: 14px !important;
        color: #374151 !important;
        font-family: 'Poppins', sans-serif !important;
        margin-bottom: 8px !important;
    }

    /* Streamlit Default Element Hides */
    .stDeployButton {
        display: none;
    }

    /* Block Container Styling */
    .block-container {
        padding-top: 30px !important;
    }

    /* Main Content Padding */
    .main .block-container {
        padding: 2rem 3rem;
    }

    /* Ensure Sidebar Styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #f8f9ff 100%) !important;
        border-right: 1px solid #e0e7ff !important;
        transition: width 0.3s ease-in-out, transform 0.3s ease-in-out !important;
    }

    /* Hide the sidebar toggle button */
    button[data-testid="baseButton-header"] {
        display: none !important;
    }
    
    /* Hide the sidebar collapse button */
    [data-testid="stSidebarCollapseButton"] {
        display: none !important;
    }
    
    /* Hide hr elements in sidebar */
    [data-testid="stSidebar"] hr {
        display: none !important;
    }
    
    /* Make sidebar more compact */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #f8f9ff 100%) !important;
        border-right: 1px solid #e0e7ff !important;
        transition: width 0.3s ease-in-out, transform 0.3s ease-in-out !important;
        overflow-y: auto !important;
        max-height: 100vh !important;
    }
    
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 10px !important;
        padding-bottom: 10px !important;
    }
    
    /* Compact sidebar title */
    .sidebar-title {
        font-size: 10px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        color: #9ca3af !important;
        padding: 0 15px !important;
        margin-bottom: 6px !important;
    }
    
    /* Compact sidebar section */
    .sidebar-section {
        padding: 3px 0 !important;
    }

    /* Floating Toggle Button when Sidebar is Collapsed */
    .sidebar-collapsed-toggle {
        position: fixed;
        left: 0;
        top: 50%;
        transform: translateY(-50%);
        width: 40px;
        height: 40px;
        background: linear-gradient(135deg, #4e54c8, #8f94fb);
        border-radius: 0 20px 20px 0;
        border: none;
        border-right: 2px solid white;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
        cursor: pointer;
        z-index: 999;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.3s ease;
    }

    .sidebar-collapsed-toggle:hover {
        width: 45px;
        box-shadow: 4px 4px 15px rgba(78, 84, 200, 0.3);
    }

    .sidebar-collapsed-toggle::after {
        content: '→';
        color: white;
        font-size: 18px;
        font-weight: bold;
    }

    /* User Info Hover & Click Effects */
    .user-info {
        cursor: pointer !important;
        transition: all 0.3s ease !important;
    }

    .user-info:hover {
        background: linear-gradient(135deg, #e8ecff, #d6d9ff) !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(78, 84, 200, 0.15) !important;
    }

    /* Profile Dropdown (hidden by default) */
    .profile-dropdown {
        position: absolute;
        top: 50px;
        right: 20px;
        background: white;
        border-radius: 12px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        min-width: 200px;
        z-index: 1000;
        display: none;
        overflow: hidden;
    }

    .profile-dropdown.show {
        display: block !important;
    }

    .dropdown-item {
        padding: 12px 20px;
        color: #4b5563;
        font-size: 14px;
        font-family: 'Poppins', sans-serif;
        cursor: pointer;
        transition: all 0.3s ease;
    }

    .dropdown-item:hover {
        background: #f8f9ff;
        color: #4e54c8;
    }

    .dropdown-item:first-child {
        padding-top: 16px;
    }

    .dropdown-item:last-child {
        padding-bottom: 16px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ==========================
# LOGIN AND SIGNUP SECTION
# ==========================
def show_login_page():
    """Display login/signup page with WordPress-style centered form"""
    # Center column approach for login form
    col1, col2, col3 = st.columns([1, 1.5, 1])
    
    with col2:
        # Main title outside the centered box
        st.markdown("""
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="font-size: 42px; font-weight: 800; background: linear-gradient(90deg, #4e54c8, #8f94fb, #4e54c8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-family: 'Poppins', sans-serif; margin-bottom: 8px;">
                    🎓 LectureBuddies
                </h1>
                <p style="color: #666; font-size: 16px; font-family: 'Poppins', sans-serif;">
                    Your intelligent study companion—learn, create, and excel with AI
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown(
            """
            <div class="login-header">
                <h2 class="login-title">Welcome Back!</h2>
                <p class="login-subtitle">Sign in to continue to LectureBuddies</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Login/Signup Tabs
        tab1, tab2 = st.tabs(["Login", "Sign Up"])

        with tab1:
            username = st.text_input("Username", placeholder="Enter your username", key="login_username")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")

            if st.button("Login", key="login_btn", help="Login to your account"):
                if username and password:
                    # Simple authentication (no database)
                    if username == "student" and password == "lecturebuddies":
                        st.session_state.authenticated = True
                        st.session_state.current_user = username
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Try: username='student', password='lecturebuddies'")
                else:
                    st.warning("Please enter both username and password")
            
            st.markdown("---")
            if st.button("🔑 Try Demo Mode", key="demo_login", help="Quick demo access", use_container_width=True):
                st.session_state.authenticated = True
                st.session_state.current_user = "demo_user"
                st.success("Demo login successful!")
                st.rerun()

        with tab2:
            new_username = st.text_input("Choose Username", placeholder="Enter your username", key="signup_username")
            new_password = st.text_input("Choose Password", type="password", placeholder="Enter your password", key="signup_password")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password", key="confirm_password")

            if st.button("Create Account", key="signup_btn", help="Create new account"):
                if new_username and new_password and confirm_password:
                    if new_password == confirm_password:
                        st.session_state.authenticated = True
                        st.session_state.current_user = new_username
                        st.success("Account created successfully!")
                        st.rerun()
                    else:
                        st.error("Passwords don't match")
                else:
                    st.warning("Please fill in all fields")

# ==========================
# DASHBOARD LAYOUT SECTION
# ==========================
def show_dashboard():
    """Display main dashboard with sidebar and content area"""
    
    # Initialize profile dropdown state
    if "show_profile_dropdown" not in st.session_state:
        st.session_state.show_profile_dropdown = False

    # Add JavaScript to detect sidebar state and show/hide floating toggle button
    st.markdown(
        """
        <script>
        // Function to check sidebar state and toggle floating button
        function checkSidebarState() {
            const sidebar = document.querySelector('[data-testid="stSidebar"]');
            let floatingToggle = document.getElementById('floating-sidebar-toggle');
            
            if (sidebar) {
                const isCollapsed = sidebar.classList.contains('css-17eq0hr') || 
                                  sidebar.style.transform === 'translateX(-100%)' ||
                                  window.getComputedStyle(sidebar).width === '0px';
                
                if (isCollapsed || !sidebar.offsetParent) {
                    // Sidebar is collapsed - show floating button
                    if (!floatingToggle) {
                        floatingToggle = document.createElement('div');
                        floatingToggle.id = 'floating-sidebar-toggle';
                        floatingToggle.className = 'sidebar-collapsed-toggle';
                        floatingToggle.onclick = function() {
                            // Click the collapse button to expand
                            const toggleBtn = document.querySelector('button[data-testid="baseButton-header"]');
                            if (toggleBtn) toggleBtn.click();
                        };
                        document.body.appendChild(floatingToggle);
                    }
                } else {
                    // Sidebar is expanded - hide floating button
                    if (floatingToggle) {
                        floatingToggle.remove();
                    }
                }
            }
        }
        
        // Check sidebar state on load and periodically
        checkSidebarState();
        setInterval(checkSidebarState, 500);
        
        // Also check when sidebar is toggled
        document.addEventListener('click', function(e) {
            if (e.target.closest('button[data-testid="baseButton-header"]')) {
                setTimeout(checkSidebarState, 350);
            }
        });
        </script>
        """,
        unsafe_allow_html=True
    )

    # Top Navbar with Profile
    current_user_display = st.session_state.current_user or "Student"
    
    # Create a custom navbar with Streamlit components
    col_brand, col_spacer, col_profile = st.columns([3, 5, 2])
    
    with col_brand:
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 24px; font-weight: 800; background: linear-gradient(135deg, #4e54c8, #8f94fb); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">🎓</span>
                <span style="font-size: 18px; font-weight: 700; color: #2c3e50; font-family: 'Poppins', sans-serif;">LectureBuddies</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col_profile:
        # Simple WordPress-style User Info display
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 10px; padding: 6px 15px; border-radius: 25px; background: linear-gradient(135deg, #f8f9ff, #e8ecff); border: 1px solid #e0e7ff;">
                <div style="width: 32px; height: 32px; border-radius: 50%; background: linear-gradient(135deg, #4e54c8, #8f94fb); display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; font-size: 14px;">
                    {current_user_display[0].upper() if current_user_display else 'U'}
                </div>
                <span style="font-weight: 600; color: #4e54c8; font-size: 14px;">
                    {current_user_display}
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Create Layout - use st.sidebar for proper sidebar integration
    # Features in Sidebar
    with st.sidebar:
        st.markdown("## 🎓 Main Menu")
        
        # Navigation menu
        if st.button("🏠 Dashboard Home", key="nav_dashboard", use_container_width=True):
            st.session_state.selected_feature = None
            st.rerun()
        
        if st.button("💬 Chatbot & Summarization", key="nav_chatbot", use_container_width=True):
            st.session_state.selected_feature = "chatbot"
            st.rerun()
        
        if st.button("📝 Quiz Generator", key="nav_quiz", use_container_width=True):
            st.session_state.selected_feature = "quiz"
            st.rerun()
        
        if st.button("🎤 Live Lecture Recording", key="nav_recording", use_container_width=True):
            st.session_state.selected_feature = "recording"
            st.rerun()
        
        if st.button("📖 Flash Cards", key="nav_flashcards", use_container_width=True):
            st.session_state.selected_feature = "flashcards"
            st.rerun()
        
        if st.button("🌐 Translation", key="nav_translation", use_container_width=True):
            st.session_state.selected_feature = "translation"
            st.rerun()
        
        if st.button("📋 Notes Manager", key="nav_notes", use_container_width=True):
            st.session_state.selected_feature = "notes"
            st.rerun()
        
        if st.button("👨‍💼 Admin Dashboard", key="nav_admin", use_container_width=True):
            st.session_state.selected_feature = "admin"
            st.rerun()
        
        if st.button("🔍 Search", key="nav_search", use_container_width=True):
            st.session_state.selected_feature = "search"
            st.rerun()
        
        if st.button("📱 Offline Mode", key="nav_offline", use_container_width=True):
            st.session_state.selected_feature = "offline"
            st.rerun()
        
        if st.button("🚪 Logout", key="logout_btn", help="Logout from your account", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.session_state.selected_feature = None
            st.rerun()

    # Main Content Area
    if st.session_state.selected_feature is None:
        show_welcome_screen()
    elif st.session_state.selected_feature == "chatbot":
        show_chatbot_feature()
    elif st.session_state.selected_feature == "quiz":
        show_quiz_feature()
    elif st.session_state.selected_feature == "recording":
        show_recording_feature()
    elif st.session_state.selected_feature == "flashcards":
        show_flashcards_feature()
    elif st.session_state.selected_feature == "translation":
        show_translation_feature()
    elif st.session_state.selected_feature == "notes":
        show_notes_feature()
    elif st.session_state.selected_feature == "admin":
        show_admin_feature()
    elif st.session_state.selected_feature == "search":
        show_search_feature()
    elif st.session_state.selected_feature == "offline":
        show_offline_feature()
    else:
        show_coming_soon_feature(st.session_state.selected_feature)

# ==========================
# WELCOME SCREEN SECTION
# ==========================
def show_welcome_screen():
    """Display welcome screen with learning visuals"""
    st.markdown(
        """
        <div class="dashboard-header">
            <h2 class="welcome-text">Welcome to LectureBuddies Dashboard!</h2>
            <p style="color: #666; font-size: 16px; font-family: 'Poppins', sans-serif;">
                Your comprehensive educational platform powered by AI. Choose a feature from the sidebar to get started.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Learning Statistics Cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            """
            <div class="feature-card">
                <h3 class="feature-title">Study Sessions</h3>
                <p class="feature-description">Track your learning progress</p>
                <h2 style="color: #4e54c8; font-size: 32px; margin: 10px 0;">24</h2>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            """
            <div class="feature-card">
                <h3 class="feature-title">Quizzes Created</h3>
                <p class="feature-description">Interactive learning materials</p>
                <h2 style="color: #4e54c8; font-size: 32px; margin: 10px 0;">12</h2>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            """
            <div class="feature-card">
                <h3 class="feature-title">Recordings</h3>
                <p class="feature-description">Audio content processed</p>
                <h2 style="color: #4e54c8; font-size: 32px; margin: 10px 0;">8</h2>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col4:
        st.markdown(
            """
            <div class="feature-card">
                <h3 class="feature-title">Progress</h3>
                <p class="feature-description">Learning efficiency</p>
                <h2 style="color: #4e54c8; font-size: 32px; margin: 10px 0;">85%</h2>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Inspirational Quote
    st.markdown(
        """
        <div class="feature-card" style="text-align: center; margin-top: 30px;">
            <h3 style="color: #4e54c8; font-size: 20px; font-weight: 600; margin-bottom: 15px; font-family: 'Poppins', sans-serif;">
                Today's Learning Quote
            </h3>
            <p style="color: #666; font-size: 18px; font-style: italic; font-family: 'Poppins', sans-serif; margin: 0;">
                "The capacity to learn is a gift; the ability to learn is a skill; the willingness to learn is a choice."
            </p>
            <p style="color: #999; font-size: 14px; margin-top: 10px; font-family: 'Poppins', sans-serif;">
                — Brian Herbert
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

# ==========================
# CHATBOT AND SUMMARIZATION SECTION
# ==========================
def show_chatbot_feature():
    """Display chatbot and summarization feature with old design"""
    # Two-Column Layout: Feature Sidebar | Main Content
    col_feature_sidebar, col_main_content = st.columns([1, 3])
    
    # Remove bottom spacing for this view
    st.markdown(
        """
        <style>
        .main .block-container { padding-bottom: 0 !important; margin-bottom: 0 !important; }
        .chip {display:inline-block; padding:4px 10px; margin:2px; background:#eef2ff; color:#4e54c8; border:1px solid #d1d9ff; border-radius:999px; font-size:12px;}
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # Initialize document processor
    doc_processor = DocumentProcessor()
    
    # LEFT: Feature-specific sidebar (Chat Settings)
    with col_feature_sidebar:
        st.markdown("### ⚙️ Chat Settings")
        st.markdown("Customize your experience.")
        
        # Model and temperature controls
        model_options = [
            "llama-3.1-8b-instant",
            "llama-3.1-70b-versatile",
            "llama-3.2-11b-text-preview"
        ]
        st.session_state.chat_model = st.selectbox("Model", model_options, index=model_options.index(st.session_state.chat_model) if st.session_state.chat_model in model_options else 0)
        st.session_state.chat_temperature = st.slider("Creativity (temperature)", 0.0, 1.0, float(st.session_state.chat_temperature), 0.1)

        # Context chips from uploaded files
        if st.session_state.document_contents:
            st.markdown("**Context Files**")
            chips = "".join([f"<span class='chip'>{fname}</span>" for fname in st.session_state.document_contents.keys()])
            st.markdown(chips, unsafe_allow_html=True)
        
        # Actions
        if st.button("🗑️ Clear Chat", key="clear_chat", use_container_width=True, help="Start a new conversation"):
            st.session_state.messages.clear()
            st.rerun()

        st.markdown("**📎 Upload Files**")
        sidebar_upload = st.file_uploader(
            "Choose files",
            type=['txt', 'pdf', 'docx', 'doc', 'png', 'jpg', 'jpeg', 'gif', 'bmp'],
            key="sidebar_uploader",
            label_visibility="collapsed",
            help="Upload documents or images for context (PDF, DOCX, TXT, Images with OCR)"
        )
        if sidebar_upload and sidebar_upload.name not in st.session_state.document_contents:
            file_details = {
                "filename": sidebar_upload.name,
                "filetype": sidebar_upload.type,
                "filesize": sidebar_upload.size
            }
            with st.spinner(f"Processing {sidebar_upload.name}..."):
                st.session_state.document_contents[sidebar_upload.name] = process_document(sidebar_upload, doc_processor)
            st.session_state.uploaded_files.append(file_details)
            st.success(f"{sidebar_upload.name} uploaded!")
            st.rerun()

        # Show uploaded files
        if st.session_state.uploaded_files:
            st.markdown("**Your Files:**")
            for i, f in enumerate(st.session_state.uploaded_files):
                st.markdown(f"📎 {f['filename']}")
                if st.button("🗑️ Remove", key=f"del_file_{i}", use_container_width=True, help="Remove file"):
                    fname = f['filename']
                    st.session_state.uploaded_files.pop(i)
                    st.session_state.document_contents.pop(fname, None)
                    st.rerun()
        
        # Regenerate last assistant response
        if st.button("🔁 Regenerate Last", key="regen_last", use_container_width=True, help="Regenerate last response using same prompt"):
            last_user = None
            for m in reversed(st.session_state.messages):
                if m.get("role") == "user":
                    last_user = m["content"]
                    break
            if last_user:
                with st.spinner("Regenerating..."):
                    reply = get_groq_response(inject_file_content(last_user), model=st.session_state.chat_model, temperature=st.session_state.chat_temperature)
                # Replace last assistant if exists, else append
                replaced = False
                for idx in range(len(st.session_state.messages)-1, -1, -1):
                    if st.session_state.messages[idx]["role"] == "assistant":
                        st.session_state.messages[idx]["content"] = reply
                        replaced = True
                        break
                if not replaced:
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                st.rerun()
        
        st.markdown("**💡 Quick Tips**")
    
    # RIGHT: Main Chat Interface
    with col_main_content:
        # Header
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #4e54c8; font-size: 28px; font-weight: 700; margin-bottom: 10px; font-family: 'Poppins', sans-serif;">
                    lecturebuddies - Chatbot
                </h1>
                <p style="color: #666; font-size: 16px; font-family: 'Poppins', sans-serif;">
                    Your intelligent study companion—chat, summarize, and learn with AI ✨
                </p>
                <hr style="border: 1px solid #4e54c8; margin: 20px 0;">
            </div>
            """,
            unsafe_allow_html=True
        )
        
        if not st.session_state.messages:
            # Welcome message box
            st.markdown(
                """
                <div style="background: #f8f9ff; padding: 30px; border-radius: 15px; text-align: center; margin: 20px 0;">
                    <h3 style="color: #4e54c8; font-size: 20px; font-weight: 600; margin-bottom: 15px; font-family: 'Poppins', sans-serif;">
                        👋 Welcome to LectureBuddies Chat!
                    </h3>
                    <p style="color: #666; font-size: 16px; font-family: 'Poppins', sans-serif;">
                        Start chatting or try a quick action below to dive into your studies.
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Quick action buttons
            col1, col2, col3 = st.columns(3)
            presets = {
                "Help with Homework": "I need help understanding this homework assignment. Can you explain step-by-step?",
                "Explain a Concept": "I'm studying this concept but finding it difficult. Can you explain clearly with examples?",
                "Study Tips": "I want to improve my study efficiency. What study strategies should I use?"
            }
            for col, (label, prompt) in zip([col1, col2, col3], presets.items()):
                with col:
                    if st.button(label, key=label.replace(" ", "_").lower(), help="Start with this prompt"):
                        st.session_state.messages.append({"role": "user", "content": prompt})
                        with st.spinner("Thinking..."):
                            reply = get_groq_response(prompt, model=st.session_state.chat_model, temperature=st.session_state.chat_temperature)
                        st.session_state.messages.append({"role": "assistant", "content": reply})
                        st.rerun()

        # Display Chat Messages
        if st.session_state.messages:
            for msg in st.session_state.messages:
                if msg["role"] == "user":
                    st.markdown(f"""
                    <div class="user-message">
                        <div class="user-bubble">
                            {msg['content']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="assistant-message">
                        <div class="assistant-bubble">
                            {msg['content']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        # Chat Input
        user_input = st.chat_input(placeholder="Ask about studies or uploaded files...")
        if user_input and user_input.strip():
            final_input = inject_file_content(user_input.strip())
            st.session_state.messages.append({"role": "user", "content": user_input.strip()})
            with st.spinner("Thinking..."):
                reply = get_groq_response(final_input, model=st.session_state.chat_model, temperature=st.session_state.chat_temperature)
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.rerun()

# ==========================
# QUIZ GENERATOR SECTION
# ==========================
def show_quiz_feature():
    """Display quiz generator feature with old design"""
    # Two-Column Layout: Feature Sidebar | Main Content
    col_feature_sidebar, col_main_content = st.columns([1, 3])
    
    # Remove bottom spacing for this view
    st.markdown(
        """
        <style>
        .main .block-container { padding-bottom: 0 !important; margin-bottom: 0 !important; }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # LEFT: Feature-specific sidebar (Quiz Settings)
    with col_feature_sidebar:
        st.markdown("### ⚙️ Quiz Settings")
        st.markdown("Customize your quiz generation.")
        
        st.markdown("**📊 Number of Questions**")
        num_questions = st.slider("How many questions?", min_value=1, max_value=20, value=st.session_state.num_questions, key="num_slider", label_visibility="collapsed")
        st.session_state.num_questions = num_questions

        st.markdown("**🎯 Difficulty Level**")
        difficulty = st.selectbox("Select difficulty:", ["Easy", "Medium", "Hard"], index=["Easy", "Medium", "Hard"].index(st.session_state.difficulty), key="diff_select", label_visibility="collapsed")
        st.session_state.difficulty = difficulty

        # Model and temperature controls
        model_options = [
            "llama-3.1-8b-instant",
            "llama-3.1-70b-versatile",
            "llama-3.2-11b-text-preview"
        ]
        st.session_state.quiz_model = st.selectbox("Model", model_options, index=model_options.index(st.session_state.quiz_model) if st.session_state.quiz_model in model_options else 0)
        st.session_state.quiz_temperature = st.slider("Creativity (temperature)", 0.0, 1.0, float(st.session_state.quiz_temperature), 0.1)
    
    # RIGHT: Main Quiz Interface
    with col_main_content:
        # Header
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #4e54c8; font-size: 28px; font-weight: 700; margin-bottom: 10px; font-family: 'Poppins', sans-serif;">
                    Lecturebuddies - Quiz Generator
                </h1>
                <p style="color: #666; font-size: 16px; font-family: 'Poppins', sans-serif;">
                    Transform your notes, lectures, or ideas into interactive quizzes with AI magic ✨
                </p>
                <hr style="border: 1px solid #4e54c8; margin: 20px 0;">
            </div>
            """,
            unsafe_allow_html=True
        )
        
        tab1, tab2, tab3 = st.tabs(["📁 Upload File", "💡 Enter Prompt", "📋 Paste Text"])

        # Tab 1 - File Upload
        with tab1:
            st.markdown("### Upload a document to generate a quiz from its content")
            uploaded_file = st.file_uploader(
                "Choose a file (PDF, DOCX, TXT)",
                type=["pdf", "docx", "txt"],
                help="Supported formats: PDF, Word documents, and plain text files."
            )

            if st.button("✨ Generate Quiz from File", key="file-btn", help=f"Create {num_questions} {difficulty} questions"):
                if uploaded_file:
                    content = extract_content_from_file(uploaded_file)
                    if content and "Error" not in content:
                        st.session_state.quiz_output = get_groq_quiz_response(content, num_questions, difficulty, model=st.session_state.quiz_model, temperature=st.session_state.quiz_temperature)
                    else:
                        st.error("Failed to extract content from file. Please try a different file or format.")
                else:
                    st.warning("Please upload a file first!")

        # Tab 2 - Prompt
        with tab2:
            st.markdown("### Describe a topic or provide content for the quiz")
            prompt_text = st.text_area(
                "Enter your topic, subject, or detailed content",
                placeholder="e.g., 'Explain photosynthesis and generate questions on it' or paste lecture notes...",
                height=100,
                help="Be as detailed as possible for better quizzes!"
            )

            if st.button("✨ Generate Quiz from Prompt", key="prompt-btn", help=f"Create {num_questions} {difficulty} questions"):
                if prompt_text.strip():
                    st.session_state.quiz_output = get_groq_quiz_response(prompt_text, num_questions, difficulty, model=st.session_state.quiz_model, temperature=st.session_state.quiz_temperature)
                else:
                    st.warning("Please enter some content or a topic!")

        # Tab 3 - Text Input
        with tab3:
            st.markdown("### Paste scanned or copied text directly")
            scanned_text = st.text_area(
                "Paste your text content here",
                placeholder="e.g., Copy-paste from a scanned PDF, image OCR, or notes...",
                height=100,
                help="Ideal for quick text from any source."
            )

            if st.button("✨ Generate Quiz from Text", key="scan-btn", help=f"Create {num_questions} {difficulty} questions"):
                if scanned_text.strip():
                    st.session_state.quiz_output = get_groq_quiz_response(scanned_text, num_questions, difficulty, model=st.session_state.quiz_model, temperature=st.session_state.quiz_temperature)
                else:
                    st.warning("Please paste some text!")

        # Display Quiz Results
        if st.session_state.quiz_output:
            if "Error" in st.session_state.quiz_output or "⚠️" in st.session_state.quiz_output or "❌" in st.session_state.quiz_output:
                st.error(st.session_state.quiz_output)
                if st.button("Clear", key="clear_error", help="Start over"):
                    st.session_state.quiz_output = None
                    st.rerun()
            else:
                st.markdown(
                    """
                    <div class="quiz-container">
                        <h3 style="color: #4e54c8; font-size: 22px; font-weight: 700; margin-bottom: 10px; text-align: center; font-family: 'Poppins', sans-serif;">
                            Your Generated Quiz
                        </h3>
                        <p style="text-align: center; color: #666; font-style: italic; font-size: 14px;">
                            {num_questions} questions at {difficulty} difficulty level
                        </p>
                    </div>
                    """.format(num_questions=st.session_state.num_questions, difficulty=st.session_state.difficulty),
                    unsafe_allow_html=True
                )

                st.markdown("### " + st.session_state.quiz_output)

                st.download_button(
                    label="Download Quiz as TXT",
                    data=st.session_state.quiz_output,
                    file_name=f"lecturebuddies_quiz_{st.session_state.num_questions}q_{st.session_state.difficulty.lower()}.txt",
                    mime="text/plain",
                    help="Save your quiz for later use!"
                )

                if st.button("Generate New Quiz", key="clear", help="Clear and start over"):
                    st.session_state.quiz_output = None
                    st.rerun()

# ==========================
# LIVE LECTURE RECORDING SECTION
# ==========================
def show_recording_feature():
    """Display simplified speech-to-text transcription via file upload (unlimited duration)"""
    # Main heading
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #4e54c8; font-size: 32px; font-weight: 700; margin-bottom: 10px; font-family: 'Poppins', sans-serif;">
                🎤 LectureBuddies — Speech to Text
            </h1>
            <p style="color: #666; font-size: 16px; font-family: 'Poppins', sans-serif;">
                Upload voice recordings or record live audio for real-time transcription
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    SAVE_DIR = "temp_recordings"
    os.makedirs(SAVE_DIR, exist_ok=True)

    # Load Whisper Model once
    @st.cache_resource
    def load_whisper_model_simple(model_size="small", device="cpu", compute_type="int8"):
        return WhisperModel(model_size, device=device, compute_type=compute_type)

    with st.spinner("Loading Faster-Whisper model... (may take a while)"):
        model = load_whisper_model_simple()

    # Tabs for different modes
    tab1, tab2 = st.tabs(["📁 Upload Audio Files", "🎤 Realtime Transcript"])

    # Tab 1: Upload Audio Files
    with tab1:
        st.markdown("### Upload audio files for transcription")
        
        # File upload (allow multiple)
        uploaded_files = st.file_uploader(
            "Upload audio file(s)",
            type=["wav", "mp3", "m4a", "flac", "ogg"],
            help="Supported formats: WAV, MP3, M4A, FLAC, OGG",
            accept_multiple_files=True,
            key="upload_files"
        )

        if uploaded_files:
            if st.button("🎯 Transcribe", key="transcribe_all", help="Start transcription of uploaded file(s)"):
                for idx, uploaded_file in enumerate(uploaded_files, start=1):
                    with st.spinner(f"Transcribing {uploaded_file.name} ({idx}/{len(uploaded_files)})..."):
                        # Save to temp
                        temp_path = os.path.join(SAVE_DIR, f"uploaded_{int(time.time())}_{uploaded_file.name}")
                        with open(temp_path, "wb") as f:
                            f.write(uploaded_file.read())

                        try:
                            segments, info = model.transcribe(temp_path, beam_size=5)
                            transcription_text = ""
                            for seg in segments:
                                transcription_text += seg.text

                            # Persist transcription
                            txt_path = os.path.join(SAVE_DIR, f"transcript_{int(time.time())}_{os.path.splitext(uploaded_file.name)[0]}.txt")
                            with open(txt_path, "w", encoding="utf-8") as f:
                                f.write(transcription_text)

                            st.success(f"✅ Transcription completed: {uploaded_file.name}")

                            # Display and downloads for each file
                            with st.expander(f"📝 {uploaded_file.name} — View Transcription"):
                                st.text_area("Transcription", value=transcription_text, height=300, key=f"tx_{idx}")
                                col_d1, col_d2 = st.columns(2)
                                with col_d1:
                                    st.download_button(
                                        "📥 Download Transcription",
                                        transcription_text,
                                        file_name=f"transcript_{os.path.splitext(uploaded_file.name)[0]}.txt",
                                        mime="text/plain",
                                        key=f"dl_txt_{idx}"
                                    )
                                with col_d2:
                                    with open(temp_path, "rb") as f:
                                        st.download_button(
                                            "📥 Download Audio",
                                            f.read(),
                                            file_name=uploaded_file.name,
                                            mime="audio/mpeg",
                                            key=f"dl_audio_{idx}"
                                        )
                        except Exception as e:
                            st.error(f"❌ Error transcribing {uploaded_file.name}: {str(e)}")
                        finally:
                            try:
                                os.remove(temp_path)
                            except Exception:
                                pass

    # Tab 2: Realtime Transcript
    with tab2:
        st.markdown("### Real-time microphone recording and transcription")
        
        # Initialize session state for realtime recording
        if "realtime_recording" not in st.session_state:
            st.session_state.realtime_recording = False
        if "realtime_transcript" not in st.session_state:
            st.session_state.realtime_transcript = ""
        if "realtime_partial" not in st.session_state:
            st.session_state.realtime_partial = ""
        if "realtime_chunks" not in st.session_state:
            st.session_state.realtime_chunks = []
        if "realtime_queue" not in st.session_state:
            st.session_state.realtime_queue = None
        if "realtime_thread" not in st.session_state:
            st.session_state.realtime_thread = None

        col1, col2 = st.columns([1, 2])

        with col1:
            st.markdown("#### 🎤 Recording Controls")
            
            # Test microphone first
            if st.button("🎤 Test Microphone", key="test_mic", help="Test if microphone is working"):
                try:
                    # Quick test recording
                    duration = 3
                    sample_rate = 16000
                    st.info(f"Recording for {duration} seconds...")
                    audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1)
                    sd.wait()
                    st.success(f"✅ Microphone test successful! Recorded {len(audio_data)} samples")
                    
                    # Test transcription
                    if st.button("🎯 Test Transcription", key="test_transcription", help="Test transcription on recorded audio"):
                        with st.spinner("Testing transcription..."):
                            try:
                                # Save test audio
                                test_path = os.path.join(SAVE_DIR, f"test_audio_{int(time.time())}.wav")
                                sf.write(test_path, audio_data, sample_rate, subtype="PCM_16")
                                
                                # Transcribe
                                segments, info = model.transcribe(test_path, beam_size=5)
                                test_text = ""
                                for seg in segments:
                                    test_text += seg.text
                                
                                if test_text.strip():
                                    st.success(f"✅ Transcription test successful: '{test_text.strip()}'")
                                else:
                                    st.warning("⚠️ No speech detected in test recording")
                                
                                # Clean up
                                try:
                                    os.remove(test_path)
                                except:
                                    pass
                            except Exception as e:
                                st.error(f"❌ Transcription test failed: {e}")
                except Exception as e:
                    st.error(f"❌ Microphone test failed: {e}")
            
            if not st.session_state.realtime_recording:
                if st.button("🎤 Start Recording", key="start_realtime", help="Start real-time recording", use_container_width=True):
                    try:
                        # Initialize recording
                        st.session_state.realtime_queue = queue.Queue()
                        st.session_state.realtime_recording = True
                        st.session_state.realtime_transcript = ""
                        st.session_state.realtime_partial = ""
                        st.session_state.realtime_chunks = []

                        stop_event = threading.Event()
                        st.session_state.realtime_stop_event = stop_event

                        # Start recording thread
                        rec_thread = threading.Thread(target=realtime_record_worker, args=(st.session_state.realtime_queue, stop_event), daemon=True)
                        rec_thread.start()
                        st.session_state.realtime_thread = rec_thread

                        # Start audio stream
                        try:
                            st.session_state.realtime_stream = sd.InputStream(
                                samplerate=16000,
                                channels=1,
                                callback=realtime_sd_callback,
                                blocksize=0
                            )
                            st.session_state.realtime_stream.start()
                            st.success("🎤 Recording started! Speak into your microphone...")
                        except Exception as e:
                            st.error(f"Failed to open microphone: {e}")
                            st.session_state.realtime_recording = False

                        # Start transcription consumer
                        consumer_thread = threading.Thread(target=realtime_transcription_consumer, args=(model, 5), daemon=True)
                        consumer_thread.start()
                        st.session_state.realtime_consumer_thread = consumer_thread

                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to start recording: {e}")
            else:
                col_stop, col_refresh = st.columns(2)
                with col_stop:
                    if st.button("⏹️ Stop Recording", key="stop_realtime", help="Stop recording", use_container_width=True):
                        # Stop recording
                        st.session_state.realtime_recording = False
                        if 'realtime_stream' in st.session_state and st.session_state.realtime_stream:
                            try:
                                st.session_state.realtime_stream.stop()
                                st.session_state.realtime_stream.close()
                            except Exception:
                                pass

                        # Process final audio
                        time.sleep(6)  # Wait for final chunk

                        # Save final transcript
                        final_transcript = st.session_state.realtime_transcript.strip()
                        if final_transcript:
                            txt_path = os.path.join(SAVE_DIR, f"realtime_transcript_{int(time.time())}.txt")
                            with open(txt_path, "w", encoding="utf-8") as f:
                                f.write(final_transcript)

                        st.success("⏹️ Recording stopped!")
                        if final_transcript:
                            st.download_button("📥 Download Realtime Transcript", final_transcript, file_name="realtime_transcript.txt", key="dl_realtime")
                        st.rerun()
                
                with col_refresh:
                    if st.button("🔄 Refresh", key="refresh_realtime", help="Refresh transcription", use_container_width=True):
                        st.rerun()

            # Recording status
            if st.session_state.realtime_recording:
                st.markdown("**Status:** 🔴 Recording")
                st.markdown("**Duration:** Unlimited")
                st.markdown("**Instructions:** Speak clearly into your microphone")
                st.markdown("**Note:** Click 'Refresh' to see new transcription")
            else:
                st.markdown("**Status:** ⏹️ Stopped")

        with col2:
            st.markdown("#### 📝 Live Transcription")
            
            # Display partial transcript
            if st.session_state.realtime_partial:
                st.markdown(f"**Latest:** {st.session_state.realtime_partial}")
            else:
                st.markdown("**Latest:** _(none yet)_")
            
            # Display full transcript
            st.text_area("Full transcript", value=st.session_state.realtime_transcript, height=400, key="realtime_display")
            
            # Debug info
            if st.session_state.realtime_recording:
                st.markdown("**Debug Info:**")
                st.markdown(f"- Queue size: {st.session_state.realtime_queue.qsize() if st.session_state.realtime_queue else 'N/A'}")
                st.markdown(f"- Chunks processed: {len(st.session_state.realtime_chunks)}")

# ==========================
# FLASH CARDS FEATURE
# ==========================
def show_flashcards_feature():
    """Display flash cards generator feature"""
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #4e54c8; font-size: 32px; font-weight: 700; margin-bottom: 10px; font-family: 'Poppins', sans-serif;">
                📖 Flash Cards Generator
            </h1>
            <p style="color: #666; font-size: 16px; font-family: 'Poppins', sans-serif;">
                Create interactive flash cards from your study materials
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### ⚙️ Settings")
        st.markdown("---")
        
        # Flash card settings
        num_cards = st.slider("Number of Cards", 1, 50, 10)
        difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
        subject = st.text_input("Subject/Topic", placeholder="e.g., Biology, History")
        
        st.markdown("---")
        st.markdown("**📄 Upload Content**")
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=['txt', 'pdf', 'docx'],
            help="Upload study material to generate flash cards"
        )
    
    with col2:
        st.markdown("### 📝 Content Input")
        
        content_input = st.text_area(
            "Or paste your study content here",
            placeholder="Paste your study material, lecture notes, or textbook content...",
            height=200
        )
        
        if st.button("🎯 Generate Flash Cards", key="generate_cards", use_container_width=True):
            if content_input or uploaded_file:
                with st.spinner("Generating flash cards..."):
                    # Generate flash cards using AI
                    flashcards = generate_flashcards(content_input or "Sample content", num_cards, difficulty, subject)
                    st.session_state.flashcards = flashcards
                    st.success(f"✅ Generated {len(flashcards)} flash cards!")
            else:
                st.warning("Please provide content to generate flash cards")
        
        # Display generated flash cards
        if st.session_state.get('flashcards'):
            st.markdown("### 🃏 Your Flash Cards")
            display_flashcards(st.session_state.flashcards)

def generate_flashcards(content, num_cards, difficulty, subject):
    """Generate flash cards from content using AI"""
    if not api_key:
        return [{"front": "Error: No API key", "back": "Please set GROQ_API_KEY in your .env file"}]
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    prompt = f"""
    Create {num_cards} flash cards from this content for {subject or 'general study'}.
    Difficulty level: {difficulty}
    
    Content: {content[:2000]}
    
    Format each card as:
    Front: [Question or term]
    Back: [Answer or definition]
    
    Make them educational and useful for studying.
    """
    
    messages = [
        {"role": "system", "content": "You are a helpful study assistant that creates educational flash cards."},
        {"role": "user", "content": prompt}
    ]
    
    payload = {"model": "llama-3.1-8b-instant", "messages": messages, "temperature": 0.7, "max_tokens": 1000}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return parse_flashcards(content)
        else:
            return [{"front": "Error generating cards", "back": f"API Error: {response.status_code}"}]
    except Exception as e:
        return [{"front": "Error", "back": f"Failed to generate cards: {str(e)}"}]

def parse_flashcards(content):
    """Parse AI response into flash card format"""
    cards = []
    lines = content.split('\n')
    current_card = {}
    
    for line in lines:
        line = line.strip()
        if line.startswith('Front:'):
            if current_card:
                cards.append(current_card)
            current_card = {"front": line.replace('Front:', '').strip(), "back": ""}
        elif line.startswith('Back:'):
            current_card["back"] = line.replace('Back:', '').strip()
    
    if current_card:
        cards.append(current_card)
    
    return cards if cards else [{"front": "Sample Question", "back": "Sample Answer"}]

def display_flashcards(cards):
    """Display flash cards in an interactive format"""
    if not cards:
        return
    
    # Initialize session state for current card
    if 'current_card_index' not in st.session_state:
        st.session_state.current_card_index = 0
    
    current_index = st.session_state.current_card_index
    current_card = cards[current_index]
    
    # Card display
    st.markdown(
        f"""
        <div style="background: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center; margin: 20px 0;">
            <h3 style="color: #4e54c8; margin-bottom: 20px;">Card {current_index + 1} of {len(cards)}</h3>
            <div style="background: #f8f9ff; padding: 20px; border-radius: 10px; margin: 20px 0;">
                <h4 style="color: #2c3e50; margin-bottom: 15px;">Front:</h4>
                <p style="font-size: 18px; color: #333;">{current_card['front']}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Show answer button
    if st.button("👁️ Show Answer", key="show_answer"):
        st.markdown(
            f"""
            <div style="background: #e8f5e8; padding: 20px; border-radius: 10px; margin: 20px 0;">
                <h4 style="color: #2c3e50; margin-bottom: 15px;">Back:</h4>
                <p style="font-size: 18px; color: #333;">{current_card['back']}</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Navigation
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("⬅️ Previous", key="prev_card", disabled=current_index == 0):
            st.session_state.current_card_index = max(0, current_index - 1)
            st.rerun()
    
    with col2:
        st.markdown(f"<div style='text-align: center; color: #666;'>Card {current_index + 1} of {len(cards)}</div>", unsafe_allow_html=True)
    
    with col3:
        if st.button("Next ➡️", key="next_card", disabled=current_index == len(cards) - 1):
            st.session_state.current_card_index = min(len(cards) - 1, current_index + 1)
            st.rerun()

# ==========================
# MULTILINGUAL TRANSLATION FEATURE
# ==========================
def show_translation_feature():
    """Display multilingual translation feature"""
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #4e54c8; font-size: 32px; font-weight: 700; margin-bottom: 10px; font-family: 'Poppins', sans-serif;">
                🌐 Multilingual Translation
            </h1>
            <p style="color: #666; font-size: 16px; font-family: 'Poppins', sans-serif;">
                Translate text to your selected language (source auto-detected)
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### ⚙️ Translation Settings")
        st.markdown("---")
        
        # Language selection (target only)
        languages = {
            "English": "en",
            "Spanish": "es", 
            "French": "fr",
            "German": "de",
            "Italian": "it",
            "Portuguese": "pt",
            "Chinese": "zh",
            "Japanese": "ja",
            "Korean": "ko",
            "Arabic": "ar",
            "Hindi": "hi",
            "Russian": "ru",
            "Urdu": "ur",
            "Punjabi": "pa",
            "Sindhi": "sd"
        }
        target_lang_label = st.selectbox("To Language", list(languages.keys()))
        
        st.markdown("---")
        st.markdown("**📄 Upload Document**")
        uploaded_file = st.file_uploader(
            "Choose a text file",
            type=['txt', 'docx'],
            help="Upload a document to translate"
        )
    
    with col2:
        st.markdown("### 📝 Text Translation")
        
        # Text input
        text_input = st.text_area(
            "Enter text to translate",
            placeholder="Type or paste your text here...",
            height=200
        )
        
        if st.button("🔄 Translate", key="translate_text", use_container_width=True):
            if text_input or uploaded_file:
                with st.spinner("Translating..."):
                    if uploaded_file:
                        # Process uploaded file
                        content = extract_content_from_file(uploaded_file)
                        translated = translate_text(content, target_lang_label)
                    else:
                        translated = translate_text(text_input, target_lang_label)
                    
                    st.session_state.translation_result = translated
                    st.success("✅ Translation completed!")
            else:
                st.warning("Please provide text to translate")
        
        # Display translation result
        if st.session_state.get('translation_result'):
            st.markdown("### 🌐 Translation Result")
            st.text_area("Translated Text", value=st.session_state.translation_result, height=200, key="translation_display")
            
            # Download button
            st.download_button(
                "📥 Download Translation",
                st.session_state.translation_result,
                file_name=f"translation_to_{languages[target_lang_label]}.txt",
                mime="text/plain"
            )

def translate_text(text, target_language_label):
    """Translate text using AI; auto-detect source language"""
    if not api_key:
        return "Error: No API key available"
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    prompt = (
        f"Detect the source language and translate the following text to {target_language_label}. "
        f"Only return the translated text, no explanations or prefixes.\n\n{text}"
    )
    
    messages = [
        {"role": "system", "content": "You are a professional translator. Translate accurately and naturally."},
        {"role": "user", "content": prompt}
    ]
    
    payload = {"model": "llama-3.1-8b-instant", "messages": messages, "temperature": 0.3, "max_tokens": 1000}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "Translation failed")
        else:
            return f"Translation error: {response.status_code}"
    except Exception as e:
        return f"Translation failed: {str(e)}"

# ==========================
# NOTES MANAGER FEATURE
# ==========================
def show_notes_feature():
    """Display notes manager with import/export and organization"""
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #4e54c8; font-size: 32px; font-weight: 700; margin-bottom: 10px; font-family: 'Poppins', sans-serif;">
                📋 Notes Manager
            </h1>
            <p style="color: #666; font-size: 16px; font-family: 'Poppins', sans-serif;">
                Organize, import, and export your study notes with rich text formatting
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Initialize notes in session state
    if 'notes' not in st.session_state:
        st.session_state.notes = []
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### 📁 Note Organization")
        st.markdown("---")
        
        # Categories
        categories = ["General", "Mathematics", "Science", "History", "Language", "Other"]
        selected_category = st.selectbox("Category", categories)
        
        # Tags
        tags_input = st.text_input("Tags (comma-separated)", placeholder="e.g., important, exam, review")
        
        st.markdown("---")
        st.markdown("**📤 Import/Export**")
        
        # Import notes
        uploaded_notes = st.file_uploader(
            "Import Notes",
            type=['txt', 'json'],
            help="Import notes from file"
        )
        
        if uploaded_notes:
            if st.button("📥 Import Notes", key="import_notes"):
                try:
                    if uploaded_notes.type == "application/json":
                        notes_data = json.loads(uploaded_notes.read())
                        st.session_state.notes.extend(notes_data)
                    else:
                        content = uploaded_notes.read().decode('utf-8')
                        new_note = {
                            "title": uploaded_notes.name,
                            "content": content,
                            "category": selected_category,
                            "tags": tags_input.split(',') if tags_input else [],
                            "created": time.time()
                        }
                        st.session_state.notes.append(new_note)
                    st.success("✅ Notes imported successfully!")
                except Exception as e:
                    st.error(f"❌ Import failed: {str(e)}")
        
        # Export notes
        if st.session_state.notes:
            if st.button("📤 Export All Notes", key="export_notes"):
                notes_json = json.dumps(st.session_state.notes, indent=2)
                st.download_button(
                    "💾 Download Notes (JSON)",
                    notes_json,
                    file_name=f"lecturebuddies_notes_{int(time.time())}.json",
                    mime="application/json"
                )
    
    with col2:
        st.markdown("### ✏️ Create New Note")
        
        # Note creation form
        note_title = st.text_input("Note Title", placeholder="Enter note title")
        
        # Rich text editor (simplified)
        note_content = st.text_area(
            "Note Content",
            placeholder="Write your note here...\n\nYou can use basic formatting:\n**Bold text**\n*Italic text*\n# Heading\n- Bullet point",
            height=300
        )
        
        if st.button("💾 Save Note", key="save_note", use_container_width=True):
            if note_title and note_content:
                new_note = {
                    "title": note_title,
                    "content": note_content,
                    "category": selected_category,
                    "tags": [tag.strip() for tag in tags_input.split(',')] if tags_input else [],
                    "created": time.time(),
                    "modified": time.time()
                }
                st.session_state.notes.append(new_note)
                st.success("✅ Note saved successfully!")
                st.rerun()
            else:
                st.warning("Please enter both title and content")
        
        # Display existing notes
        if st.session_state.notes:
            st.markdown("### 📚 Your Notes")
            for i, note in enumerate(st.session_state.notes):
                with st.expander(f"📝 {note['title']} ({note['category']})"):
                    st.markdown(f"**Created:** {time.ctime(note['created'])}")
                    st.markdown(f"**Tags:** {', '.join(note['tags']) if note['tags'] else 'None'}")
                    st.markdown("**Content:**")
                    st.markdown(note['content'])
                    
                    col_del, col_edit = st.columns(2)
                    with col_del:
                        if st.button("🗑️ Delete", key=f"del_note_{i}"):
                            st.session_state.notes.pop(i)
                            st.rerun()
                    with col_edit:
                        if st.button("✏️ Edit", key=f"edit_note_{i}"):
                            st.session_state.editing_note = i
                            st.rerun()

# ==========================
# ADMIN DASHBOARD FEATURE
# ==========================
def show_admin_feature():
    """Display admin dashboard for system management"""
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #4e54c8; font-size: 32px; font-weight: 700; margin-bottom: 10px; font-family: 'Poppins', sans-serif;">
                👨‍💼 Admin Dashboard
            </h1>
            <p style="color: #666; font-size: 16px; font-family: 'Poppins', sans-serif;">
                System management and analytics for administrators
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Check if user is admin
    if st.session_state.current_user != "admin":
        st.warning("🔒 Admin access required. Please login as admin.")
        return
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 📊 System Stats")
        st.metric("Total Users", "1,234")
        st.metric("Active Sessions", "45")
        st.metric("Storage Used", "2.3 GB")
    
    with col2:
        st.markdown("### 🎯 Feature Usage")
        st.metric("Chatbot Queries", "5,678")
        st.metric("Quiz Generated", "234")
        st.metric("Recordings Made", "89")
    
    with col3:
        st.markdown("### ⚙️ System Health")
        st.metric("API Status", "✅ Online")
        st.metric("Database", "✅ Connected")
        st.metric("Storage", "✅ Available")
    
    st.markdown("---")
    
    # System management
    st.markdown("### 🔧 System Management")
    
    tab1, tab2, tab3 = st.tabs(["Users", "Settings", "Logs"])
    
    with tab1:
        st.markdown("#### 👥 User Management")
        st.dataframe({
            "Username": ["admin", "student1", "student2"],
            "Role": ["Admin", "Student", "Student"],
            "Last Login": ["2024-01-15", "2024-01-14", "2024-01-13"],
            "Status": ["Active", "Active", "Inactive"]
        })
    
    with tab2:
        st.markdown("#### ⚙️ System Settings")
        st.checkbox("Enable Registration", value=True)
        st.checkbox("Maintenance Mode", value=False)
        st.slider("Max File Size (MB)", 1, 100, 10)
    
    with tab3:
        st.markdown("#### 📋 System Logs")
        st.text_area("Recent Logs", value="2024-01-15 10:30:15 - User login: admin\n2024-01-15 10:25:32 - Quiz generated: student1\n2024-01-15 10:20:45 - Recording started: student2", height=200)

# ==========================
# CATEGORIZED SEARCH FEATURE
# ==========================
def show_search_feature():
    """Display categorized search functionality"""
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #4e54c8; font-size: 32px; font-weight: 700; margin-bottom: 10px; font-family: 'Poppins', sans-serif;">
                🔍 Categorized Search
            </h1>
            <p style="color: #666; font-size: 16px; font-family: 'Poppins', sans-serif;">
                Search across all your content with advanced filtering and categorization
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### 🔍 Search Filters")
        st.markdown("---")
        
        # Search categories
        search_categories = st.multiselect(
            "Search in:",
            ["Chat History", "Notes", "Quizzes", "Recordings", "Flash Cards"],
            default=["Chat History", "Notes"]
        )
        
        # Date range
        date_range = st.date_input("Date Range", value=[])
        
        # Content type
        content_type = st.selectbox("Content Type", ["All", "Text", "Audio", "Images", "Documents"])
        
        # Tags filter
        tags_filter = st.text_input("Tags", placeholder="e.g., important, exam")
    
    with col2:
        st.markdown("### 🔎 Search Query")
        
        search_query = st.text_input(
            "Enter your search query",
            placeholder="Search for specific topics, keywords, or phrases...",
            key="search_input"
        )
        
        if st.button("🔍 Search", key="perform_search", use_container_width=True):
            if search_query:
                with st.spinner("Searching..."):
                    results = perform_search(search_query, search_categories, date_range, content_type, tags_filter)
                    st.session_state.search_results = results
                    st.success(f"✅ Found {len(results)} results!")
            else:
                st.warning("Please enter a search query")
        
        # Display search results
        if st.session_state.get('search_results'):
            st.markdown("### 📋 Search Results")
            display_search_results(st.session_state.search_results)

def perform_search(query, categories, date_range, content_type, tags_filter):
    """Perform categorized search"""
    # This is a simplified search implementation
    # In a real application, you would search through actual data
    results = []
    
    # Simulate search results
    sample_results = [
        {
            "title": "Chemistry Notes - Organic Compounds",
            "content": "Organic compounds are carbon-based molecules...",
            "category": "Notes",
            "date": "2024-01-15",
            "tags": ["chemistry", "organic", "important"],
            "relevance": 0.95
        },
        {
            "title": "Math Quiz - Calculus",
            "content": "Quiz questions about derivatives and integrals...",
            "category": "Quizzes", 
            "date": "2024-01-14",
            "tags": ["math", "calculus", "quiz"],
            "relevance": 0.87
        },
        {
            "title": "Biology Lecture Recording",
            "content": "Transcription of biology lecture about cell division...",
            "category": "Recordings",
            "date": "2024-01-13",
            "tags": ["biology", "lecture", "cell"],
            "relevance": 0.82
        }
    ]
    
    # Filter results based on search criteria
    for result in sample_results:
        if result['category'] in categories:
            if query.lower() in result['title'].lower() or query.lower() in result['content'].lower():
                results.append(result)
    
    return sorted(results, key=lambda x: x['relevance'], reverse=True)

def display_search_results(results):
    """Display search results in a formatted way"""
    for i, result in enumerate(results):
        with st.expander(f"📄 {result['title']} (Relevance: {result['relevance']:.2f})"):
            st.markdown(f"**Category:** {result['category']}")
            st.markdown(f"**Date:** {result['date']}")
            st.markdown(f"**Tags:** {', '.join(result['tags'])}")
            st.markdown(f"**Content:** {result['content'][:200]}...")
            
            if st.button("📖 View Full", key=f"view_result_{i}"):
                st.markdown(f"**Full Content:**\n\n{result['content']}")

# ==========================
# OFFLINE MODE FEATURE
# ==========================
def show_offline_feature():
    """Display offline mode functionality"""
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #4e54c8; font-size: 32px; font-weight: 700; margin-bottom: 10px; font-family: 'Poppins', sans-serif;">
                📱 Offline Mode
            </h1>
            <p style="color: #666; font-size: 16px; font-family: 'Poppins', sans-serif;">
                Access your content and basic features without internet connection
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Check internet connection
    try:
        requests.get("https://www.google.com", timeout=5)
        internet_status = "🟢 Online"
        connection_color = "#28a745"
    except:
        internet_status = "🔴 Offline"
        connection_color = "#dc3545"
    
    st.markdown(
        f"""
        <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0; text-align: center;">
            <h3 style="color: {connection_color}; margin-bottom: 10px;">Connection Status: {internet_status}</h3>
            <p style="color: #666;">Current mode: {'Offline' if 'Offline' in internet_status else 'Online'}</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📱 Offline Features")
        st.markdown("---")
        
        offline_features = [
            "📚 View saved notes",
            "🃏 Review flash cards", 
            "📝 Read saved quizzes",
            "🎧 Play downloaded recordings",
            "🔍 Search local content",
            "📊 View offline analytics"
        ]
        
        for feature in offline_features:
            st.markdown(f"✅ {feature}")
        
        st.markdown("---")
        st.markdown("### 💾 Sync Options")
        
        if st.button("🔄 Sync Now", key="sync_now"):
            if "Offline" in internet_status:
                st.warning("⚠️ No internet connection. Sync will happen when you're back online.")
            else:
                st.success("✅ Sync completed! All offline content updated.")
    
    with col2:
        st.markdown("### 📊 Offline Content")
        
        # Display offline content stats
        st.metric("Saved Notes", "23")
        st.metric("Flash Cards", "156")
        st.metric("Quizzes", "12")
        st.metric("Recordings", "8")
        
        st.markdown("---")
        st.markdown("### ⚙️ Offline Settings")
        
        auto_sync = st.checkbox("Auto-sync when online", value=True)
        download_quality = st.selectbox("Download Quality", ["High", "Medium", "Low"])
        storage_limit = st.slider("Storage Limit (GB)", 1, 10, 5)
        
        if st.button("💾 Download for Offline", key="download_offline"):
            st.info("📥 Downloading content for offline use...")
            st.progress(0.7)
            st.success("✅ Offline content ready!")

# ==========================
# HELPER FUNCTIONS
# ==========================
def inject_file_content(user_message: str) -> str:
    """Replace file references in user message with extracted text"""
    for fname, content in st.session_state.document_contents.items():
        if fname.lower() in user_message.lower():
            extracted = content if content.strip() else "[No text extracted from this file]"
            user_message = user_message.replace(
                fname,
                f"(Extracted content: {extracted[:1000]}...)"
            )
    return user_message

def get_groq_response(user_input, model="llama-3.1-8b-instant", temperature=0.7):
    """Send query + context to Groq API and return assistant response"""
    if not api_key or api_key.strip() == "":
        return "Missing API key. Please set GROQ_API_KEY in your .env file."

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    # Build document context
    doc_context = ""
    if st.session_state.document_contents:
        doc_context = "\n\n**Available Documents:**\n"
        for fname, content in st.session_state.document_contents.items():
            snippet = content[:1000] if content else "[No extractable text]"
            doc_context += f"\n--- {fname} ---\n{snippet}...\n"

    # Build conversation
    messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
    system_msg = (
        f"You are LectureBuddies, an AI chatbot designed for education. "
        f"Answer clearly, summarize effectively, and explain concepts step by step."
        f"{' Available Documents: ' + doc_context if doc_context else ''}\n\n"
        "Guidelines:\n"
        "Education-focused\n"
        "Summarization expert\n"
        "Clarity first (simple language, then details)\n"
        "Confidence + accuracy\n"
        "Break down topics step-by-step, use examples, and stay professional yet supportive."
    )
    messages.insert(0, {"role": "system", "content": system_msg})
    messages.append({"role": "user", "content": user_input})

    payload = {"model": model, "messages": messages, "temperature": float(temperature), "max_tokens": 1000}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "No response received.")
        elif resp.status_code == 401:
            return "Invalid API key. Please check GROQ_API_KEY in your .env file."
        elif resp.status_code == 429:
            return "Too many requests. Please slow down and retry shortly."
        else:
            return f"API Error {resp.status_code}: {resp.text}"
    except requests.exceptions.Timeout:
        return "Request timed out. Please retry."
    except requests.exceptions.RequestException as e:
        return f"Network error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"

def process_document(uploaded_file, doc_processor):
    """Extract text from uploaded documents"""
    try:
        temp_path = os.path.join("temp", uploaded_file.name)
        os.makedirs("temp", exist_ok=True)
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.read())

        content = doc_processor.process_document(temp_path)
        return content if content.strip() else "[No text extracted]"
    except Exception as e:
        return f"[File processing error: {e}]"

def get_groq_quiz_response(content, num_questions=5, difficulty="Medium", model="llama-3.1-8b-instant", temperature=0.7):
    """Send content to Groq API and get quiz questions back"""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    difficulty_map = {"Easy": "simple and straightforward", "Medium": "balanced and informative", "Hard": "challenging and detailed"}
    diff_desc = difficulty_map.get(difficulty, "balanced")

    system_msg = (
        "You are LectureBuddies Quiz Generator. "
        "Your task is to generate high-quality multiple-choice quizzes (MCQs) from educational material. "
        f"Generate exactly {num_questions} MCQs. Each question should have 4 options (A, B, C, D), one correct answer, "
        "and clearly mark the correct answer (e.g., Correct: A). "
        f"Make questions {diff_desc} in difficulty. "
        "Format the output neatly with numbered questions, bold question text, and labeled options. "
        "End with a summary of correct answers."
    )

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": f"Generate a quiz from this content:\n\n{content}"}
    ]

    payload = {"model": model, "messages": messages, "temperature": float(temperature), "max_tokens": 1200}

    try:
        with st.spinner(f"Generating {num_questions} {difficulty} quiz questions..."):
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "No response received.")
        elif resp.status_code == 401:
            return "Invalid API key. Please check GROQ_API_KEY in your .env file."
        elif resp.status_code == 429:
            return "Too many requests. Please retry shortly."
        else:
            return f"API Error {resp.status_code}: {resp.text}"
    except requests.exceptions.Timeout:
        return "Request timed out. Please retry."
    except Exception as e:
        return f"Error: {str(e)}"

def extract_content_from_file(uploaded_file):
    """Extract text content from uploaded file (PDF, DOCX, TXT)"""
    file_type = uploaded_file.type if hasattr(uploaded_file, 'type') else uploaded_file.name.split('.')[-1].lower()

    try:
        if file_type == "application/pdf" or file_type.endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
            content = ""
            for page in pdf_reader.pages:
                text = page.extract_text() or ""
                content += text + "\n"
            return content.strip()
        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or file_type.endswith('.docx'):
            doc = Document(io.BytesIO(uploaded_file.read()))
            content = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
            return content.strip()
        else:  # TXT or other text-based
            return uploaded_file.read().decode("utf-8", errors="ignore").strip()
    except Exception as e:
        return f"Error extracting content: {str(e)}"

# Recording helper functions
def record_worker(audio_q: queue.Queue, stop_event: threading.Event):
    """Recording thread worker"""
    while not stop_event.is_set():
        time.sleep(0.1)

def sd_callback(indata, frames, time_info, status):
    """Callback for sounddevice.InputStream"""
    if status:
        pass
    mono = np.mean(indata, axis=1).astype(np.float32)
    # guard: audio_queue may be None if recording not properly started
    if st.session_state.get("audio_queue") is not None:
        try:
            st.session_state.audio_queue.put(mono)
        except Exception:
            pass

def transcription_consumer(model: WhisperModel, chunk_seconds=5):
    """Transcription consumer thread"""
    sample_per_chunk = chunk_seconds * 16000
    buffer = np.zeros((0,), dtype=np.float32)
    chunk_index = 0

    while st.session_state.recording or (st.session_state.audio_queue is not None and not st.session_state.audio_queue.empty()):
        try:
            while st.session_state.audio_queue is not None and not st.session_state.audio_queue.empty():
                data = st.session_state.audio_queue.get_nowait()
                buffer = np.concatenate((buffer, data))

            if buffer.shape[0] >= sample_per_chunk:
                to_process = buffer[:sample_per_chunk]
                buffer = buffer[sample_per_chunk:]

                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp_path = tmp.name
                    sf.write(tmp_path, to_process, 16000, subtype="PCM_16")

                segments, info = model.transcribe(tmp_path, beam_size=5)
                partial_text = ""
                for seg in segments:
                    partial_text += seg.text

                prev = st.session_state.transcript
                st.session_state.transcript = (prev + " " + partial_text).strip()
                st.session_state.partial_transcript = partial_text

                saved_chunk = os.path.join("temp_recordings", f"chunk_{int(time.time())}_{chunk_index}.wav")
                os.replace(tmp_path, saved_chunk)
                st.session_state.chunks_saved.append(saved_chunk)
                chunk_index += 1
            else:
                time.sleep(0.2)
        except Exception:
            time.sleep(0.1)
    return

# Realtime recording helper functions
def realtime_record_worker(audio_q: queue.Queue, stop_event: threading.Event):
    """Recording thread worker for realtime"""
    while not stop_event.is_set():
        time.sleep(0.1)

def realtime_sd_callback(indata, frames, time_info, status):
    """Callback for sounddevice.InputStream in realtime mode"""
    if status:
        pass
    mono = np.mean(indata, axis=1).astype(np.float32)
    if st.session_state.get("realtime_queue") is not None:
        try:
            st.session_state.realtime_queue.put(mono)
        except Exception:
            pass

def realtime_transcription_consumer(model: WhisperModel, chunk_seconds=5):
    """Transcription consumer thread for realtime"""
    sample_per_chunk = chunk_seconds * 16000
    buffer = np.zeros((0,), dtype=np.float32)
    chunk_index = 0

    while st.session_state.realtime_recording or (st.session_state.realtime_queue is not None and not st.session_state.realtime_queue.empty()):
        try:
            # Get audio data from queue
            while st.session_state.realtime_queue is not None and not st.session_state.realtime_queue.empty():
                data = st.session_state.realtime_queue.get_nowait()
                buffer = np.concatenate((buffer, data))

            # Process when we have enough data
            if buffer.shape[0] >= sample_per_chunk:
                to_process = buffer[:sample_per_chunk]
                buffer = buffer[sample_per_chunk:]

                # Save audio chunk to temporary file
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp_path = tmp.name
                    sf.write(tmp_path, to_process, 16000, subtype="PCM_16")

                # Transcribe the chunk
                try:
                    segments, info = model.transcribe(tmp_path, beam_size=5)
                    partial_text = ""
                    for seg in segments:
                        partial_text += seg.text

                    # Update session state
                    if partial_text.strip():
                        prev = st.session_state.realtime_transcript
                        st.session_state.realtime_transcript = (prev + " " + partial_text).strip()
                        st.session_state.realtime_partial = partial_text
                        
                        # Save chunk for debugging
                        saved_chunk = os.path.join("temp_recordings", f"realtime_chunk_{int(time.time())}_{chunk_index}.wav")
                        os.replace(tmp_path, saved_chunk)
                        st.session_state.realtime_chunks.append(saved_chunk)
                        chunk_index += 1
                        
                        print(f"Transcribed chunk {chunk_index}: {partial_text}")  # Debug print
                    else:
                        print(f"No text in chunk {chunk_index}")  # Debug print
                        os.remove(tmp_path)
                        
                except Exception as e:
                    print(f"Transcription error: {e}")  # Debug print
                    try:
                        os.remove(tmp_path)
                    except:
                        pass
            else:
                time.sleep(0.2)
        except Exception as e:
            print(f"Consumer error: {e}")  # Debug print
            time.sleep(0.1)
    return

# ==========================
# MAIN APPLICATION LOGIC
# ==========================
def main():
    """Main application entry point"""
    if not st.session_state.authenticated:
        show_login_page()
    else:
        show_dashboard()

if __name__ == "__main__":
    main()
