# ============================================
# Supply AI System
# File: core/pdf_rag.py
# Description: PDF Retrieval-Augmented Generation using FAISS
# ============================================

import os, io
from pypdf import PdfReader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.messages import SystemMessage, HumanMessage

_embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
_pdf_store = {}

def ingest_pdf(pdf_bytes: bytes, filename: str, llm, session_id: str = "default") -> dict:
    try:
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
            return {"error": "Could not extract any readable text from PDF."}
            
        vector_store = FAISS.from_texts(chunks, _embeddings)
        _pdf_store[session_id] = {
            "filename": filename,
            "vector_store": vector_store,
            "llm": llm
        }
        return {"filename": filename, "chunks": len(chunks)}
    except Exception as e:
        return {"error": f"Failed to parse PDF: {str(e)}"}

def query_pdf(query: str, session_id: str = "default", language: str = "en") -> str:
    session = _pdf_store.get(session_id)
    if not session:
        return "No PDF has been uploaded for this session."
        
    vector_store = session["vector_store"]
    llm = session["llm"]
    
    docs = vector_store.similarity_search(query, k=3)
    context = "\n\n".join(d.page_content for d in docs)
    
    lang_instruction = "Respond in Hindi." if language == "hi" else "Respond in English."
    
    system_prompt = f"""You are AAMF's RAG answering engine.
Answer the user's query strictly based on the provided PDF context snippet below.
Do not make up facts outside the context.
{lang_instruction}

Context:
{context}"""

    try:
        res = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=query)
        ])
        return res.content.strip()
    except Exception as e:
        return f"Error querying document: {e}"

def get_pdf_status(session_id: str = "default") -> dict | None:
    session = _pdf_store.get(session_id)
    if session:
        return {"loaded": True, "filename": session["filename"]}
    return None

def clear_pdf(session_id: str = "default"):
    _pdf_store.pop(session_id, None)
