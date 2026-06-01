import streamlit as st
import sqlite3
import io
import hashlib
import time
from PyPDF2 import PdfReader
from groq import Groq

# ================= CONFIG (DARK MODE UI DECORATION) =================
st.set_page_config(
    page_title="Helia AI • Smart Study Workspace",
    page_icon="🧠",
    layout="wide"
)

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    section[data-testid="stSidebar"] { background-color: #161b22 !important; }
    div[data-testid="stSidebarUserContent"] { padding-top: 1.5rem; }
    .stButton>button { width: 100%; border-radius: 8px; }
    .stTextInput input, .stTextArea textarea { color: #ffffff !important; }
    h1, h2, h3, p, span, label { color: #ffffff !important; }
    .stCaption p { color: #8b949e !important; }
    </style>
""", unsafe_allow_html=True)

# ================= INITIALIZE GROQ CLIENT =================

try:
    groq_api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=groq_api_key)
except Exception as e:
    st.error("Groq API Key not found! Please configure it in Streamlit Secrets.")
    st.stop()

# ================= MODEL ROUTER =================

MODEL_ROUTER = {
    "Chat": "llama-3.1-8b-instant",
    "Summary": "llama-3.3-70b-versatile",
    "Quiz Maker": "llama-3.3-70b-versatile",
    "Study Planner": "llama-3.3-70b-versatile"
}


# ================= DB (DATABASE LAYER) =================
conn = sqlite3.connect("helia.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT UNIQUE,
    password TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT,
    role TEXT,
    content TEXT
)
""")
conn.commit()


# ================= HELPERS =================
def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


def save_message(user, role, content):
    cur.execute(
        "INSERT INTO messages (user, role, content) VALUES (?, ?, ?)",
        (user, role, content)
    )
    conn.commit()


def get_messages(user):
    cur.execute(
        "SELECT role, content FROM messages WHERE user=? ORDER BY id ASC",
        (user,)
    )
    return [{"role": r, "content": c} for r, c in cur.fetchall()]


def clear_chat(user):
    cur.execute("DELETE FROM messages WHERE user=?", (user,))
    conn.commit()


# ================= GLOBAL IDENTITY PROMPT =================
IDENTITY_PROMPT = (
    "CRITICAL IDENTITY RULES:\n"
    "1. Your name is Helia AI. You are an advanced study assistant.\n"
    "2. You were completely created and developed by Helin Gündoğan.\n"
    "3. You have absolutely NO connection, affiliation, or relationship with any other company, "
    "platform, or website named 'Helia AI' or similar on the internet.\n"
    "4. If the user asks questions like 'Who created you?', 'Who is your creator?', 'Who developed you?', "
    "'Seni kim yarattı?', 'Yaratıcın kim?', '¿Quién te creó?' or ANY identity-related questions in ANY language, "
    "you MUST explicitly and clearly state that you were developed by Helin Gündoğan. Do not credit any other entity.\n"
    "5. Always respond in the language used by the user, but never alter or translate the name 'Helin Gündoğan'.\n"
)


# ================= SESSION STATE =================
if "user" not in st.session_state:
    st.session_state.user = None

if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""

if "active_feature" not in st.session_state:
    st.session_state.active_feature = None

# ================= AUTHENTICATION =================
if st.session_state.user is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; color: white;'>🧠 Helia AI</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #8b949e;'>Your Personal Advanced Study Workspace</p>",
                    unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["🔒 Sign In", "📝 Create Account"])

        with tab1:
            u = st.text_input("Username", key="login_user", placeholder="Enter your username")
            p = st.text_input("Password", type="password", key="login_pass", placeholder="Enter your password")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Login", type="primary"):
                cur.execute(
                    "SELECT * FROM users WHERE username=? AND password=?",
                    (u, hash_pw(p))
                )
                if cur.fetchone():
                    st.session_state.user = u
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

        with tab2:
            u2 = st.text_input("New Username", key="reg_user", placeholder="Choose a unique username")
            p2 = st.text_input("New Password", type="password", key="reg_pass", placeholder="Create a strong password")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Register"):
                try:
                    cur.execute(
                        "INSERT INTO users VALUES (?, ?)",
                        (u2, hash_pw(p2))
                    )
                    conn.commit()
                    st.success("Account created successfully! You can now log in.")
                except:
                    st.error("This username is already taken.")

# ================= MAIN APPLICATION LAYER =================
else:
    if not st.session_state.user:
        st.stop()

    # --- SIDEBAR DESIGN ---
    st.sidebar.markdown("## 🧠 Helia Workspace")
    st.sidebar.markdown("---")

    old_menu = st.session_state.get("current_menu", "Chat")
    menu = st.sidebar.selectbox(
        "Select Feature",
        ["Chat", "Summary", "Quiz Maker", "Study Planner"]
    )
    st.session_state.current_menu = menu
    if old_menu != menu:
        st.session_state.active_feature = None

    st.sidebar.markdown("<br>", unsafe_allow_html=True)

    # PDF UPLOADER
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
                st.sidebar.error("Could not extract text. Scanned PDF?")
            else:
                st.session_state.pdf_text = text[:25000]
                st.sidebar.success(f" Ready: {len(st.session_state.pdf_text)} chars")
        except Exception as e:
            st.sidebar.error(f"PDF Error: {e}")

    # Advanced Settings
    with st.sidebar.expander("⚙️ Advanced Settings"):
        temperature = st.slider("Creativity (Temperature)", 0.0, 1.5, 0.7)
        use_pdf = st.toggle("Feed PDF context to Chat", value=True)

    # --- THE BOTTOM SECTION OF SIDEBAR ---
    st.sidebar.markdown("<br><br><hr>", unsafe_allow_html=True)

    if st.sidebar.button("🔄 New Chat / Clear History", type="secondary"):
        clear_chat(st.session_state.user)
        st.session_state.active_feature = None
        st.sidebar.info("Workspace cleared.")
        time.sleep(0.4)
        st.rerun()

    st.sidebar.markdown(f"""
        <div style='background-color: #1f2937; padding: 10px; border-radius: 8px; border-left: 4px solid #3b82f6; margin-top: 10px;'>
            <p style='margin: 0; font-size: 12px; color: #60a5fa; font-weight: bold;'>ACTIVE SESSION</p>
            <p style='margin: 0; font-size: 15px; color: #ffffff; font-weight: 500;'>👤 {st.session_state.user}</p>
        </div>
    """, unsafe_allow_html=True)

    current_model = MODEL_ROUTER[menu]

    # ================= 1. CHAT MODULE =================
    if menu == "Chat":
        st.title("🧠 Workspace Chat")
        st.caption("Ask questions, explore concepts, or analyze your uploaded document.")

        messages = get_messages(st.session_state.user)
        for msg in messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        prompt = st.chat_input("Type your question here...")

        if prompt:
            with st.chat_message("user"):
                st.markdown(prompt)
            save_message(st.session_state.user, "user", prompt)

            pdf_context = st.session_state.pdf_text if use_pdf else ""
            system_prompt = f"{IDENTITY_PROMPT}\nYou are Helia AI, an advanced study assistant. Use markdown formatting.\n\nPDF CONTEXT:\n{pdf_context}"
            full_messages = [{"role": "system", "content": system_prompt}] + get_messages(st.session_state.user)

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

                    # Typing Effect
                    for chunk in stream:
                        content = chunk.choices[0].delta.content
                        if content:
                            for char in content:
                                output += char
                                placeholder.markdown(output + " ▌")
                                time.sleep(0.005)  

                    placeholder.markdown(output)
                    save_message(st.session_state.user, "assistant", output)

                except Exception as e:
                    st.error(f"Groq streaming error: {e}")

    # ================= 2. SUMMARY MODULE =================
    elif menu == "Summary":
        st.title("📚 Executive Summary Assistant")
        st.caption("Extract key definitions, concepts, and bullet points instantly.")

        if not st.session_state.pdf_text:
            st.info("💡 Please upload a study material PDF from the sidebar to activate the Summary tool.")
        else:
            if st.button("Generate Summary", type="primary"):
                st.session_state.active_feature = "summary"

            if st.session_state.active_feature == "summary":
                placeholder = st.empty()
                output = ""
                placeholder.markdown("*Analyzing document and writing summary...*")
                try:
                    stream = client.chat.completions.create(
                        model=current_model,
                        messages=[
                            {"role": "system", "content": IDENTITY_PROMPT},
                            {"role": "user", "content": f"Provide a comprehensive summary of this text in markdown formats and bullet points:\n{st.session_state.pdf_text}"}
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
                    st.error(f"Error: {e}")

    # ================= 3. QUIZ MAKER MODULE =================
    elif menu == "Quiz Maker":
        st.title("📝 Smart Quiz Generator")
        st.caption("Test your knowledge with custom multi-choice questions generated from your file.")

        if not st.session_state.pdf_text:
            st.info("💡 Please upload a study material PDF from the sidebar to activate the Quiz Maker.")
        else:
            if st.button("Generate Practice Test", type="primary"):
                st.session_state.active_feature = "quiz"

            if st.session_state.active_feature == "quiz":
                placeholder = st.empty()
                output = ""
                placeholder.markdown("*Compiling questions...*")
                try:
                    stream = client.chat.completions.create(
                        model=current_model,
                        messages=[
                            {"role": "system", "content": IDENTITY_PROMPT},
                            {"role": "user", "content": f"Create 5 challenging multiple-choice questions with answers based on this text:\n{st.session_state.pdf_text}"}
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
                    st.error(f"Error: {e}")

    # ================= 4. STUDY PLANNER MODULE =================
    elif menu == "Study Planner":
        st.title("📅 AI Curriculum & Study Planner")
        st.caption("Break down dense material into clear, day-by-day learning schedules.")

        if not st.session_state.pdf_text:
            st.info(
                "💡 Please upload a study material PDF from the sidebar to align plans with your exact course material.")
        else:
            with st.container():
                days = st.number_input("Days left until your exam:", min_value=1, max_value=365, value=7,
                                       key="planner_days_input")
                st.markdown("<br>", unsafe_allow_html=True)
                btn = st.button("Build My Schedule", type="primary")

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
                    st.error(f"Error: {e}")
                    st.session_state.active_feature = None
