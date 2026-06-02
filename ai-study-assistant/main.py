import streamlit as st
import sqlite3
import io
import hashlib
import time
import re  
import json  
from PyPDF2 import PdfReader
from groq import Groq

# ================= CONFIG & MODERN UI GLASSMORPHISM DECORATION =================
st.set_page_config(
    page_title="Helia AI • Smart Study Workspace",
    page_icon="🧠",
    layout="wide"
)

# Advanced CSS injection for premium SaaS UI/UX look (With Sidebar Conversations View)
st.markdown("""
    <style>
    /* Global App Background & Font Settings */
    .stApp { 
        background: radial-gradient(circle at top right, #111827, #030712); 
        color: #f3f4f6;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Sidebar Overhaul */
    section[data-testid="stSidebar"] { 
        background-color: #0b0f19 !important; 
        border-right: 1px solid #1f2937 !important;
    }
    div[data-testid="stSidebarUserContent"] { padding-top: 1.5rem; }
    
    /* Premium Dashboard Titles */
    div.stMarkdown div[data-testid="stMarkdownContainer"] h1 {
        font-weight: 800;
        letter-spacing: -0.05em;
        background: linear-gradient(to right, #60a5fa, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Custom Card Containers for Results */
    .premium-card {
        background: rgba(17, 24, 39, 0.7);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
    }
    
    /* Elegant Interactive Buttons */
    .stButton>button { 
        width: 100%; 
        border-radius: 10px !important; 
        background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
        color: white !important;
        font-weight: 600 !important;
        border: none !important;
        padding: 12px 24px !important;
        transition: all 0.3s ease-in-out !important;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
    }
    .stButton>button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.4) !important;
        background: linear-gradient(135deg, #3b82f6, #1d4ed8) !important;
    }
    
    /* Secondary Action Buttons (Clear Chat, etc.) */
    div[data-testid="stSidebar"] .stButton>button {
        background: #111827 !important;
        border: 1px solid #374151 !important;
        color: #d1d5db !important;
    }
    div[data-testid="stSidebar"] .stButton>button:hover {
        background: #1f2937 !important;
        border-color: #4b5563 !important;
        color: #ffffff !important;
    }
    
    /* Sidebar Conversation History List Buttons */
    .chat-history-btn>button {
        background: transparent !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        color: #9ca3af !important;
        text-align: left !important;
        padding: 8px 12px !important;
        font-size: 13px !important;
        font-weight: 400 !important;
        border-radius: 8px !important;
        margin-bottom: 5px !important;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .chat-history-btn>button:hover {
        background: rgba(59, 130, 246, 0.1) !important;
        border-color: rgba(59, 130, 246, 0.4) !important;
        color: #60a5fa !important;
        transform: none !important;
        box-shadow: none !important;
    }
    
    /* Inputs Styling */
    .stTextInput input, .stTextArea textarea, .stNumberInput input { 
        background-color: #111827 !important;
        border: 1px solid #374151 !important;
        color: #ffffff !important; 
        border-radius: 10px !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {
        border-color: #3b82f6 !important;
    }
    
    /* Radio Buttons Layout for Interactive Quiz */
    div[data-testid="stRadio"] {
        background: #111827;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #1f2937;
    }
    
    /* Utility Metrics */
    div[data-testid="stMetricValue"] {
        font-size: 36px !important;
        font-weight: 800 !important;
        color: #3b82f6 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ================= INITIALIZE GROQ CLIENT =================
try:
    groq_api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=groq_api_key)
except Exception as e:
    st.error("Groq API Key not found! Please configure it in Streamlit Secrets.")
    st.stop()

# ================= OPTIMIZED MODEL ROUTER =================
MODEL_ROUTER = {
    "Chat": "llama-3.3-70b-versatile",       
    "Summary": "llama-3.3-70b-versatile",    
    "Quiz Maker": "llama-3.3-70b-versatile", 
    "Study Planner": "llama-3.1-8b-instant"  
}

# ================= THREAD-SAFE DATABASE LAYER =================
DB_NAME = "helia.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT UNIQUE,
            password TEXT
        )
        """)
        # Base table template creation
        cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            role TEXT,
            content TEXT
        )
        """)
        
        # SAFE MIGRATION: Catch database layout versioning errors dynamically
        try:
            cur.execute("SELECT session_id FROM messages LIMIT 1")
        except sqlite3.OperationalError:
            # Inject session column if legacy DB architecture structure is discovered
            cur.execute("ALTER TABLE messages ADD COLUMN session_id TEXT")
            
        cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            session_id TEXT UNIQUE,
            username TEXT,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()

init_db()

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# ================= MULTI-SESSION ARCHITECTURE FUNCTIONS =================
def create_new_session(username):
    session_id = f"sess_{int(time.time()*1000)}"
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO chat_sessions (session_id, username, title) VALUES (?, ?, ?)",
            (session_id, username, "New Chat / Yeni Sohbet")
        )
        conn.commit()
    return session_id

def update_session_title(session_id, first_msg):
    try:
        # Use a comprehensive topic title from the initial prompt
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a chat session title generator. Analyze the user's first message and generate a clean, professional, and specific title of maximum 3-4 words. Match the language of the user's message. Output ONLY the title itself, without quotes, punctuation, or any introductory prose."},
                {"role": "user", "content": f"First Message: {first_msg}"}
            ],
            max_tokens=15,
            temperature=0.5
        )
        clean_title = response.choices[0].message.content.strip()
        if not clean_title:
            clean_title = first_msg[:24] + "..." if len(first_msg) > 24 else first_msg
    except Exception:
        # in case of temporary network or API limits failures
        clean_title = first_msg[:24] + "..." if len(first_msg) > 24 else first_msg

    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE chat_sessions SET title=? WHERE session_id=?",
            (clean_title, session_id)
        )
        conn.commit()

def get_user_sessions(username):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT session_id, title FROM chat_sessions WHERE username=? ORDER BY created_at DESC",
            (username,)
        )
        return cur.fetchall()

def save_message(session_id, user, role, content):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO messages (session_id, user, role, content) VALUES (?, ?, ?, ?)",
            (session_id, user, role, content)
        )
        conn.commit()

def get_messages(session_id):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT role, content FROM messages WHERE session_id=? ORDER BY id ASC",
            (session_id,)
        )
        return [{"role": r, "content": c} for r, c in cur.fetchall()]

def delete_session(session_id):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
        cur.execute("DELETE FROM chat_sessions WHERE session_id=?", (session_id,))
        conn.commit()

# ================= ERROR HANDLING HELPER =================
def handle_groq_error(error_obj, UI_placeholder):
    error_msg = str(error_obj)
    UI_placeholder.empty()  
    
    if "429" in error_msg or "rate_limit" in error_msg:
        wait_time = "a few minutes"
        match = re.search(r"try again in (\d+m\d+\.\d+s|\d+m|\d+\.\d+s|\d+s)", error_msg)
        if match:
            try:
                raw_time = match.group(1).split(".")[0]  
                wait_time = raw_time.replace("m", " minute(s) ").replace("s", " second(s)")
            except:
                pass
        
        st.error(f"⏳ **Daily Token Limit Reached!**\n\nHelia AI has reached its API threshold due to high traffic or dense context. The system window will reset in approximately **{wait_time}**. Please take a short break and try again.")
    else:
        st.error(f"⚠️ **API Execution Error:** {error_msg}")

# ================= GLOBAL IDENTITY PROMPT =================
IDENTITY_PROMPT = (
    "CRITICAL IDENTITY, LANGUAGE & EMOTIONAL INTELLIGENCE RULES:\n"
    "1. Your name is Helia AI. You are an advanced study assistant completely created and developed by Helin Gündoğan.\n"
    "2. MANDATORY PRIVACY RULE: Do NOT mention Helin Gündoğan or your development history in regular conversation. "
    "NEVER bring up your creator's name unless the user explicitly asks 'Who created you?', 'Yaratıcın kim?' etc. Keep it completely hidden during standard study assistance.\n"
    "3. Always respond in the language used by the user, but never translate or alter the name 'Helin Gündoğan' when explicitly asked.\n"
    "4. TONALITY & STYLE (BALANCED COMPANION): Do NOT be overly stiff, robotic, or hyper-formal. Avoid corporate phrases like 'Saygılarımla'. "
    "Instead, act like a smart, helpful, polite, and encouraging university study companion. Be clear, professional yet natural, and approachable from the very first message.\n"
    "5. DYNAMIC MIRROWING & HIGH EQ: Actively monitor the user's conversational style. If the user becomes more casual, uses jokes, or feels stressed about exams, instantly match their energy, soften your tone further, and provide empathetic, warm support.\n"
    "6. EMOJI CONSTRAINT: Use emojis very maturely and sparsely (maximum 1 or 2 per response, or none if the context is strictly technical). Never flood the text with emojis.\n"
    "7. TURKISH PERFORMANCE & SYNTAX: When speaking Turkish, you MUST use standard, formal, and non-inverted (kurallı) sentences. "
    "CRITICAL: Keep the verb (yüklem) strictly at the very end of every sentence. Do NOT use inverted sentences. "
    "STRICT LANGUAGE PURITY: Use ONLY native, pure, and accurate Turkish words. Never mix English words into Turkish sentences (e.g., do NOT write 'feelingsini', 'meetinge', etc.). "
    "Avoid hybrid 'Plaza Turkish' completely. Ensure it feels organic and native, avoiding literal translations from English structure. "
    "Never deform words (e.g., ALWAYS write 'diziler', NEVER write 'dizieler').\n"
)

# ================= SESSION STATE & URL PARAMETERS =================
url_user = st.query_params.get("user_session", None)

if "user" not in st.session_state:
    st.session_state.user = url_user

if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""

if "active_feature" not in st.session_state:
    st.session_state.active_feature = None

if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None

# ================= AUTHENTICATION LAYER =================
if st.session_state.user is None:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; font-size: 50px;'>🧠 Helia AI</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #9ca3af; font-size: 16px; margin-top: -10px;'>Your Personal Smart Study Workspace</p>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["🔒 Secure Login", "📝 Create Account"])

        with tab1:
            u = st.text_input("Username", key="login_user", placeholder="Enter your username...")
            p = st.text_input("Password", type="password", key="login_pass", placeholder="Enter your password...")
            remember_me = st.checkbox("Keep me logged in", value=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("Access Workspace", type="primary"):
                with sqlite3.connect(DB_NAME) as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT * FROM users WHERE username=? AND password=?",
                        (u, hash_pw(p))
                    )
                    if cur.fetchone():
                        st.session_state.user = u
                        if remember_me:
                            st.query_params["user_session"] = u
                        st.rerun()
                    else:
                        st.error("Invalid username or password. Please try again.")

        with tab2:
            u2 = st.text_input("Choose Username", key="reg_user", placeholder="Pick a unique username...")
            p2 = st.text_input("Create Password", type="password", key="reg_pass", placeholder="Create a strong password...")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Register Account"):
                try:
                    with sqlite3.connect(DB_NAME) as conn:
                        cur = conn.cursor()
                        cur.execute("INSERT INTO users VALUES (?, ?)", (u2, hash_pw(p2)))
                        conn.commit()
                    st.success("Account created successfully! You can now log in.")
                except:
                    st.error("This username is already taken.")

# ================= MAIN APPLICATION LAYER =================
else:
    if "user_session" not in st.query_params:
        st.query_params["user_session"] = st.session_state.user

    # Establish an initial chat channel session tracking vector if none exists
    if not st.session_state.current_session_id:
        existing_sess = get_user_sessions(st.session_state.user)
        if existing_sess:
            st.session_state.current_session_id = existing_sess[0][0]
        else:
            st.session_state.current_session_id = create_new_session(st.session_state.user)

    # --- SIDEBAR CONTROL CENTER ---
    st.sidebar.markdown("<h2 style='font-size: 24px; font-weight: 800; color: #ffffff;'>⚡ Control Panel</h2>", unsafe_allow_html=True)
    st.sidebar.markdown("---")

    old_menu = st.session_state.get("current_menu", "Chat")
    menu = st.sidebar.selectbox(
        "Select Feature",
        ["Chat", "Summary", "Quiz Maker", "Study Planner"]
    )
    st.session_state.current_menu = menu
    if old_menu != menu:
        st.session_state.active_feature = None

    # --- CHAT HISTORY SECTIONS MANAGER BLOCK (RENDERED ONLY WHEN MENU MATCHES CHAT) ---
    if menu == "Chat":
        st.sidebar.markdown("<br>", unsafe_allow_html=True)
        if st.sidebar.button("➕ New Chat / Yeni Sohbet", type="primary", use_container_width=True):
            st.session_state.current_session_id = create_new_session(st.session_state.user)
            st.rerun()
            
        st.sidebar.markdown("<p style='font-size:12px; font-weight:700; color:#4b5563; margin-bottom:8px; letter-spacing:0.05em;'>RECENT CHATS</p>", unsafe_allow_html=True)
        user_history = get_user_sessions(st.session_state.user)
        
        for s_id, title in user_history:
            prefix = "💬 " if s_id != st.session_state.current_session_id else "🚀 "
            st.sidebar.markdown(f'<div class="chat-history-btn">', unsafe_allow_html=True)
            if st.sidebar.button(f"{prefix}{title}", key=f"nav_{s_id}", use_container_width=True):
                st.session_state.current_session_id = s_id
                st.rerun()
            st.sidebar.markdown('</div>', unsafe_allow_html=True)

    st.sidebar.markdown("<br>", unsafe_allow_html=True)

    # USER-FRIENDLY FILE UPLOADER UI
    file = st.sidebar.file_uploader("📘 Upload Study Material (PDF)", type=["pdf"])

    if file:
        try:
            pdf = io.BytesIO(file.read())
            reader = PdfReader(pdf)
            text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"

            if text.strip() == "":
                st.sidebar.error("Could not read PDF text. Is it a scanned image?")
            else:
                st.session_state.pdf_text = text[:25000]
                st.sidebar.success(f" Ready: {len(st.session_state.pdf_text)} characters")
        except Exception as e:
            st.sidebar.error(f"File Error: {e}")

    # Expandable Advanced Settings
    with st.sidebar.expander("⚙️ Advanced Tuning"):
        temperature = st.slider("Creativity (Temperature)", 0.0, 1.5, 0.3)
        use_pdf = st.toggle("Include PDF document in Chat", value=True)

    # Control Operations
    st.sidebar.markdown("<br><hr>", unsafe_allow_html=True)

    if menu == "Chat":
        if st.sidebar.button("🗑️ Delete Current Chat Thread", type="secondary"):
            delete_session(st.session_state.current_session_id)
            st.session_state.current_session_id = None
            st.sidebar.info("Conversation thread purged.")
            time.sleep(0.4)
            st.rerun()
    else:
        if st.sidebar.button("🔄 Clear System State", type="secondary"):
            st.session_state.active_feature = None
            st.sidebar.info("Operational variables flushed clean.")
            time.sleep(0.4)
            st.rerun()
        
    if st.sidebar.button("🚪 Log Out", type="primary"):
        st.query_params.clear()
        st.session_state.user = None
        st.session_state.pdf_text = ""
        st.session_state.active_feature = None
        st.session_state.current_session_id = None
        st.rerun()

    # Session Status Badge
    st.sidebar.markdown(f"""
        <div style='background-color: #0f172a; padding: 14px; border-radius: 12px; border: 1px solid #1e293b; border-left: 4px solid #2563eb; margin-top: 20px;'>
            <p style='margin: 0; font-size: 11px; color: #3b82f6; font-weight: 800; letter-spacing: 0.05em;'>ACTIVE SESSION</p>
            <p style='margin: 0; font-size: 16px; color: #ffffff; font-weight: 600; margin-top: 2px;'>👤 {st.session_state.user}</p>
        </div>
    """, unsafe_allow_html=True)

    current_model = MODEL_ROUTER[menu]

    # ================= 1. CHAT MODULE (MULTI-SESSION UPDATED) =================
    if menu == "Chat":
        st.markdown("<h1>🧠 Workspace Smart Chat</h1>", unsafe_allow_html=True)
        st.caption("Ask questions, explore academic concepts, or analyze your uploaded document lines.")

        messages = get_messages(st.session_state.current_session_id)
        for msg in messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        prompt = st.chat_input("Type your study question here...")

        if prompt:
            with st.chat_message("user"):
                st.markdown(prompt)
            
            if len(messages) == 0:
                update_session_title(st.session_state.current_session_id, prompt)
                
            save_message(st.session_state.current_session_id, st.session_state.user, "user", prompt)

            pdf_context = st.session_state.pdf_text if use_pdf else ""
            system_prompt = f"{IDENTITY_PROMPT}\nYou are Helia AI, an advanced study assistant. Use markdown formatting.\n\nPDF CONTEXT:\n{pdf_context}"
            full_messages = [{"role": "system", "content": system_prompt}] + get_messages(st.session_state.current_session_id)

            with st.chat_message("assistant"):
                placeholder = st.empty()
                output = ""
                placeholder.markdown("*Thinking...*")

                try:
                    stream = client.chat.completions.create(
                        model=current_model,
                        messages=full_messages,
                        stream=True,
                        temperature=temperature
                    )

                    for chunk in stream:
                        content = chunk.choices[0].delta.content
                        if content:
                            for char in content:
                                output += char
                                placeholder.markdown(output + " ▌")
                                time.sleep(0.002)  

                    placeholder.markdown(output)
                    save_message(st.session_state.current_session_id, st.session_state.user, "assistant", output)
                    
                    if len(messages) == 0:
                        st.rerun()

                except Exception as e:
                    handle_groq_error(e, placeholder)

    # ================= 2. SUMMARY MODULE =================
    elif menu == "Summary":
        st.markdown("<h1>📚 Comprehensive Summary Assistant</h1>", unsafe_allow_html=True)
        st.caption("Extract clear definitions, key themes, and main structures from your document instantly.")

        if not st.session_state.pdf_text:
            st.info("💡 Please upload a study material PDF from the sidebar to activate the Summary assistant.")
        else:
            if st.button("Generate Document Summary", type="primary"):
                st.session_state.active_feature = "summary"

            if st.session_state.active_feature == "summary":
                st.markdown("<br>", unsafe_allow_html=True)
                placeholder = st.empty()
                output = ""
                placeholder.markdown("*Performing deep academic analysis on the document...*")
                try:
                    stream = client.chat.completions.create(
                        model=current_model,
                        messages=[
                            {"role": "system", "content": IDENTITY_PROMPT},
                            {"role": "user", "content": f"""
                            You are an expert academic research assistant. Analyze the following source text deeply and extract a high-fidelity summary.
                            
                            CRITICAL INSTRUCTIONS:
                            1. Structure your output clearly using professional Markdown: Use bold headers for core themes, and clean bullet points for sub-concepts.
                            2. Extract and define all technical jargon, formulas, or key concepts found in the text.
                            3. Avoid generic filler. Capture the exact technical essence and relationships between concepts.
                            
                            SOURCE TEXT TO ANALYZE:
                            {st.session_state.pdf_text}
                            """}
                        ],
                        stream=True
                    )
                    for chunk in stream:
                        content = chunk.choices[0].delta.content
                        if content:
                            output += content
                            placeholder.markdown(output + " ▌")
                    placeholder.markdown(output)
                except Exception as e:
                    handle_groq_error(e, placeholder)

    # ================= 3. QUIZ MAKER MODULE =================
    elif menu == "Quiz Maker":
        st.markdown("<h1>📝 Interactive Quiz Generator</h1>", unsafe_allow_html=True)
        st.caption("Test your knowledge with multiple-choice questions and instant score feedback.")

        if not st.session_state.pdf_text:
            st.info("💡 Please upload a study material PDF from the sidebar to activate the Quiz Generator.")
        else:
            if "quiz_data" not in st.session_state:
                st.session_state.quiz_data = None
            if "user_answers" not in st.session_state:
                st.session_state.user_answers = {}

            with st.container():
                num_questions = st.number_input(
                    "How many questions would you like to generate?",
                    min_value=1,
                    max_value=10,
                    value=3,
                    step=1,
                    key="quiz_num_input"
                )
                st.markdown("<br>", unsafe_allow_html=True)
                generate_btn = st.button("Build My Practice Exam", type="primary")

            if generate_btn:
                placeholder = st.empty()
                placeholder.markdown(f"*Preparing {num_questions} exam questions from the document...*")
                try:
                    response = client.chat.completions.create(
                        model=current_model,
                        response_format={"type": "json_object"},
                        messages=[
                            {"role": "system", "content": "You are a strict exam generator. You must output raw JSON only, matching the exact requested structure. Do not include any conversational prose."},
                            {"role": "user", "content": f"""
                            Create exactly {num_questions} multiple-choice questions based on the text below.
                            Provide the output in this strict JSON format:
                            {{
                                "questions": [
                                    {{
                                        "id": 1,
                                        "question": "Question text here",
                                        "options": ["Option A", "Option B", "Option C", "Option D"],
                                        "answer": "The exact correct option string matching one of the options"
                                    }}
                                ]
                            }}
                            
                            TEXT MATERIAL:
                            {st.session_state.pdf_text}
                            """}
                        ]
                    )
                    
                    st.session_state.quiz_data = json.loads(response.choices[0].message.content)
                    st.session_state.user_answers = {}
                    placeholder.empty()
                except Exception as e:
                    handle_groq_error(e, placeholder)

            if st.session_state.quiz_data and "questions" in st.session_state.quiz_data:
                st.markdown("---")
                score = 0
                total_q = len(st.session_state.quiz_data["questions"])
                
                for q in st.session_state.quiz_data["questions"]:
                    st.markdown(f"""
                        <div class="premium-card">
                            <span style='color: #60a5fa; font-weight: 800; font-size: 14px;'>EXAM QUESTION {q['id']}</span>
                            <h3 style='margin-top: 4px; font-weight: 600;'>{q['question']}</h3>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    user_choice = st.radio(
                        "Choose your answer:",
                        options=q["options"],
                        key=f"q_{q['id']}",
                        index=None,
                        label_visibility="collapsed"
                    )
                    st.session_state.user_answers[q["id"]] = user_choice
                    st.markdown("<br>", unsafe_allow_html=True)

                if st.button("Submit & Verify My Answers", type="secondary"):
                    st.markdown("<h2 style='font-size: 22px;'>📊 Results Summary</h2>", unsafe_allow_html=True)
                    for q in st.session_state.quiz_data["questions"]:
                        ans = st.session_state.user_answers.get(q["id"])
                        if ans == q["answer"]:
                            st.success(f"✅ **Question {q['id']}: Correct!** (Your answer: {ans})")
                            score += 1
                        else:
                            st.error(f"❌ **Question {q['id']}: Incorrect.**\n\n*Your answer:* {ans} | *Correct answer:* {q['answer']}")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.metric(label="Final Score Summary", value=f"{score} / {total_q}", delta=f"{int((score/total_q)*100)}% Success Rate")

    # ================= 4. STUDY PLANNER MODULE =================
    elif menu == "Study Planner":
        st.markdown("<h1>📅 AI Curriculum & Study Planner</h1>", unsafe_allow_html=True)
        st.caption("Break down dense exam materials into clean, step-by-step daily milestones.")

        if not st.session_state.pdf_text:
            st.info("💡 Please upload a study material PDF from the sidebar to align plans with your exact course material.")
        else:
            with st.container():
                days = st.number_input("Days left until your exam:", min_value=1, max_value=365, value=7, key="planner_days_input")
                st.markdown("<br>", unsafe_allow_html=True)
                btn = st.button("Build My Learning Schedule", type="primary")

            if btn:
                st.session_state.active_feature = "planner"

            if st.session_state.active_feature == "planner":
                st.markdown("---")
                placeholder = st.empty()
                output = ""
                placeholder.markdown("*Mapping targets and building calendar...*")
                try:
                    stream = client.chat.completions.create(
                        model=current_model,
                        messages=[
                            {"role": "system", "content": IDENTITY_PROMPT},
                            {"role": "user", "content": f"Design a rigorous {days}-day study plan detailing daily targets and sub-topics from this material:\n{st.session_state.pdf_text}"}
                        ],
                        stream=True
                    )

                    for chunk in stream:
                        content = chunk.choices[0].delta.content
                        if content:
                            output += content
                            placeholder.markdown(output + " ... ▌")

                    placeholder.markdown(output)

                except Exception as e:
                    handle_groq_error(e, placeholder)
                    st.session_state.active_feature = None
