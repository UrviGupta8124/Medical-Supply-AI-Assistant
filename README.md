# 🩺 AI Assistant for Medical Facilities
### *Medical Supply Chain & Pharmaceutical Inventory Assistant*

[![Next.js](https://img.shields.io/badge/Next.js-16.0-black?style=flat&logo=next.js)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19.0-61DAFB?style=flat&logo=react)](https://react.dev/)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=flat&logo=flask)](https://flask.palletsprojects.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python)](https://www.python.org/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=flat&logo=sqlite)](https://www.sqlite.org/)
[![Groq](https://img.shields.io/badge/Groq-Llama--3.1--8b-f34f29?style=flat)](https://groq.com/)
[![LangChain](https://img.shields.io/badge/LangChain-FAISS-1C3C3C?style=flat)](https://www.langchain.com/)

A full-stack, grounded conversational AI assistant and real-time dashboard built for pharmaceutical inventory management, 30-day demand forecasting, document Q&A (RAG), and supply chain analytics across hospital medical stores.

---

## 🌟 Key Features

* 💬 **Grounded Conversational AI**: Powered by Groq's `Llama-3.1-8b-instant` with a two-tier routing system. Features a **Keyword Fast-Path** to execute direct SQL queries against SQLite views (bypassing the LLM for zero latency) and a **LangChain Tool-Calling Agent** for dynamic data retrieval.
* 📈 **30-Day Demand Forecasting**: Computes trend-aware rolling consumption rates with Exponential Moving Average (EMA) smoothing to project stockout dates per drug per hospital—cached for 10-minute cycles to optimize performance.
* 📄 **Conversational PDF Q&A (RAG)**: Ingests tender circulars and regulation PDFs via PyPDF, chunks text, embeds chunks using HuggingFace `all-MiniLM-L6-v2`, and queries an in-memory **FAISS** vector store with multi-turn history-aware session memory.
* 📊 **Interactive Recharts Dashboard**: Automatically renders dynamic Bar, Line, and Pie charts inside chat bubbles and dashboard panels based on query intents (e.g., *"plot paracetamol stock"*).
* 🎙️ **Hands-Free Voice Mode**: Integrated Web Speech API (`SpeechRecognition` + `SpeechSynthesis`) supporting continuous listen-process-speak interaction in both English and Hindi (`hi-IN`).
* 🔒 **Secure Administrative Panel**: Protected by credential verification and alphanumeric math CAPTCHAs. Features a full-page grid for live CRUD operations (Create, Read, Update, Delete) on relational DVDMS schemas (`gblt_hospital_mst`, `hstt_drugbrand_mst`, `hstt_inventory_dtl`, `hstt_ratecontract_item_dtl`, `gblt_supplier_mst`).

---

## 🏗️ System Architecture & Tech Stack

The system follows a decoupled N-Tier architecture separating client presentation, REST controllers, AI/RAG services, and data persistence:

| Layer | Technology | Purpose & Description |
| :--- | :--- | :--- |
| **Presentation Layer** | Next.js 16 + React 19 + Recharts | Single-Page Application (SPA) with Glassmorphism UI tokens, chat widget, charts, and admin CRUD grid. |
| **Application Layer** | Python + Flask | REST API controllers in `app.py` managing CORS, custom IP rate limiting, session auth, and route dispatching. |
| **Intelligence Layer** | Groq API + LangChain + FAISS | Intent routing, HuggingFace sentence embeddings (`all-MiniLM-L6-v2`), vector similarity search, and LLM text completion. |
| **Data Layer** | SQLite + SQLAlchemy ORM | Relational tables (`medicines.db`) operating in WAL mode and optimized SQLite Views (`vw_medicine_inventory`, `vw_active_contracts`, `vw_low_stock_alerts`, `vw_ved`). |

---

## 📁 Project Directory Structure

```text
med/ (project root)
│
├── app.py                   # Flask server API, REST endpoints, SQL Agent, RAG & forecasting engines
├── init_db.py               # Database initialization, DVDMS schema creation & SQLite view seeding
├── medicines.db             # SQLite relational database containing inventory, hospital & contract tables
├── defense_protocols.txt    # Unstructured clinical guidelines text store
├── requirements.txt         # Python backend package dependencies
│
├── src/                     # Next.js 16 & React 19 Frontend Source Code
│   └── app/
│       ├── page.tsx         # Main Single-Page App (Chat UI, Recharts dashboard, Admin CRUD grid)
│       ├── layout.tsx       # Root layout wrapper & HTML metadata
│       └── globals.css      # Glassmorphism CSS design system & theme tokens
│
├── public/                  # Public static branding assets and icons
├── package.json             # Node.js frontend dependencies (Next.js, React, Recharts, Lucide-react)
├── tsconfig.json            # TypeScript build configuration
└── next.config.ts           # Next.js framework configuration
```

---

## 🚀 Getting Started & Local Installation

### Prerequisites
* **Python**: `3.10` or higher
* **Node.js**: `18.0` or higher & `npm`
* **C++ Build Tools**: Required for `faiss-cpu` installation on Windows

### 1. Clone the Repository
```bash
git clone https://github.com/UrviGupta8124/Chatbot_Assistant.git
cd Chatbot_Assistant
```

### 2. Install Dependencies
```bash
# Install Python backend requirements
pip install -r requirements.txt

# Install Node.js frontend packages
npm install
```

### 3. Configure Environment Variables
Create a `.env` file in the project root:
```env
GROQ_API_KEY=your_groq_api_key_here
FLASK_ENV=development
```

### 4. Initialize Database
Run the seeding script to create `medicines.db` and populate DVDMS master tables & views:
```bash
python init_db.py
```

### 5. Launch Application Servers

**Terminal 1 (Backend Flask Server):**
```bash
python app.py
# Running on http://localhost:5000
```

**Terminal 2 (Frontend Next.js Client):**
```bash
npm run dev
# Running on http://localhost:3000
```

Open your browser and navigate to **[http://localhost:3000](http://localhost:3000)**!

---

## 📡 REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/chat` | Main conversational endpoint. Executes dynamic SQL views / FAISS RAG and returns LLM replies with Recharts parameters. |
| `GET` | `/api/forecast` | Returns cached 30-day stockout projections per drug/hospital pair. |
| `POST` | `/api/upload-pdf` | Ingests uploaded PDF documents, chunks text, and builds in-memory FAISS vector index. |
| `GET` | `/api/pdf-status` | Checks active PDF session status. |
| `DELETE`| `/api/pdf-clear` | Clears loaded PDF documents and frees session FAISS memory. |
| `GET` | `/api/dashboard` | Retrieves summary counts for inventory, low stock alerts, and contracts. |
| `POST` | `/api/transcribe` | Receives audio recordings from voice mode and transcribes spoken text. |
| `POST` | `/api/login` | Validates officer credentials and initializes session state. |
| `POST` | `/api/signup` | Registers new medical officer credentials into `gblt_officer_mst`. |
| `GET` | `/api/data/<table_name>` | Admin endpoint: lists all rows of an allow-listed table. |
| `POST` | `/api/data/<table_name>` | Admin endpoint: inserts a new record into a table. |
| `PUT` | `/api/data/<table_name>/<row_id>` | Admin endpoint: updates an existing row by ID and invalidates forecast cache. |
| `DELETE`| `/api/data/<table_name>/<row_id>` | Admin endpoint: deletes a row by ID and invalidates forecast cache. |

---

## 🧪 Unit Testing

Run the automated Pytest suite to verify the forecasting engine (rolling-average base, slope extrapolation, EMA smoothing, and stockout date calculations):

```bash
pytest tests/test_forecasting.py -v
```

Output:
```text
============================== 11 passed in 1.23s ==============================
```

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.
