# ============================================
# Supply AI System
# File: core/router.py
# Description: Intent routing for chatbot queries
# ============================================

import os, json
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY")
)

def route_query(query: str) -> dict:
    system_prompt = """You are the classification router for AAMF.
Analyze the user's query and decide what categories of data are needed.
Respond with a JSON object containing exactly these boolean keys:
- needs_inventory: true if the query is about stock, medicine quantities, or hospital stock.
- needs_forecast: true if the query is about future demand, stockout dates, depletion, or forecasting.
- needs_contracts: true if the query is about rate contracts, prices, supplier rates.
- needs_pvms: true if the query asks about PVMS codes, sections, or items by PVMS.
- needs_cold: true if the query asks about cold chain, refrigeration, or cold storage drugs.
- needs_ved: true if the query asks about VED categories (Vital, Essential, Desirable).
- needs_edl: true if the query asks about Essential Drug List (EDL) status.
- needs_drug_detail: true if the query asks for deep details/specifications of a specific drug.
- needs_tender: true if the query asks about tender numbers or quotation details.

Example Output:
{
  "needs_inventory": true,
  "needs_forecast": false,
  "needs_contracts": true,
  "needs_pvms": false,
  "needs_cold": false,
  "needs_ved": false,
  "needs_edl": false,
  "needs_drug_detail": false,
  "needs_tender": false
}"""

    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Query: {query}")
        ]
        res = _llm.invoke(messages)
        clean_res = res.content.strip()
        if "```json" in clean_res:
            clean_res = clean_res.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_res:
            clean_res = clean_res.split("```")[1].split("```")[0].strip()
            
        return json.loads(clean_res)
    except Exception as e:
        print(f"Router error: {e}")
        return {
            "needs_inventory": False,
            "needs_forecast": False,
            "needs_contracts": False,
            "needs_pvms": False,
            "needs_cold": False,
            "needs_ved": False,
            "needs_edl": False,
            "needs_drug_detail": False,
            "needs_tender": False
        }
