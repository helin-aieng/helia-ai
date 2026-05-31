# 🧠 Helia AI • Advanced Smart Study Workspace

Helia AI is a high-performance, cloud-integrated study workspace designed to transform dense academic materials into structured knowledge. Powered by **Groq's Ultra-Fast LPU Infrastructure** and the latest Open-Source LLMs, it provides seamless document analysis, real-time streaming chat, and intelligent exam preparation tools.

### 🌐 Live Demo: [👉 Click Here to Explore Helia AI](https://helia-ai-ye5zgogz2ld3uy24yywn8e.streamlit.app/)]

---

## 🚀 Core Capabilities
- **🔑 Secure Authentication:** Personalized workspace experience with an isolated SQLite3 database layer and SHA-256 password hashing.
- **💬 Context-Aware AI Chat:** Dynamic conversation engine utilizing a custom context injection layer (up to 25k characters) for document-grounded Q&A.
- **⚡ Real-Time Streaming:** Sub-second response token generation powered by asynchronous chunking to maximize user experience (UX) and eliminate network blocking.
- **📚 Executive Summarizer:** Instant structural breakdown of dense PDF chapters into clean markdown bullet points and core definitions.
- **📝 Automated Quiz Maker:** Generates deep-thinking, multiple-choice assessment questions directly from your source material.
- **📅 Dynamic Curriculum Planner:** Builds optimized, day-by-day customized learning schedules based on remaining exam days.
- **🌙 Premium UI:** Sleek, custom CSS dark-mode interface optimized for late-night study sessions.

---

## 🛠️ Tech Stack & Architecture
- **Frontend & UI:** Streamlit (Custom Dark Theme & Session State Lock Management)
- **AI Orchestration & Cloud Inf:** Groq API (Utilizing state-of-the-art open models)
- **Database Layer:** SQLite3 (Persistent User Access & Cryptographic Password Hashing)
- **File Processing:** PyPDF2 (Binary buffer text parsing)

### 🤖 Intelligent Model Routing Strategy
To optimize response accuracy, reasoning, and generation speed, Helia AI dynamically routes user intents to specific advanced model architectures via Groq:
- **Chat:** `llama-3.1-8b-instant` (Ultra-fast, low-latency, and highly responsive model for fluid conversations)
- **Summary:** `llama-3.3-70b-versatile` (State-of-the-art deep reasoning model for structural text extraction)
- **Quiz Maker:** `llama-3.3-70b-versatile` (High-capacity model optimized for complex, multi-variable logic handling)
- **Study Planner:** `llama-3.3-70b-versatile` (Advanced structural mapping and temporal calendar planning)

---

## 📸 Screenshots

### 🔒 Secure Gateway & Authentication
*(assets/login page1.png)*
*(assets/login page2.png)*

### 💬 Document-Grounded Chat
*(assets/workspace chat.png)*

### 📚 Executive Summaries & Quizzes & Planner
*(assets/summary.png)*
*(assets/quiz generator.png)*
*(assets/study planner.png)*

---

## 📌 Production Roadmap
- [ ] Implement Full Vector Database Integration (ChromaDB/FAISS) for advanced RAG.
- [ ] Add dynamic flashcard generation with space-repetition scheduling.
- [ ] Integrate speech-to-text for audio-driven lecture note parsing.

---

## 👤 Author
**Helia Gündoğan**
Built as a hands-on production-grade AI learning project to master cloud LLM orchestration, secure user state management, and optimized streaming user interfaces.


