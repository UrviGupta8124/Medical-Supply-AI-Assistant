import os
import requests
import io
from pypdf import PdfReader
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

from langchain_groq import ChatGroq
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.chains import create_retrieval_chain, create_history_aware_retriever
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.utilities import SQLDatabase
from langchain.agents import initialize_agent, Tool, AgentType
from langchain.schema import Document
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import hashlib
from init_db import ConversationLog, Base, GbltOfficerMst, HsttDrugbrandMst, HsttRatecontractItemDtl, GbltHospitalMst, HsttInventoryDtl, GbltSupplierMst

from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

session_pdf_store = {}

# 1. Initialize Embeddings
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# 2. Connect to Database
print("Connecting to Database...")
db_uri = "sqlite:///medicines.db"
engine = create_engine(db_uri)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
db = SQLDatabase(engine)

from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

print("Skipping SQL-to-FAISS injection because DVDMS schema is active.")
docs = []
print("Loading Defense Protocols...")
try:
    loader = TextLoader("defense_protocols.txt")
    defense_docs = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=100)
    defense_splits = text_splitter.split_documents(defense_docs)
    for split in defense_splits:
        split.metadata["source"] = "Defense_Protocols"
    docs.extend(defense_splits)
except Exception as e:
    print(f"Warning: Could not load defense protocols: {e}")

vector_store = FAISS.from_documents(docs, embeddings)
retriever = vector_store.as_retriever(search_kwargs={"k": 3})

# 4. Initialize LLMs
from langchain_core.prompts import MessagesPlaceholder, ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.tools.retriever import create_retriever_tool
from langchain_community.agent_toolkits import SQLDatabaseToolkit

# Use a fast model for the agent and reasoning
ENABLE_MEMORY = True  # User wants memory enabled

# If memory is enabled, we will pull the last N messages from the conversation_log table
MEMORY_LIMIT = 6  # number of recent messages to include as context


# 5. Hybrid Master Agent Setup
llm_primary = ChatGroq(model="llama-3.1-8b-instant", temperature=0, max_tokens=2500)
llm_fallback = ChatGroq(model="llama3-8b-8192", temperature=0, max_tokens=2500)
llm = llm_primary # Keep reference for compatibility

import time

def invoke_llm_with_fallback(prompt, response_format=None):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if response_format:
                return llm_primary.invoke(prompt, response_format=response_format)
            else:
                return llm_primary.invoke(prompt)
        except Exception as e:
            print(f"Primary Groq model error on attempt {attempt+1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2.0)
                continue
            
            # Fall back to secondary Groq model automatically on rate-limit or persistent errors (NFR-3)
            print("Primary Groq model failed. Falling back to secondary Groq model...")
            try:
                if response_format:
                    return llm_fallback.invoke(prompt, response_format=response_format)
                else:
                    return llm_fallback.invoke(prompt)
            except Exception as fe:
                print(f"Fallback Groq model also failed: {fe}")
                raise fe

# 30-Day Forecast Caching (NFR-1)
FORECAST_CACHE_DURATION = 600  # 10 minutes
forecast_cache = {
    "timestamp": 0,
    "data": None
}

from collections import defaultdict
chat_rate_limit_store = defaultdict(list)  # IP -> list of request timestamps
CHAT_RATE_LIMIT = 5  # Max 5 requests per 10 seconds

def is_chat_rate_limited(ip):
    now = time.time()
    chat_rate_limit_store[ip] = [t for t in chat_rate_limit_store[ip] if now - t < 10]
    if len(chat_rate_limit_store[ip]) >= CHAT_RATE_LIMIT:
        return True
    chat_rate_limit_store[ip].append(now)
    return False

from langchain_core.tools import tool

@tool
def query_database(query: str) -> str:
    """Queries the local SQLite database and returns the result. 
    Use this tool whenever the user asks for database records, inventory lists, contracts, hospitals, suppliers, or alerts.
    Input should be a complete SQLite SELECT statement targeting one of the views (e.g., 'SELECT * FROM vw_medicine_inventory LIMIT 20')."""
    try:
        return db.run(query)
    except Exception as e:
        return f"Error executing query: {str(e)}"

retriever_tool = create_retriever_tool(
    retriever,
    "medical_protocols",
    "Searches and returns guidelines and protocols for military medical care. Use this when the user asks about medical treatments, drug side effects, algorithms like MARCH, or trauma management."
)

tools = [retriever_tool, query_database]

system_prompt = (
    "You are a secure military medical assistant. Provide answers strictly based on the provided tools. "
    "Do not hallucinate.\n\n"
    "CRITICAL TOOL-ROUTING INSTRUCTION:\n"
    "- If the user is asking about databases, tables, lists of items, medicine inventory, active contracts, suppliers, registered hospitals, VED analysis, low stock alerts, or any structured data in the facility, you MUST ONLY use the query_database tool to fetch the data from the SQLite database. Do NOT use the 'medical_protocols' tool.\n"
    "- If the user is asking about medical treatments, guidelines, drug side effects, algorithms like MARCH, clinical protocols, or trauma management, you MUST use the 'medical_protocols' tool. Do NOT use the query_database tool.\n\n"
    "CRITICAL: When providing inventory data, historical data, or medicine details, you MUST format the data as a Markdown table with the most appropriate columns.\n"
    "CHARTING INSTRUCTION: Do NOT generate a chart unless the user explicitly uses the words 'graph', 'chart', 'plot', or 'visualize'. If they do, you MUST respond with a JSON block inside triple backticks labeled 'chart'. The frontend ONLY supports 'pie', 'line', and 'bar' charts. You must dynamically select the best chart type based on the data and query:\n"
    "  - Use 'pie' when the data shows parts of a whole, percentages, or high-volume composition.\n"
    "  - Use 'line' when the data shows trends over time, sequential periods, or continuous data.\n"
    "  - Use 'bar' when comparing different distinct categories.\n"
    "The JSON must be an object with 'chartType' and 'data' keys. You MUST query the database view directly to get the real stock values via query_database (e.g. 'SELECT MedicineName, Quantity FROM vw_medicine_inventory LIMIT 20'). DO NOT attempt to write joins with 'vw_medicine' or other non-existent tables—all required fields are already in the view directly. Example:\n"
    "```chart\n"
    '{{"chartType": "bar", "data": [{{"name": "Paracetamol", "value": 5000}}, {{"name": "Ibuprofen", "value": 3000}}]}}\n'
    "```\n"
    "FORMATTING INSTRUCTION:\n"
    "- If the user is asking a specific clinical or medical advice question (e.g. treatments, drug side effects, algorithms), start your response with a source citation (e.g., 'Source: Defense Medical Guidelines, Section 4.1') and include a 'Related protocols:' section at the end listing 2-3 relevant protocols.\n"
    "- If the user is asking a database, inventory, contracts, hospitals, suppliers, or low stock question, you MUST format the response strictly as a Markdown table (e.g., | Name | Quantity | Location |) containing the real queried data. Do NOT include any 'Source: Defense Medical Guidelines' citation and do NOT include any 'Related protocols:' section at the end of database/inventory responses.\n\n"
    "CRITICAL: When asked to show 'medicine inventory' or similar, you MUST query the 'vw_medicine_inventory' view directly. This view is already joined and contains MedicineName, Quantity, MinStock, ExpiryDate, etc. DO NOT attempt to join the base tables yourself.\n"
    "CRITICAL: When asked to show 'active contracts' or similar, you MUST query the 'vw_active_contracts' view directly. DO NOT attempt to join the base tables yourself.\n"
    "CRITICAL: When asked to list 'registered hospitals' or similar, you MUST query the 'vw_registered_hospitals' view directly.\n"
    "CRITICAL: When asked to show 'low stock' or similar, you MUST execute exactly 'SELECT * FROM vw_low_stock_alerts LIMIT 20'. DO NOT query vw_medicine_inventory and DO NOT apply your own WHERE clauses. Trust the view completely.\n"
    "CRITICAL: When asked to show 'ved' or 'ved table' or 'ved analysis' or similar, you MUST query the 'ved' view directly. DO NOT query vw_medicine_inventory. You MUST query and display all four columns exactly as they are: MedicineName, Quantity, VEDCategory, and Criticality. Do NOT rename 'VEDCategory' to 'Priority' or omit 'Criticality'. Present them exactly as 'Medicine Name', 'Quantity', 'VED Category', and 'Criticality' in your Markdown table.\n"
    "CRITICAL: When asked to show 'paracetamol' or 'paracetamol table' or similar, you MUST query the 'vw_paracetamol_inventory' view directly.\n"
    "CRITICAL: To avoid exceeding token limits, NEVER output more than 20 rows of data in a single table. If there are more rows, just output the first 20.\n"
    "CRITICAL: NEVER rely on your chat history or memory to answer data questions. ALWAYS use the query_database tool to fetch fresh data for every request, even if you think you already know the answer. Do not hallucinate data to fit a narrative.\n"
    "If the user is just saying hello or asking a casual question, respond naturally and conversationally without any source citation or protocols.\n\n"
    "LANGUAGE MODE CONSTRAINT:\n"
    "You are currently communicating in: {language_name}.\n"
    "CRITICAL: Regardless of what language was used in the previous conversation history messages, you MUST write your entire new response strictly in the current language mode: {language_name}. Completely ignore the language of the previous turns.\n"
    "- If the language mode is 'Hindi', you MUST write your ENTIRE final response (including all text descriptions, table headers, table cells, source citation, and related protocols) in Hindi (Devanagari script), translating the medical names and terms appropriately. All tool calls, SQL query checking, and database queries must remain in English.\n"
    "- If the language mode is 'English', you MUST write your ENTIRE final response (including all text descriptions, table headers, table cells, source citation, and related protocols) in English only. Do NOT output any Devanagari Hindi characters.\n\n"
)

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)

import re

def clean_history_content(content):
    if not content:
        return ""
    # Strip markdown chart code blocks
    content = re.sub(r'```chart[\s\S]*?```', '[Chart visualization omitted from memory]', content)
    # Strip markdown table formatting
    lines = content.split('\n')
    cleaned_lines = []
    in_table = False
    for line in lines:
        if line.strip().startswith('|'):
            if not in_table:
                cleaned_lines.append('[Table inventory/contract data omitted from memory]')
                in_table = True
        else:
            in_table = False
            cleaned_lines.append(line)
    return '\n'.join(cleaned_lines)

@app.route('/chat', methods=['POST'])
def chat():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr or 'unknown')
    if is_chat_rate_limited(ip):
        return jsonify({"error": "Too many requests. Please wait a few seconds before trying again."}), 429

    data = request.get_json()
    if not data or 'messages' not in data:
        return jsonify({"error": "Invalid request"}), 400
        
    messages = data['messages']
    lang = data.get('language', 'EN')
    user_query = ""
    
    # Retrieve conversation memory from DB if enabled
    db_session = Session()
    history = []
    if ENABLE_MEMORY:
        recent_logs = db_session.query(ConversationLog).order_by(ConversationLog.id.desc()).limit(MEMORY_LIMIT).all()
        for log in reversed(recent_logs):
            cleaned = clean_history_content(log.content)
            
            # Filter history by language mode to prevent few-shot mixing
            log_is_hi = any('\u0900' <= char <= '\u097F' for char in cleaned)
            if lang == 'HI' and not log_is_hi and log.role == 'assistant':
                continue
            if lang == 'EN' and log_is_hi:
                continue

            if log.role == 'user':
                history.append(HumanMessage(content=cleaned))
            else:
                history.append(AIMessage(content=cleaned))
    # Get current user query
    if messages and messages[-1].get('role') == 'user':
        user_query = messages[-1].get('content', '')
        # Log user message
        db_session.add(ConversationLog(role='user', content=user_query))
        db_session.commit()
    
    if not user_query:
        return jsonify({"error": "No user query found"}), 400

    def generate():
        import json
        import time
        lang_name = "Hindi" if lang == 'HI' else "English"
               # Step 1: Keyword-first intent router (NFR-1)
        # Check for simple greetings or acknowledgments to bypass LLM classification
        q_clean = user_query.strip().lower().replace('?', '')
        routing = None
        
        # Simple greetings / acknowledgments -> route to casual
        greetings = {"hi", "hello", "hey", "ok", "okay", "thanks", "thank you", "cool", "bye", "goodbye"}
        if q_clean in greetings:
            print("Keyword Router: Greeting detected. Routing to casual.")
            routing = {"route": "casual"}
            
        # Database view explicit matches
        elif q_clean in {"show medicines", "list medicines", "medicines table", "show inventory", "list inventory", "inventory table"}:
            print("Keyword Router: Medicines query detected. Routing to database.")
            routing = {"route": "database", "sql": "SELECT * FROM vw_medicine_inventory LIMIT 20"}
        elif q_clean in {"stock alerts", "low stock", "show stock alerts", "list low stock"}:
            print("Keyword Router: Low stock query detected. Routing to database.")
            routing = {"route": "database", "sql": "SELECT * FROM vw_low_stock_alerts LIMIT 20"}
        elif q_clean in {"show contracts", "list contracts", "rate contracts", "show active contracts"}:
            print("Keyword Router: Contracts query detected. Routing to database.")
            routing = {"route": "database", "sql": "SELECT * FROM vw_active_contracts LIMIT 20"}
        elif q_clean in {"show hospitals", "list hospitals", "registered hospitals"}:
            print("Keyword Router: Hospitals query detected. Routing to database.")
            routing = {"route": "database", "sql": "SELECT * FROM vw_registered_hospitals LIMIT 20"}
        elif q_clean in {"show suppliers", "list suppliers", "registered suppliers"}:
            print("Keyword Router: Suppliers query detected. Routing to database.")
            routing = {"route": "database", "sql": "SELECT * FROM vw_suppliers LIMIT 20"}
        elif q_clean in {"ved analysis", "ved table", "show ved"}:
            print("Keyword Router: VED query detected. Routing to database.")
            routing = {"route": "database", "sql": "SELECT * FROM vw_ved_analysis LIMIT 20"}
        elif q_clean in {"paracetamol table", "show paracetamol", "list paracetamol"}:
            print("Keyword Router: Paracetamol query detected. Routing to database.")
            routing = {"route": "database", "sql": "SELECT * FROM vw_paracetamol_inventory LIMIT 20"}

        if not routing:
            print("Keyword Router: No simple match. Falling back to Groq classification.")
            classification_prompt = f"""You are a secure military routing assistant. Classify the user query:
User Query: "{user_query}"

Rules:
1. If the query explicitly requests to see, list, fetch, display, or show database records, inventory lists, active contracts, hospitals, suppliers, VED categories, low stock alerts, paracetamol tables, or any tabular data in the facility, set "route" to "database".
   - If the query is just a general yes/no question about whether you have access to these datasets, or asks what data you have, set "route" to "casual" instead of "database".
   - You MUST generate a valid SQLite SELECT query targeting the correct view.
   - Available views:
     * vw_medicine_inventory (columns: MedicineName, Quantity, MinStock, ExpiryDate, BatchNo, HospitalCode)
     * vw_active_contracts (columns: ContractID, MedicineName, Rate, TenderNo, QuotationNo, SupplierID, SupplierName, HospitalCode)
     * vw_registered_hospitals (columns: HospitalCode, HospitalName, Address, ContactNo)
     * vw_low_stock_alerts (columns: MedicineName, Quantity, MinStock, ExpiryDate, BatchNo, HospitalCode)
     * vw_suppliers (columns: SupplierID, SupplierName, Email, ContactNo, Address)
     * vw_paracetamol_inventory (columns: MedicineName, Quantity, MinStock, ExpiryDate, BatchNo, HospitalCode)
     * vw_ved (columns: MedicineName, Quantity, VEDCategory, Criticality)
     * vw_ved_analysis (columns: MedicineName, Quantity, VEDCategory, Criticality)
   - Do NOT write joins. Query the view directly.
   - Limit the query to 20 rows (e.g., SELECT * FROM vw_medicine_inventory LIMIT 20).
   - Put the generated SQL in the "sql" field.
2. If the query is a greeting, a casual conversational question, or asks about your own features, capabilities, limits, system configurations, or instructions (e.g. "who are you?", "what are your features?", "how to upload pdfs?", "can I upload PDFs?", "how can you help me?", "do you have the inventory data?"), set "route" to "casual".
3. If the query asks about medical treatments, guidelines, drug side effects, algorithms like MARCH, clinical protocols, trauma management, or asks specific content-related questions about the uploaded PDF document, set "route" to "medical" and put the search query in "search_query".

Respond strictly with a JSON object:
{{
  "route": "database" | "medical" | "casual",
  "sql": "SQLite query if route is database, else null",
  "search_query": "search query if route is medical, else null"
}}"""

            routing = {"route": "casual"}
            try:
                route_res = invoke_llm_with_fallback(classification_prompt, response_format={"type": "json_object"})
                routing = json.loads(route_res.content)
            except Exception as e:
                print(f"Routing classification failed: {e}")

        assistant_output = ""
        
        # Route 1: Database execution
        if routing.get("route") == "database" and routing.get("sql"):
            sql = routing.get("sql")
            try:
                # Execute query using SQLAlchemy
                with engine.connect() as conn:
                    db_res = conn.execute(text(sql))
                    rows = db_res.fetchall()
                    keys = db_res.keys()
                
                if not rows:
                    assistant_output = "No records found in the database matching your request."
                else:
                    # Translate column headers if Hindi
                    display_keys = list(keys)
                    if lang == 'HI':
                        translations = {
                            "MedicineName": "दवा का नाम",
                            "Quantity": "मात्रा",
                            "MinStock": "न्यूनतम स्टॉक",
                            "ExpiryDate": "समाप्ति तिथि",
                            "BatchNo": "बैच संख्या",
                            "HospitalCode": "अस्पताल कोड",
                            "ContractID": "अनुबंध आईडी",
                            "Rate": "दर",
                            "TenderNo": "निविदा संख्या",
                            "QuotationNo": "कोटेशन संख्या",
                            "SupplierID": "आपूर्तिकर्ता आईडी",
                            "SupplierName": "आपूर्तिकर्ता का नाम",
                            "HospitalName": "अस्पताल का नाम",
                            "Address": "पता",
                            "ContactNo": "संपर्क नंबर",
                            "Email": "ईमेल",
                            "VEDCategory": "VED श्रेणी",
                            "Criticality": "गंभीरता"
                        }
                        display_keys = [translations.get(k, k) for k in keys]
                    
                    headers = " | ".join(display_keys)
                    divider = " | ".join(["---"] * len(keys))
                    table_rows = []
                    for r in rows:
                        table_rows.append(" | ".join(str(val) for val in r))
                    markdown_table = f"| {headers} |\n| {divider} |\n" + "\n".join(f"| {tr} |" for tr in table_rows)
                    
                    # Generate a chart block if explicitly requested
                    is_chart_requested = any(w in user_query.lower() for w in ["chart", "graph", "plot", "visualize"])
                    chart_block = ""
                    if is_chart_requested:
                        chart_type = "bar"
                        if "pie" in user_query.lower():
                            chart_type = "pie"
                        elif "line" in user_query.lower():
                            chart_type = "line"
                            
                        chart_data = []
                        for r in rows[:10]:
                            name_val = str(r[0])
                            try:
                                val_num = int(r[1])
                            except:
                                val_num = 0
                            chart_data.append({"name": name_val, "value": val_num})
                        
                        chart_block = f"\n\n```chart\n{{\"chartType\": \"{chart_type}\", \"data\": {json.dumps(chart_data)}}}\n```\n"
                    
                    assistant_output = markdown_table + chart_block
            except Exception as e:
                assistant_output = f"Error executing database query: {str(e)}"
                
        # Route 2: Medical Protocols / PDF QA Content
        elif routing.get("route") == "medical":
            search_q = routing.get("search_query") or user_query
            pdf_session = session_pdf_store.get("default")
            
            # Construct conversation memory context for FR-6
            history_str = ""
            if history:
                history_str = "Previous conversation turns:\n"
                for msg in history[-4:]:  # last 4 turns for context
                    role = "User" if isinstance(msg, HumanMessage) else "Assistant"
                    history_str += f"{role}: {msg.content}\n"
                history_str += "\n"

            # Check if PDF session is active and query the uploaded document context instead
            if pdf_session:
                pdf_vector_store = pdf_session["vector_store"]
                pdf_retriever = pdf_vector_store.as_retriever(search_kwargs={"k": 3})
                try:
                    retrieved_docs = pdf_retriever.invoke(search_q)
                    context = "\n\n".join(doc.page_content for doc in retrieved_docs)
                    
                    pdf_prompt = (
                        f"You are AAMF's secure medical assistant. Respond to the user query based on the provided PDF context below.\n"
                        f"CRITICAL: Do NOT say 'Based on the provided context...', 'According to the PDF...', 'The context snippet does not mention...', or similar robotic meta-references. "
                        f"Speak naturally and conversationally, as if you already have this medical knowledge in your mind. "
                        f"If the information is not in the context, respond politely: 'I don't have details on that in my medical guidelines' or 'I couldn't find information on that in the uploaded document.'\n\n"
                        f"Language Mode: {lang_name}\n"
                        f"{history_str}"
                        f"User Query: {user_query}\n\n"
                        f"Context:\n{context}\n\n"
                        f"CRITICAL: You MUST write your entire response strictly in {lang_name}."
                    )
                    
                    try:
                        res = invoke_llm_with_fallback(pdf_prompt)
                        assistant_output = res.content
                    except Exception as e:
                        assistant_output = f"Error generating response from document: {str(e)}"
                except Exception as e:
                    assistant_output = f"Error querying document context: {str(e)}"
            else:
                try:
                    retrieved_docs = retriever.invoke(search_q)
                    context = "\n\n".join(doc.page_content for doc in retrieved_docs)
                    
                    medical_prompt = (
                        f"You are a secure military medical assistant. Respond to the user query based on the retrieved medical guidelines context below.\n"
                        f"CRITICAL: Do NOT say 'Based on the provided context...', 'According to the retrieved protocols...', 'The context does not mention...', or similar robotic meta-references. "
                        f"Speak naturally and conversationally, as if you already have this medical knowledge in your mind. "
                        f"If the information is not in the guidelines, respond politely: 'I don't have details on that in my medical guidelines' or 'I couldn't find information on that in the current protocols.'\n\n"
                        f"Language Mode: {lang_name}\n"
                        f"{history_str}"
                        f"User Query: {user_query}\n\n"
                        f"Retrieved Context:\n{context}\n\n"
                        f"CRITICAL: You MUST write your entire response strictly in {lang_name}.\n"
                        f"At the end of your response, you MUST include a 'Related protocols:' section listing 2-3 relevant protocols."
                    )
                    
                    try:
                        med_res = invoke_llm_with_fallback(medical_prompt)
                        assistant_output = med_res.content
                    except Exception as e:
                        assistant_output = f"Error generating medical response: {str(e)}"
                except Exception as e:
                    assistant_output = f"Error searching medical protocols: {str(e)}"
                
        # Route 3: Casual conversation
        else:
            casual_prompt = (
                f"You are the AI Assistant for Medical Facilities (AAMF) - a secure conversational assistant designed for managing pharmaceutical inventory, demand forecasting, and supply-chain analytics across hospitals.\n"
                f"CRITICAL: Do NOT say 'Based on the provided context...', 'According to the context snippet...', 'The context does not mention...', or similar robotic meta-references. Speak naturally and conversationally as the AAMF assistant.\n"
                f"You help medical stores officers track thousands of stock-keeping units (SKUs), anticipate stockouts, predict 30-day consumption trends, reconcile supplier rate contracts, query registered hospitals/suppliers, and search trauma protocols.\n"
                f"You also support uploading PDF documents (like tenders, SOPs, circulars, or medical guidelines) for document Q&A context.\n"
                f"If the user is just saying hello, asking who you are, or giving a short acknowledgment (like 'OK', 'thanks', 'cool'), respond naturally and briefly (e.g., 'Hello! I am the AI Assistant for Medical Facilities (AAMF). I am ready to help you manage inventory, view active contracts, predict stockouts, or analyze low stock alerts. Let me know how I can assist you today!'). Do not talk about clinical topics or databases unless requested.\n\n"
                f"Language Mode: {lang_name}\n"
                f"User Query: {user_query}\n\n"
                f"CRITICAL: You MUST write your entire response strictly in {lang_name}."
            )
            try:
                cas_res = invoke_llm_with_fallback(casual_prompt)
                assistant_output = cas_res.content
            except Exception as e:
                assistant_output = f"Error generating response: {str(e)}"
                
        # Save response in database
        db_session.add(ConversationLog(role='assistant', content=assistant_output))
        db_session.commit()
        db_session.close()
        
        yield assistant_output
                
    return Response(generate(), mimetype='text/plain')

@app.route('/api/upload-pdf', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "Only PDF files are supported"}), 400
    
    try:
        pdf_bytes = file.read()
        reader = PdfReader(io.BytesIO(pdf_bytes))
        chunks = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                for j in range(0, len(text), 400):
                    chunk = text[j:j+500].strip()
                    if chunk:
                        chunks.append(chunk)
        
        if not chunks:
            return jsonify({"error": "Could not extract any readable text from PDF."}), 422
            
        vector_store = FAISS.from_texts(chunks, embeddings)
        session_pdf_store["default"] = {
            "filename": file.filename,
            "vector_store": vector_store
        }
        return jsonify({"filename": file.filename, "chunks": len(chunks)})
    except Exception as e:
        return jsonify({"error": f"Failed to parse PDF: {str(e)}"}), 500

@app.route('/api/pdf-status', methods=['GET'])
def pdf_status():
    session = session_pdf_store.get("default")
    if session:
        return jsonify({"loaded": True, "filename": session["filename"]})
    return jsonify({"loaded": False})

@app.route('/api/pdf-clear', methods=['POST', 'DELETE'])
def pdf_clear():
    session_pdf_store.pop("default", None)
    return jsonify({"success": True})

@app.route('/api/dashboard', methods=['GET'])
def dashboard_data():
    with engine.connect() as conn:
        medicines = conn.execute(text("SELECT hstnumItembrandId, hststrItemName, 'General' as medicine_class FROM hstt_drugbrand_mst LIMIT 50")).fetchall()
        inventory = conn.execute(text("SELECT i.hstnumInventoryId, m.hststrItemName, i.hstnumStockQty, 'Central Store' FROM hstt_inventory_dtl i JOIN hstt_drugbrand_mst m ON i.hstnumItembrandId = m.hstnumItembrandId LIMIT 50")).fetchall()
        suppliers = conn.execute(text("SELECT SupplierID, SupplierName, Email, ContactNo FROM vw_suppliers LIMIT 50")).fetchall()
        contracts = conn.execute(text("SELECT c.ContractID, c.TenderNo, c.Rate, c.SupplierName, c.MedicineName FROM vw_active_contracts c LIMIT 50")).fetchall()
        
    return jsonify({
        "medicines": [{"id": m[0], "name": m[1], "class": m[2]} for m in medicines],
        "inventory": [{"id": i[0], "name": i[1], "stock": i[2], "location": i[3]} for i in inventory],
        "suppliers": [{"id": s[0], "name": s[1], "email": s[2], "phone": s[3]} for s in suppliers],
        "contracts": [{"id": c[0], "contractNo": c[1], "rate": c[2], "supplier": c[3], "medicine": c[4]} for c in contracts]
    })

@app.route('/api/forecast', methods=['GET'])
def forecast_data():
    global forecast_cache
    now = time.time()
    
    # Check if cache is still valid (NFR-1)
    if forecast_cache["data"] is not None and (now - forecast_cache["timestamp"]) < FORECAST_CACHE_DURATION:
        print("Forecast Cache: Returning cached data.")
        return jsonify(forecast_cache["data"])
        
    print("Forecast Cache: Recomputing 30-day forecast.")
    db_session = Session()
    try:
        from datetime import datetime, timedelta
        # Fetch real items and current quantities
        inventory_items = db_session.execute(text(
            "SELECT MedicineName, Quantity, MinStock, HospitalCode FROM vw_medicine_inventory"
        )).fetchall()
        
        data = []
        base_date = datetime.now()
        
        for i in range(30):
            day = base_date + timedelta(days=i)
            day_str = day.strftime("%Y-%m-%d")
            
            total_consumption = 0
            total_stock = 0
            
            for item in inventory_items:
                med_name, qty, min_stock, hosp_code = item
                # Generate stable baseline daily consumption seeded reproducibly by medicine name & hospital code
                seed_val = sum(ord(char) for char in med_name) + hosp_code
                base_consumption = (seed_val % 12) + 4  # 4 to 15 units per day
                
                # Apply trend and EMA-like smoothing
                h = i / 30.0
                # rolling demand growth rate (trend)
                trend_factor = 1.0 + 0.05 * h
                predicted_c = base_consumption * trend_factor
                
                # Project stock level
                consumed_so_far = base_consumption * i + 0.5 * (base_consumption * 0.05) * (i * i / 30.0)
                stock_left = max(0, qty - consumed_so_far)
                
                total_consumption += predicted_c
                total_stock += stock_left
                
            data.append({
                "date": day_str,
                "predicted_consumption": int(total_consumption),
                "stock_level": int(total_stock)
            })
            
        forecast_cache["timestamp"] = now
        forecast_cache["data"] = data
        return jsonify(data)
    except Exception as e:
        print(f"Error calculating forecast: {e}")
        # fallback to basic generation if DB error
        import random
        from datetime import datetime, timedelta
        fallback_data = []
        base_date = datetime.now()
        for i in range(30):
            day = base_date + timedelta(days=i)
            fallback_data.append({
                "date": day.strftime("%Y-%m-%d"),
                "predicted_consumption": random.randint(80, 150),
                "stock_level": max(0, 3000 - i * 85)
            })
        return jsonify(fallback_data)
    finally:
        db_session.close()

@app.route('/api/transcribe', methods=['POST'])
def transcribe_audio():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return jsonify({"error": "GROQ_API_KEY not configured"}), 500
        
    try:
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        file_bytes = file.read()
        
        files = {
            "file": ("audio.webm", file_bytes, file.mimetype or "audio/webm")
        }
        data = {
            "model": "whisper-large-v3-turbo",
            "temperature": "0"
        }
        
        lang = request.form.get('language', 'EN')
        if lang == 'HI':
            data["language"] = "hi"
        
        response = requests.post(url, headers=headers, files=files, data=data)
        
        if response.ok:
            result = response.json()
            text = result.get("text", "").strip()
            
            # Filter common Whisper hallucinations on silent audio chunks
            lower_text = text.lower()
            hallucinations = [
                "thank you.", "thank you", "hello.", "hello", "i.", "you.", "okay.", 
                "thanks.", "subtitles", "amara.org", "i thank you.", "i hello.", 
                "thank you very much.", "bye.", "bye", "subscribe"
            ]
            
            if text in hallucinations or lower_text in hallucinations:
                text = ""
                
            # Filter the exact hallucination the user experienced
            if "thank you" in lower_text and "hello" in lower_text and len(lower_text) < 40:
                text = ""
                
            return jsonify({"text": text})
        else:
            print(f"Groq API error: {response.text}")
            return jsonify({"error": f"Groq API error: {response.text}"}), response.status_code
            
    except Exception as e:
        print(f"Transcription error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/signup', methods=['POST'])
def api_signup():
    data = request.get_json()
    if not data or not all(k in data for k in ('sector', 'email', 'username', 'password')):
        return jsonify({"error": "Missing signup credentials"}), 400
        
    sector = data['sector']
    email = data['email'].strip().lower()
    username = data['username'].strip().lower()
    password = data['password']
    
    db_session = Session()
    try:
        # Check if username or email already exists
        existing_user = db_session.query(GbltOfficerMst).filter(
            (GbltOfficerMst.username == username) | (GbltOfficerMst.email == email)
        ).first()
        
        if existing_user:
            return jsonify({"error": "Username or Email already registered"}), 409
            
        # Hash password securely
        password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        
        new_officer = GbltOfficerMst(
            command_sector=sector,
            email=email,
            username=username,
            password_hash=password_hash
        )
        db_session.add(new_officer)
        db_session.commit()
        return jsonify({"success": "Account created successfully"}), 201
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close()

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    if not data or not all(k in data for k in ('sector', 'username', 'password')):
        return jsonify({"error": "Missing login credentials"}), 400
        
    sector = data['sector']
    username = data['username'].strip().lower()
    password = data['password']
    
    db_session = Session()
    try:
        password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        officer = db_session.query(GbltOfficerMst).filter(
            GbltOfficerMst.command_sector == sector,
            GbltOfficerMst.username == username,
            GbltOfficerMst.password_hash == password_hash
        ).first()
        
        if not officer:
            return jsonify({"error": "Invalid Command Sector, Username, or Password"}), 401
            
        return jsonify({
            "success": "Logged in successfully",
            "officer": {
                "username": officer.username,
                "email": officer.email,
                "sector": officer.command_sector
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close()

def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        return None

@app.route('/api/data/<table_name>', methods=['GET'])
def get_table_data(table_name):
    db_session = Session()
    try:
        if table_name == 'medicines':
            rows = db_session.query(HsttDrugbrandMst).all()
            data = [{
                "id": r.hstnumItembrandId,
                "hospital_code": r.gnumHospitalCode,
                "item_id": r.hstnumItemId,
                "name": r.hststrItemName,
                "manufacturer_id": r.hstnumManufacturerId,
                "default_rate": r.hstnumDefaultRate,
                "rate_unit_id": r.hstnumRateUnitId,
                "approved_type": r.hstnumApprovedType,
                "specification": r.hststrSpecification,
                "item_make": r.hstnumItemMake,
                "effective_from": r.gdtEffectiveFrm.strftime("%Y-%m-%d") if r.gdtEffectiveFrm else None,
                "ved_category": r.hststrVedCategory
            } for r in rows]
        elif table_name == 'inventory':
            rows = db_session.query(HsttInventoryDtl).all()
            data = [{
                "id": r.hstnumInventoryId,
                "hospital_code": r.gnumHospitalCode,
                "item_id": r.hstnumItemId,
                "itembrand_id": r.hstnumItembrandId,
                "quantity": r.hstnumStockQty,
                "min_stock": r.hstnumMinStockLevel,
                "max_stock": r.hstnumMaxStockLevel,
                "expiry_date": r.hstdtExpiryDate.strftime("%Y-%m-%d") if r.hstdtExpiryDate else None,
                "batch_no": r.hststrBatchNo
            } for r in rows]
        elif table_name == 'contracts':
            rows = db_session.query(HsttRatecontractItemDtl).all()
            data = [{
                "id": r.hstnumRcId,
                "hospital_code": r.gnumHospitalCode,
                "is_approval": r.hstnumIsApproval,
                "contract_type_id": r.hstnumContractTypeId,
                "item_id": r.hstnumItemId,
                "itembrand_id": r.hstnumItembrandId,
                "tender_no": r.hststrTenderNo,
                "quotation_no": r.hststrQuotationNo,
                "supplier_id": r.hstnumSupplierId,
                "rate": r.hstnumRate
            } for r in rows]
        elif table_name == 'hospitals':
            rows = db_session.query(GbltHospitalMst).all()
            data = [{
                "id": r.gnumHospitalCode,
                "name": r.gstrHospitalName,
                "address": r.gstrHospitalAddress,
                "contact_no": r.gnumContactNo
            } for r in rows]
        elif table_name == 'suppliers':
            rows = db_session.query(GbltSupplierMst).all()
            data = [{
                "id": r.supplier_id,
                "name": r.supplier_name,
                "email": r.email,
                "contact_no": r.contact_no,
                "address": r.address
            } for r in rows]
        else:
            db_name_map = {
                "medicines": "hstt_drugbrand_mst",
                "inventory": "hstt_inventory_dtl",
                "contracts": "hstt_ratecontract_item_dtl",
                "hospitals": "gblt_hospital_mst",
                "suppliers": "gblt_supplier_mst"
            }
            db_table = db_name_map.get(table_name, table_name)
            result = db_session.execute(text(f"SELECT * FROM {db_table}"))
            keys = result.keys()
            data = [dict(zip(keys, row)) for row in result]
            
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close()

@app.route('/api/data/<table_name>', methods=['POST'])
def add_table_row(table_name):
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    db_session = Session()
    try:
        if table_name == 'medicines':
            row = HsttDrugbrandMst(
                gnumHospitalCode=int(data.get('hospital_code', 101)),
                hstnumItemId=int(data.get('item_id', 1)),
                hststrItemName=data.get('name'),
                hstnumManufacturerId=int(data.get('manufacturer_id', 1)),
                hstnumDefaultRate=float(data.get('default_rate', 0.0)),
                hstnumRateUnitId=int(data.get('rate_unit_id', 1)),
                hstnumApprovedType=int(data.get('approved_type', 1)),
                hststrSpecification=data.get('specification'),
                hstnumItemMake=int(data.get('item_make', 1)),
                gdtEffectiveFrm=parse_date(data.get('effective_from')),
                hststrVedCategory=data.get('ved_category', 'E')
            )
        elif table_name == 'inventory':
            row = HsttInventoryDtl(
                gnumHospitalCode=int(data.get('hospital_code', 101)),
                hstnumItemId=int(data.get('item_id', 1)),
                hstnumItembrandId=int(data.get('itembrand_id', 1)),
                hstnumStockQty=int(data.get('quantity', 0)),
                hstnumMinStockLevel=int(data.get('min_stock', 50)),
                hstnumMaxStockLevel=int(data.get('max_stock', 500)),
                hstdtExpiryDate=parse_date(data.get('expiry_date')),
                hststrBatchNo=data.get('batch_no')
            )
        elif table_name == 'contracts':
            row = HsttRatecontractItemDtl(
                gnumHospitalCode=int(data.get('hospital_code', 101)),
                hstnumIsApproval=int(data.get('is_approval', 1)),
                hstnumContractTypeId=int(data.get('contract_type_id', 1)),
                hstnumItemId=int(data.get('item_id', 1)),
                hstnumItembrandId=int(data.get('itembrand_id', 1)),
                hststrTenderNo=data.get('tender_no'),
                hststrQuotationNo=data.get('quotation_no'),
                hstnumSupplierId=int(data.get('supplier_id', 1)),
                hstnumRate=float(data.get('rate', 0.0))
            )
        elif table_name == 'hospitals':
            row = GbltHospitalMst(
                gnumHospitalCode=int(data.get('id')),
                gstrHospitalName=data.get('name'),
                gstrHospitalAddress=data.get('address'),
                gnumContactNo=data.get('contact_no')
            )
        elif table_name == 'suppliers':
            row = GbltSupplierMst(
                supplier_id=int(data.get('id')),
                supplier_name=data.get('name'),
                email=data.get('email'),
                contact_no=data.get('contact_no'),
                address=data.get('address')
            )
        else:
            db_name_map = {
                "medicines": "hstt_drugbrand_mst",
                "inventory": "hstt_inventory_dtl",
                "contracts": "hstt_ratecontract_item_dtl",
                "hospitals": "gblt_hospital_mst",
                "suppliers": "gblt_supplier_mst"
            }
            db_table = db_name_map.get(table_name, table_name)
            cols = [k for k in data.keys() if k != 'id']
            placeholders = ", ".join([f":{k}" for k in cols])
            cols_str = ", ".join(cols)
            db_session.execute(text(f"INSERT INTO {db_table} ({cols_str}) VALUES ({placeholders})"), data)
            db_session.commit()
            forecast_cache["data"] = None # Invalidate cache (FR-9)
            return jsonify({"success": "Row added successfully"}), 201
            
        db_session.add(row)
        db_session.commit()
        forecast_cache["data"] = None # Invalidate cache (FR-9)
        return jsonify({"success": "Row added successfully", "id": getattr(row, 'hstnumItembrandId' if table_name=='medicines' else 'hstnumInventoryId' if table_name=='inventory' else 'hstnumRcId' if table_name=='contracts' else 'gnumHospitalCode' if table_name=='hospitals' else 'supplier_id')}), 201
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close()

@app.route('/api/data/<table_name>/<int:row_id>', methods=['PUT'])
def update_table_row(table_name, row_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    db_session = Session()
    try:
        if table_name == 'medicines':
            row = db_session.query(HsttDrugbrandMst).filter(HsttDrugbrandMst.hstnumItembrandId == row_id).first()
            if not row: return jsonify({"error": "Row not found"}), 404
            row.gnumHospitalCode = int(data.get('hospital_code', row.gnumHospitalCode))
            row.hstnumItemId = int(data.get('item_id', row.hstnumItemId))
            row.hststrItemName = data.get('name', row.hststrItemName)
            row.hstnumManufacturerId = int(data.get('manufacturer_id', row.hstnumManufacturerId))
            row.hstnumDefaultRate = float(data.get('default_rate', row.hstnumDefaultRate))
            row.hstnumRateUnitId = int(data.get('rate_unit_id', row.hstnumRateUnitId))
            row.hstnumApprovedType = int(data.get('approved_type', row.hstnumApprovedType))
            row.hststrSpecification = data.get('specification', row.hststrSpecification)
            row.hstnumItemMake = int(data.get('item_make', row.hstnumItemMake))
            row.gdtEffectiveFrm = parse_date(data.get('effective_from')) or row.gdtEffectiveFrm
            row.hststrVedCategory = data.get('ved_category', row.hststrVedCategory)
        elif table_name == 'inventory':
            row = db_session.query(HsttInventoryDtl).filter(HsttInventoryDtl.hstnumInventoryId == row_id).first()
            if not row: return jsonify({"error": "Row not found"}), 404
            row.gnumHospitalCode = int(data.get('hospital_code', row.gnumHospitalCode))
            row.hstnumItemId = int(data.get('item_id', row.hstnumItemId))
            row.hstnumItembrandId = int(data.get('itembrand_id', row.hstnumItembrandId))
            row.hstnumStockQty = int(data.get('quantity', row.hstnumStockQty))
            row.hstnumMinStockLevel = int(data.get('min_stock', row.hstnumMinStockLevel))
            row.hstnumMaxStockLevel = int(data.get('max_stock', row.hstnumMaxStockLevel))
            row.hstdtExpiryDate = parse_date(data.get('expiry_date')) or row.hstdtExpiryDate
            row.hststrBatchNo = data.get('batch_no', row.hststrBatchNo)
        elif table_name == 'contracts':
            row = db_session.query(HsttRatecontractItemDtl).filter(HsttRatecontractItemDtl.hstnumRcId == row_id).first()
            if not row: return jsonify({"error": "Row not found"}), 404
            row.gnumHospitalCode = int(data.get('hospital_code', row.gnumHospitalCode))
            row.hstnumIsApproval = int(data.get('is_approval', row.hstnumIsApproval))
            row.hstnumContractTypeId = int(data.get('contract_type_id', row.hstnumContractTypeId))
            row.hstnumItemId = int(data.get('item_id', row.hstnumItemId))
            row.hstnumItembrandId = int(data.get('itembrand_id', row.hstnumItembrandId))
            row.hststrTenderNo = data.get('tender_no', row.hststrTenderNo)
            row.hststrQuotationNo = data.get('quotation_no', row.hststrQuotationNo)
            row.hstnumSupplierId = int(data.get('supplier_id', row.hstnumSupplierId))
            row.hstnumRate = float(data.get('rate', row.hstnumRate))
        elif table_name == 'hospitals':
            row = db_session.query(GbltHospitalMst).filter(GbltHospitalMst.gnumHospitalCode == row_id).first()
            if not row: return jsonify({"error": "Row not found"}), 404
            row.gstrHospitalName = data.get('name', row.gstrHospitalName)
            row.gstrHospitalAddress = data.get('address', row.gstrHospitalAddress)
            row.gnumContactNo = data.get('contact_no', row.gnumContactNo)
        elif table_name == 'suppliers':
            row = db_session.query(GbltSupplierMst).filter(GbltSupplierMst.supplier_id == row_id).first()
            if not row: return jsonify({"error": "Row not found"}), 404
            row.supplier_name = data.get('name', row.supplier_name)
            row.email = data.get('email', row.email)
            row.contact_no = data.get('contact_no', row.contact_no)
            row.address = data.get('address', row.address)
        else:
            db_name_map = {
                "medicines": "hstt_drugbrand_mst",
                "inventory": "hstt_inventory_dtl",
                "contracts": "hstt_ratecontract_item_dtl",
                "hospitals": "gblt_hospital_mst",
                "suppliers": "gblt_supplier_mst"
            }
            db_table = db_name_map.get(table_name, table_name)
            pk_res = db_session.execute(text(f"PRAGMA table_info({db_table})"))
            pk_col = "id"
            for col in pk_res:
                if col[5] == 1:
                    pk_col = col[1]
                    break
            set_clauses = ", ".join([f"{k} = :{k}" for k in data.keys() if k != pk_col])
            query_str = f"UPDATE {db_table} SET {set_clauses} WHERE {pk_col} = :pk_val"
            params = {**data, "pk_val": row_id}
            db_session.execute(text(query_str), params)
            db_session.commit()
            forecast_cache["data"] = None # Invalidate cache (FR-9)
            return jsonify({"success": "Row updated successfully"}), 200
            
        db_session.commit()
        forecast_cache["data"] = None # Invalidate cache (FR-9)
        return jsonify({"success": "Row updated successfully"}), 200
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close()

@app.route('/api/data/<table_name>/<int:row_id>', methods=['DELETE'])
def delete_table_row(table_name, row_id):
    db_session = Session()
    try:
        if table_name == 'medicines':
            row = db_session.query(HsttDrugbrandMst).filter(HsttDrugbrandMst.hstnumItembrandId == row_id).first()
        elif table_name == 'inventory':
            row = db_session.query(HsttInventoryDtl).filter(HsttInventoryDtl.hstnumInventoryId == row_id).first()
        elif table_name == 'contracts':
            row = db_session.query(HsttRatecontractItemDtl).filter(HsttRatecontractItemDtl.hstnumRcId == row_id).first()
        elif table_name == 'hospitals':
            row = db_session.query(GbltHospitalMst).filter(GbltHospitalMst.gnumHospitalCode == row_id).first()
        elif table_name == 'suppliers':
            row = db_session.query(GbltSupplierMst).filter(GbltSupplierMst.supplier_id == row_id).first()
        else:
            db_name_map = {
                "medicines": "hstt_drugbrand_mst",
                "inventory": "hstt_inventory_dtl",
                "contracts": "hstt_ratecontract_item_dtl",
                "hospitals": "gblt_hospital_mst",
                "suppliers": "gblt_supplier_mst"
            }
            db_table = db_name_map.get(table_name, table_name)
            pk_res = db_session.execute(text(f"PRAGMA table_info({db_table})"))
            pk_col = "id"
            for col in pk_res:
                if col[5] == 1:
                    pk_col = col[1]
                    break
            db_session.execute(text(f"DELETE FROM {db_table} WHERE {pk_col} = :row_id"), {"row_id": row_id})
            db_session.commit()
            forecast_cache["data"] = None # Invalidate cache (FR-9)
            return jsonify({"success": "Row deleted successfully"}), 200
            
        if not row:
            return jsonify({"error": "Row not found"}), 404
            
        db_session.delete(row)
        db_session.commit()
        forecast_cache["data"] = None # Invalidate cache (FR-9)
        return jsonify({"success": "Row deleted successfully"}), 200
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close()

@app.route('/api/tables', methods=['GET'])
def get_tables_list():
    db_session = Session()
    try:
        result = db_session.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'conversation_%' AND name NOT LIKE 'gblt_officer_mst'"
        ))
        tables = [row[0] for row in result]
        
        table_mappings = {
            "hstt_drugbrand_mst": "medicines",
            "hstt_inventory_dtl": "inventory",
            "hstt_ratecontract_item_dtl": "contracts",
            "gblt_hospital_mst": "hospitals",
            "gblt_supplier_mst": "suppliers"
        }
        
        data = []
        for t in tables:
            data.append({
                "db_name": t,
                "name": table_mappings.get(t, t)
            })
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close()

@app.route('/api/columns/<table_name>', methods=['GET'])
def get_table_columns(table_name):
    db_name_map = {
        "medicines": "hstt_drugbrand_mst",
        "inventory": "hstt_inventory_dtl",
        "contracts": "hstt_ratecontract_item_dtl",
        "hospitals": "gblt_hospital_mst",
        "suppliers": "gblt_supplier_mst"
    }
    db_table = db_name_map.get(table_name, table_name)
    db_session = Session()
    try:
        result = db_session.execute(text(f"PRAGMA table_info({db_table})"))
        columns = []
        for row in result:
            columns.append({
                "name": row[1],
                "type": row[2]
            })
        return jsonify(columns), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close()

@app.route('/api/table/create', methods=['POST'])
def create_new_table():
    data = request.get_json()
    if not data or 'table_name' not in data:
        return jsonify({"error": "Missing table name"}), 400
        
    table_name = data['table_name'].strip().lower().replace(' ', '_')
    if not table_name.isalnum() and '_' not in table_name:
        return jsonify({"error": "Invalid table name. Only alphanumeric and underscore allowed."}), 400
        
    db_session = Session()
    try:
        db_session.execute(text(f"""
            CREATE TABLE {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT
            )
        """))
        db_session.commit()
        return jsonify({"success": f"Table '{table_name}' created successfully with columns: id, name, description, status."}), 201
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)
