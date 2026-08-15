# ============================================
# Supply AI System
# File: main.py
# Description: FastAPI backend server
# Run: uvicorn main:app --reload
# ============================================

from fastapi import FastAPI, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import trim_messages, SystemMessage, HumanMessage, AIMessage
import os, sys, time, re, secrets, random, string
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Header, HTTPException, Depends
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import base64

from core.pdf_rag import ingest_pdf, query_pdf, get_pdf_status, clear_pdf
from core.router import route_query
from core.database import (
    get_connection, get_cursor, get_all_inventory, get_low_stock,
    get_active_contracts, get_cold_storage_items, get_items_by_ved,
    get_edl_items, get_drug_details, get_item_by_pvms, get_items_by_pvms_section
)
from core.forecasting import run_forecast

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"reply": "⚠ Too many requests. Please wait a moment."}
    )

app.mount("/static", StaticFiles(directory="static"), name="static")

ALLOWED_IPS = ["127.0.0.1"]
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme123")

_admin_sessions: dict = {}
_captcha_store: dict = {}

ALLOWED_TABLES = {
    "bases": ["id", "name", "location"],
    "items": ["id", "name", "category", "composition", "specification", "shelf_life",
              "unit", "packing_unit", "pvms_code", "pvms_section_id", "pvms_subsection_id",
              "strength", "drug_short_name", "ved_category", "edl_flag", "is_cold",
              "drug_standard", "cpa_code", "is_valid"],
    "inventory": ["id", "item_id", "base_id", "quantity", "threshold"],
    "rate_contracts": ["id", "rc_no", "item_id", "supplier_id", "base_id", "contract_type",
                        "quantity", "ordered_qty", "rate", "rate_inc_tax", "sgst_tax",
                        "cgst_tax", "igst_tax", "security_amount", "contract_date",
                        "contract_from_date", "contract_to_date", "delivery_lead_time",
                        "delivery_days", "tender_no", "tender_date", "quotation_no",
                        "quotation_date", "status", "remarks"],
}

class CaptchaResponse(BaseModel):
    captcha_id: str
    answer: str

class LoginRequest(BaseModel):
    username: str
    password: str
    captcha_id: str
    captcha_answer: str

def verify_ip(request: Request):
    client_ip = request.client.host
    if client_ip not in ALLOWED_IPS:
        raise HTTPException(status_code=403, detail="Forbidden")

_llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.2,
    api_key=os.getenv("GROQ_API_KEY")
)

_fallback_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.1,
    api_key=os.getenv("GROQ_API_KEY")
)

_forecast_cache = {"data": None, "timestamp": 0}
CACHE_DURATION = 600

_FORECAST_KEYWORDS = [
    "stockout", "stock out", "run out", "runs out", "when will",
    "how long", "days left", "days remaining", "last how", "deplete",
    "exhaust", "reorder", "replenish", "restock", "forecast", "predict",
    "demand", "projection", "expiry of stock", "critical date",
    "out of stock", "stockout date",
]

def _needs_forecast_hint(query_lower: str) -> bool:
    return any(w in query_lower for w in _FORECAST_KEYWORDS)

def _get_forecast_df():
    global _forecast_cache
    now = time.time()
    if _forecast_cache["data"] is None or now - _forecast_cache["timestamp"] > CACHE_DURATION:
        forecast_df = run_forecast(silent=True)
        _forecast_cache["data"] = forecast_df
        _forecast_cache["timestamp"] = now
    return _forecast_cache["data"]

def generate_captcha_image(text: str) -> str:
    width, height = 320, 90
    img = Image.new("RGB", (width, height), color=(245, 245, 245))
    draw = ImageDraw.Draw(img)

    for _ in range(6):
        x1, y1 = random.randint(0, width), random.randint(0, height)
        x2, y2 = random.randint(0, width), random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(180, 180, 180), width=1)

    for _ in range(80):
        x, y = random.randint(0, width), random.randint(0, height)
        draw.point((x, y), fill=(150, 150, 150))

    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except:
        font = ImageFont.load_default()

    x = 20
    for char in text:
        char_img = Image.new("RGBA", (40, 60), (0, 0, 0, 0))
        char_draw = ImageDraw.Draw(char_img)
        color = (
            random.randint(20, 100),
            random.randint(20, 100),
            random.randint(20, 100)
        )
        char_draw.text((5, 5), char, font=font, fill=color)
        angle = random.randint(-25, 25)
        char_img = char_img.rotate(angle, expand=True)
        y_offset = random.randint(5, 20)
        img.paste(char_img, (x, y_offset), char_img)
        x += random.randint(28, 36)

    img = img.filter(ImageFilter.GaussianBlur(radius=0.8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return "data:image/png;base64," + base64.b64encode(buf.read()).decode()

@app.get("/")
def serve_home():
    return FileResponse("static/index.html")

@app.get("/api/forecast")
def get_forecast(_=Depends(verify_ip)):
    forecast_df = _get_forecast_df()
    result = []
    for _, row in forecast_df.iterrows():
        days_until = None
        if row["stockout_date"]:
            days_until = (datetime.strptime(row["stockout_date"], "%Y-%m-%d") - datetime.now()).days
        result.append({
            "item": row["item"],
            "base": row["base"],
            "current_stock": row["current_stock"],
            "avg_daily_forecast": row["avg_daily_forecast"],
            "total_30d_forecast": row["total_30d_forecast"],
            "stockout_date": row["stockout_date"],
            "days_until_stockout": days_until,
            "status": "critical" if days_until and days_until < 10
                      else "low" if days_until and days_until < 20
                      else "safe"
        })
    result.sort(key=lambda x: x["days_until_stockout"] if x["days_until_stockout"] is not None else 999)
    return result

@app.post("/api/upload-pdf")
async def upload_pdf(request: Request, file: UploadFile = File(...), _=Depends(verify_ip)):
    if not file.filename.endswith(".pdf"):
        return JSONResponse(status_code=400, content={"error": "Only PDF files are supported."})
    pdf_bytes = await file.read()
    result = ingest_pdf(pdf_bytes, file.filename, _llm, session_id="default")
    if "error" in result:
        return JSONResponse(status_code=422, content=result)
    return result

@app.get("/api/pdf-status")
def pdf_status(_=Depends(verify_ip)):
    status = get_pdf_status("default")
    return status if status else {"loaded": False}

@app.delete("/api/pdf-clear")
def pdf_clear(_=Depends(verify_ip)):
    clear_pdf("default")
    return {"success": True}

class ChatRequest(BaseModel):
    message: str
    history: list = []
    language: str = "en"

    @field_validator('message')
    def message_must_be_valid(cls, v):
        if len(v) > 1000:
            raise ValueError('Message too long')
        if not v.strip():
            raise ValueError('Message cannot be empty')
        return v.strip()

@app.post("/api/chat")
@limiter.limit("20/minute")
def chat(request: Request, body: ChatRequest, _=Depends(verify_ip)):
    query = body.message.lower()
    
    pdf_info = get_pdf_status("default")
    if pdf_info:
        system_keywords = ["stock", "inventory", "contract", "forecast", "hospital", "base"]
        is_system_query = any(w in query for w in system_keywords)
        if not is_system_query:
            answer = query_pdf(body.message, session_id="default", language=body.language)
            return {"reply": answer}

    route = route_query(body.message)
    needs_inventory = route["needs_inventory"]
    needs_forecast = route["needs_forecast"]
    needs_contracts = route["needs_contracts"]
    needs_pvms = route["needs_pvms"]
    needs_cold = route["needs_cold"]
    needs_ved = route["needs_ved"]
    needs_edl = route["needs_edl"]
    needs_drug_detail = route["needs_drug_detail"]
    needs_tender = route["needs_tender"]

    if needs_inventory and _needs_forecast_hint(query):
        needs_forecast = True
    if _needs_forecast_hint(query):
        needs_forecast = True

    inventory_rows = get_all_inventory() if (needs_inventory or needs_drug_detail or needs_pvms) else []
    low_stock_rows = get_low_stock() if (needs_inventory or needs_forecast) else []

    inventory_text = ""
    if needs_inventory:
        inventory_text = "\n".join(
            f"{r['item']} | Stock: {r['quantity']} {r['unit']} | "
            f"Threshold: {r['threshold']} | Hospital: {r['base']} | "
            f"Level: {round(r['quantity']/r['threshold']*100)}% | "
            f"VED: {'Vital' if r['ved_category']==1 else 'Essential' if r['ved_category']==2 else 'Desirable'} | "
            f"EDL: {'Yes' if r['edl_flag']==1 else 'No'} | "
            f"Cold: {'Yes' if r['is_cold']==1 else 'No'} | "
            f"PVMS: {r['pvms_code']} | CPA: {r['cpa_code']}"
            for r in inventory_rows
        )

    low_stock_text = "\n".join(
        f"{r['item']} | Current: {r['quantity']} | "
        f"Threshold: {r['threshold']} | Hospital: {r['base']} | "
        f"Stock: {r['stock_pct']}%"
        for r in low_stock_rows
    ) or "All medicines above threshold."

    contract_text = ""
    if needs_contracts:
        contract_rows = get_active_contracts()
        contract_text = f"TOTAL ACTIVE CONTRACTS: {len(contract_rows)}\n\n" + "\n".join(
            f"{r['item']} | RC: {r['rc_no']} | Supplier: {r['supplier']} | "
            f"Rate: ₹{r['rate']} | Rate+Tax: ₹{r['rate_inc_tax']}"
            for r in contract_rows
        )

    pvms_text = ""
    if needs_pvms:
        section_match = re.search(r'section\s+(\d+)', query)
        code_match = re.search(r'pvms\s+([A-Z0-9\-]+)', body.message, re.IGNORECASE)
        if section_match:
            section_id = int(section_match.group(1))
            pvms_rows = get_items_by_pvms_section(section_id)
            pvms_text = f"PVMS SECTION {section_id}:\n" + "\n".join(
                f"{r['name']} | PVMS: {r['pvms_code']}"
                for r in pvms_rows
            )
        elif code_match:
            pvms_code = code_match.group(1)
            pvms_rows = get_item_by_pvms(pvms_code)
            pvms_text = f"PVMS CODE {pvms_code}:\n" + "\n".join(
                f"{r['name']} | Stock: {r['quantity']} | Hospital: {r['base']}"
                for r in pvms_rows
            )

    cold_text = ""
    if needs_cold:
        cold_rows = get_cold_storage_items()
        cold_text = "\n".join(
            f"{r['name']} | PVMS: {r['pvms_code']} | Stock: {r['quantity']} | Hospital: {r['base']}"
            for r in cold_rows
        )

    ved_text = ""
    if needs_ved:
        vital = get_items_by_ved(1)
        essential = get_items_by_ved(2)
        desirable = get_items_by_ved(3)
        ved_text = "VITAL DRUGS:\n" + "\n".join(
            f"{r['name']} | Stock: {r['quantity']} | Hospital: {r['base']}" for r in vital
        )

    edl_text = ""
    if needs_edl:
        edl_rows = get_edl_items()
        edl_text = "\n".join(
            f"{r['name']} | Stock: {r['quantity']} | Hospital: {r['base']}"
            for r in edl_rows
        )

    forecast_text = ""
    if needs_forecast:
        forecast_df = _get_forecast_df()
        forecast_text = "\n".join(
            f"{row['item']} | Hospital: {row['base']} | "
            f"Avg/day: {row['avg_daily_forecast']} | "
            f"Stockout: {row['stockout_date'] or 'Safe'}"
            for _, row in forecast_df.iterrows()
        )

    category_summary: dict = {}
    hospital_summary: dict = {}
    for r in inventory_rows:
        category_summary[r['category']] = category_summary.get(r['category'], 0) + r['quantity']
        hospital_summary[r['base']] = hospital_summary.get(r['base'], 0) + r['quantity']

    category_text = "\n".join(f"{cat}: {qty}" for cat, qty in category_summary.items())
    hospital_text = "\n".join(f"{hosp}: {qty}" for hosp, qty in hospital_summary.items())

    language_instruction = "Respond in Hindi." if body.language == "hi" else "Respond in English."

    system_prompt = f"""You are AAMF — AI Assistant for Medical Facilities, an expert medical supply chain analyst.
You manage pharmaceutical supply for three hospitals: Delhi Hospital, Mumbai Hospital, and Chennai Hospital.

STRICT RULES:
- Provide recommendations based strictly on the provided context tables.
- Limit output tables to max 5 columns and 20 rows.
- If user requests a chart, include a JSON code block formatted as:
