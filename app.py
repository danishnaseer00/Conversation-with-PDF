# ========================================
# MODIFIED FRONTEND - app.py
# Run this in VSCode on your local PC
# ========================================

import streamlit as st
import requests
import os


# Page configuration
st.set_page_config(
    page_title="PDF Chat Assistant",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)



# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "pdf_uploaded" not in st.session_state:
    st.session_state.pdf_uploaded = False
if "api_url" not in st.session_state:
    st.session_state.api_url = ""
if "connected" not in st.session_state:
    st.session_state.connected = False

# ========================================
# BACKEND COMMUNICATION FUNCTIONS
# ========================================

def check_backend_connection(url):
    """Check if backend is accessible."""
    try:
        response = requests.get(f"{url}/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return True, data
        return False, None
    except Exception as e:
        return False, str(e)

def process_pdf_backend(api_url, file):
    """Send PDF to backend for processing."""
    try:
        files = {'file': (file.name, file.getvalue(), 'application/pdf')}
        response = requests.post(
            f"{api_url}/process-pdf",
            files=files,
            timeout=300  # 5 minutes
        )
        return response.json(), response.status_code
    except requests.exceptions.Timeout:
        return {"error": "Request timed out. PDF might be too large."}, 408
    except Exception as e:
        return {"error": str(e)}, 500

def ask_question_backend(api_url, question, top_k=3):
    """Get answer from backend."""
    try:
        data = {"query": question, "top_k": top_k}
        response = requests.post(
            f"{api_url}/answer",
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        return response.json(), response.status_code
    except Exception as e:
        return {"error": str(e)}, 500

def get_backend_stats(api_url):
    """Get backend statistics."""
    try:
        response = requests.get(f"{api_url}/stats", timeout=5)
        return response.json()
    except:
        return {"total_chunks": 0}

def clear_backend_collection(api_url):
    """Clear backend collection."""
    try:
        response = requests.post(f"{api_url}/clear", timeout=10)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# ========================================
# MAIN APP
# ========================================

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1 class="main-title">📄 PDF Chat Assistant</h1>
        <p class="main-subtitle">Upload a PDF and start a conversation with your document</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 🔗 Backend Connection")
        st.markdown("---")
        
        # Backend URL input
        api_url_input = st.text_input(
            "Colab Backend URL",
            value=st.session_state.api_url,
            placeholder="",
            help="Enter the ngrok URL from your Colab notebook"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔌 Connect", type="primary"):
                if api_url_input:
                    with st.spinner("Connecting..."):
                        connected, data = check_backend_connection(api_url_input)
                        if connected:
                            st.session_state.api_url = api_url_input
                            st.session_state.connected = True
                            st.success("✅ Connected!")
                            st.rerun()
                        else:
                            st.error(f"❌ Connection failed: {data}")
                else:
                    st.warning("Please enter URL")
        
        with col2:
            if st.button("🔄 Refresh"):
                st.rerun()
        
        st.markdown("---")
        
        # Connection status
        if st.session_state.connected:
            st.success("🟢 Backend Online")
            
            # Get stats
            stats = get_backend_stats(st.session_state.api_url)
            st.metric("Chunks in DB", stats.get('total_chunks', 0))
            
        else:
            st.warning("🔴 Not Connected")
            st.info("👆 Enter your Colab backend URL above")
        
        st.markdown("---")
        
        # PDF Upload Section
        if st.session_state.connected:
            st.markdown("### 📤 Upload PDF Document")
            
            uploaded_file = st.file_uploader(
                "Choose a PDF file",
                type="pdf",
                help="Upload a PDF document to start chatting with it"
            )
            
            if uploaded_file is not None:
                # Show file info
                file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
                st.write(f"📎 **{uploaded_file.name}**")
                st.write(f"📊 Size: {file_size_mb:.2f} MB")
                
                if file_size_mb > 10:
                    st.error("⚠️ File too large! Max size: 10MB")
                else:
                    if st.button("🔄 Process PDF", type="primary"):
                        process_pdf(uploaded_file)
            
            st.markdown("---")
            
            # Status indicator
            if st.session_state.pdf_uploaded:
                st.markdown("""
                <div style="color: #4CAF50; font-weight: 600;">
                    <span class="status-indicator status-pdf"></span>
                    PDF Ready for Chat
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="color: #FF9800; font-weight: 600;">
                    <span class="status-indicator status-general"></span>
                    No PDF Loaded
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            if st.button("🗑️ Clear Chat History"):
                st.session_state.chat_history = []
                st.rerun()
            
            if st.button("🧹 Clear Backend DB"):
                result = clear_backend_collection(st.session_state.api_url)
                if 'error' not in result:
                    st.session_state.pdf_uploaded = False
                    st.success("Backend cleared!")
                    st.rerun()
    
    # Main chat interface
    if not st.session_state.connected:
        st.info("👈 Please connect to your Colab backend first using the sidebar")
        st.markdown("""
        ### 📝 Setup Instructions:
        1. Open Google Colab
        2. Run the backend code
        3. Copy the ngrok URL
        4. Paste it in the sidebar
        5. Click "Connect"
        """)
    else:
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col2:
            # Chat container
            st.markdown('<div class="chat-container">', unsafe_allow_html=True)
            
            # Display chat history
            if st.session_state.chat_history:
                for message in st.session_state.chat_history:
                    if message["role"] == "user":
                        st.markdown(f"""
                        <div class="user-message">
                            <strong>You:</strong> {message["content"]}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        response_class = "pdf-response" if message.get("type") == "pdf" else "general-response"
                        st.markdown(f"""
                        <div class="bot-message {response_class}">
                            <strong>Assistant:</strong> {message["content"]}
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="text-align: center; padding: 2rem; color: #666;">
                    <h3>👋 Welcome to PDF Chat Assistant</h3>
                    <p>Upload a PDF document and start asking questions about its content!</p>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Chat input
            with st.form(key="chat_form", clear_on_submit=True):
                question = st.text_input(
                    "Ask a question about your PDF...",
                    placeholder="Type your question here...",
                    label_visibility="collapsed"
                )
                submit_button = st.form_submit_button("Send 📤")
            
            if submit_button and question:
                handle_chat(question)

# ========================================
# HELPER FUNCTIONS
# ========================================

def process_pdf(uploaded_file):
    """Process the uploaded PDF file via backend."""
    try:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("📤 Uploading PDF to backend...")
        progress_bar.progress(20)
        
        # Send to backend
        result, status_code = process_pdf_backend(st.session_state.api_url, uploaded_file)
        progress_bar.progress(50)
        
        if status_code == 200 and 'error' not in result:
            status_text.text("✅ PDF processed successfully!")
            progress_bar.progress(100)
            
            st.session_state.pdf_uploaded = True
            
            # Clear progress
            progress_bar.empty()
            status_text.empty()
            
            # Show success
            st.success(f"✅ {result['message']}")
            st.json({
                "Filename": result.get('filename'),
                "Size": f"{result.get('file_size_mb')} MB",
                "Chunks Created": result.get('total_chunks')
            })
            st.balloons()
            
        else:
            progress_bar.empty()
            status_text.empty()
            error_msg = result.get('error', 'Unknown error')
            st.error(f"❌ Error: {error_msg}")
            st.session_state.pdf_uploaded = False
            
    except Exception as e:
        st.error(f"❌ Error processing PDF: {str(e)}")
        st.session_state.pdf_uploaded = False

def handle_chat(question):
    """Handle chat interaction."""
    if not st.session_state.pdf_uploaded:
        st.warning("⚠️ Please upload and process a PDF first!")
        return
    
    # Add user message to history
    st.session_state.chat_history.append({
        "role": "user"
        "content": question
    })
    
    try:
        with st.spinner("🤔 Thinking..."):
            # Get response from backend
            result, status_code = ask_question_backend(st.session_state.api_url, question)
            
            if status_code == 200 and 'error' not in result:
                # Add assistant response to history
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": result.get('answer'),
                    "type": result.get('type', 'general')
                })
            else:
                error_msg = result.get('error', 'Unknown error')
                st.error(f"❌ Error: {error_msg}")
                return
            
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Error generating response: {str(e)}")

if __name__ == "__main__":
    main()