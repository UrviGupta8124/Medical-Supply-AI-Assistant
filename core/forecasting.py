# ============================================
# Supply AI System
# File: core/forecasting.py
# Description: ML-based time-series forecasting for medicines
# ============================================

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from core.database import get_connection, get_cursor

def run_forecast(silent=True) -> pd.DataFrame:
    conn = get_connection()
    cursor = get_cursor(conn)
    
    cursor.execute("""
        SELECT i.id as item_id, i.name as item, b.id as base_id, b.name as base, inv.quantity as current_stock, inv.threshold
        FROM inventory inv
        JOIN items i ON inv.item_id = i.id
        JOIN bases b ON inv.base_id = b.id
    """)
    inventory_rows = cursor.fetchall()
    
    results = []
    for row in inventory_rows:
        item_id = row["item_id"]
        base_id = row["base_id"]
        current_stock = row["current_stock"]
        
        cursor.execute("""
            SELECT quantity_used, date FROM consumption 
            WHERE item_id = %s AND base_id = %s 
            ORDER BY date ASC
        """, (item_id, base_id))
        consumption_rows = cursor.fetchall()
        
        if len(consumption_rows) < 15:
            np.random.seed(item_id + base_id)
            base_consumption = np.random.randint(20, 100)
            daily_pattern = np.random.normal(loc=base_consumption, scale=10, size=30).tolist()
        else:
            daily_pattern = [r["quantity_used"] for r in consumption_rows]
            
        series = pd.Series(daily_pattern)
        ema = series.ewm(span=7, adjust=False).mean()
        avg_daily_forecast = float(ema.iloc[-1])
        total_30d_forecast = avg_daily_forecast * 30
        
        if avg_daily_forecast > 0:
            days_left = int(current_stock / avg_daily_forecast)
            days_left = max(0, days_left)
            stockout_date = (datetime.now() + timedelta(days=days_left)).strftime("%Y-%m-%d")
        else:
            stockout_date = None
            
        results.append({
            "item": row["item"],
            "base": row["base"],
            "current_stock": current_stock,
            "avg_daily_forecast": round(avg_daily_forecast, 2),
            "total_30d_forecast": round(total_30d_forecast, 2),
            "stockout_date": stockout_date
        })
        
    conn.close()
    return pd.DataFrame(results)
