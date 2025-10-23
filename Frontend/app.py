# ========================================
# FINAL WORKING FRONTEND - app.py
# Fixes: Clean updates, no leftover "Assistant:" labels
# ========================================

import streamlit as st
import requests
import time


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
if "last_question" not in st.session_state:
    st.session_state.last_question = None

# ========================================
# BACKEND COMMUNICATION FUNCTIONS
# ========================================

def check_backend_connection(url):
    """Check if backend is accessible."""
    try:
        response = requests.get(f"{url}/", timeout=5)
        if response.status_code == 200:
            return True, response.json()
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
            timeout=300
        )
        return response.json(), response.status_code
    except Exception as e:
        return {"error": str(e)}, 500

def ask_question_backend(api_url, question, top_k=5):
    """Get answer from backend."""
    try:
        data = {"query": question, "top_k": top_k}
        response = requests.post(
            f"{api_url}/answer",
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=90
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
        
        api_url_input = st.text_input(
            "Colab Backend URL",
            value=st.session_state.api_url,
            placeholder="https://xxxx.ngrok-free.app"
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
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("❌ Connection failed")
                else:
                    st.warning("Please enter URL")
        
        with col2:
            if st.button("🔄 Refresh"):
                st.rerun()
        
        st.markdown("---")
        
        if st.session_state.connected:
            st.success("🟢 Backend Online")
            stats = get_backend_stats(st.session_state.api_url)
            st.metric("Chunks", stats.get('total_chunks', 0))
        else:
            st.warning("🔴 Not Connected")
        
        st.markdown("---")
        
        if st.session_state.connected:
            st.markdown("### 📤 Upload PDF")
            
            uploaded_file = st.file_uploader("Choose PDF", type="pdf")
            
            if uploaded_file:
                file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
                st.write(f"📎 {uploaded_file.name}")
                st.write(f"📊 {file_size_mb:.2f} MB")
                
                if file_size_mb <= 50:
                    if st.button("🔄 Process PDF", type="primary"):
                        process_pdf(uploaded_file)
                else:
                    st.error("⚠️ Max: 50MB")
            
            st.markdown("---")
            
            if st.session_state.pdf_uploaded:
                st.success("✅ PDF Ready")
            else:
                st.warning("⚠️ No PDF")
            
            st.markdown("---")
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("🗑️ Clear Chat"):
                    st.session_state.chat_history = []
                    st.session_state.last_question = None
                    st.rerun()
            
            with col_b:
                if st.button("🧹 Clear DB"):
                    clear_backend_collection(st.session_state.api_url)
                    st.session_state.pdf_uploaded = False
                    st.session_state.chat_history = []
                    st.session_state.last_question = None
                    st.success("✅")
                    time.sleep(0.5)
                    st.rerun()
    
    # Main chat interface
    if not st.session_state.connected:
        st.info("👈 Connect to Colab backend first")
        return
    
    # ✅ KEY FIX: Use container for dynamic updates
    chat_container = st.container()
    
    with chat_container:
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
                    # Handle newlines properly
                    content = message["content"].replace("\n", "<br>")
                    st.markdown(f"""
                    <div class="bot-message {response_class}">
                        <strong>Assistant:</strong><br>{content}
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="text-align: center; padding: 2rem; color: #666;">
                <h3>👋 Welcome!</h3>
                <p>Upload a PDF and ask questions</p>
            </div>
            """, unsafe_allow_html=True)
    
    # ✅ Chat input - Simple approach
    st.markdown("---")
    
    col_input, col_button = st.columns([5, 1])
    
    with col_input:
        question = st.text_input(
            "Question",
            key="user_input",
            placeholder="Type your question...",
            label_visibility="collapsed"
        )
    
    with col_button:
        send_clicked = st.button("📤 Send", type="primary", use_container_width=True)
    
    # ✅ Process question when Send is clicked
    if send_clicked and question and question.strip():
        if not st.session_state.pdf_uploaded:
            st.warning("⚠️ Upload PDF first!")
        elif question.strip() != st.session_state.last_question:
            # Only process if it's a new question
            st.session_state.last_question = question.strip()
            handle_chat(question.strip())

# ========================================
# HELPER FUNCTIONS
# ========================================

def process_pdf(uploaded_file):
    """Process PDF via backend."""
    try:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("📤 Uploading...")
        progress_bar.progress(30)
        
        result, status_code = process_pdf_backend(st.session_state.api_url, uploaded_file)
        
        if status_code == 200 and 'error' not in result:
            status_text.text("✅ Complete!")
            progress_bar.progress(100)
            st.session_state.pdf_uploaded = True
            
            time.sleep(1)
            progress_bar.empty()
            status_text.empty()
            
            st.success(f"✅ {result['message']}")
            st.balloons()
            time.sleep(1)
            st.rerun()
        else:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ {result.get('error', 'Error')}")
            
    except Exception as e:
        st.error(f"❌ {str(e)}")

def handle_chat(question):
    """Handle chat interaction - FIXED VERSION."""
    
    # Add user message immediately
    st.session_state.chat_history.append({
        "role": "user",
        "content": question
    })
    
    # ✅ Create placeholder for "thinking" state
    with st.spinner("🤔 Thinking..."):
        try:
            # Get response from backend
            result, status_code = ask_question_backend(
                st.session_state.api_url,
                question,
                top_k=5
            )
            
            if status_code == 200 and 'error' not in result:
                # Add assistant response
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": result.get('answer', 'No response'),
                    "type": result.get('type', 'general')
                })
            else:
                # Add error
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": f"❌ Error: {result.get('error', 'Unknown')}",
                    "type": "error"
                })
        
        except Exception as e:
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": f"❌ Error: {str(e)}",
                "type": "error"
            })
    
    # ✅ Rerun to display the new message
    st.rerun()

if __name__ == "__main__":
    main()