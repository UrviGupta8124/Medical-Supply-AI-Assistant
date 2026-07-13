import sqlite3, os

db_path = os.path.join('c:/Users/gupta/Downloads/urvashi/projects/med','medicines.db')
conn = sqlite3.connect(db_path)

tables = [
    'gblt_supplier_mst',
    'gblt_hospital_mst',
    'hstt_drugbrand_mst',
    'hstt_ratecontract_item_dtl',
    'hstt_inventory_dtl',
    'conversation_log'
]

views = [
    'vw_medicine_inventory',
    'vw_active_contracts',
    'vw_registered_hospitals',
    'vw_low_stock_alerts',
    'vw_suppliers',
    'vw_paracetamol_inventory',
    'ved'
]

print("=== Base Tables ===")
for t in tables:
    try:
        count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"{t}: {count} rows")
    except Exception as e:
        print(f"{t}: Error: {e}")

print("\n=== SQL Views ===")
for v in views:
    try:
        count = conn.execute(f"SELECT COUNT(*) FROM {v}").fetchone()[0]
        print(f"{v}: {count} rows")
    except Exception as e:
        print(f"{v}: Error: {e}")

conn.close()
