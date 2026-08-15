# ============================================
# Supply AI System
# File: core/database.py
# Description: Database setup and operations
# ============================================

import mysql.connector
from mysql.connector import pooling
import os
from dotenv import load_dotenv

load_dotenv()

_pool: pooling.MySQLConnectionPool | None = None

def _get_pool() -> pooling.MySQLConnectionPool:
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="defence_pool",
            pool_size=5,
            pool_reset_session=True,
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "defence_supply"),
        )
    return _pool

def get_connection():
    return _get_pool().get_connection()

def get_cursor(conn):
    return conn.cursor(dictionary=True)

def create_tables():
    conn = get_connection()
    cursor = get_cursor(conn)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bases (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(255) NOT NULL,
            location VARCHAR(255)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(255) NOT NULL,
            address VARCHAR(255),
            email VARCHAR(255),
            phone VARCHAR(255),
            pan_no VARCHAR(255),
            tan_no VARCHAR(255),
            gstn_no VARCHAR(255),
            bank_name VARCHAR(255),
            branch_name VARCHAR(255),
            ifsc_code VARCHAR(255),
            account_no VARCHAR(255)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(255) NOT NULL,
            category VARCHAR(100),
            composition VARCHAR(255),
            specification VARCHAR(255),
            shelf_life INT,
            unit VARCHAR(255),
            packing_unit VARCHAR(255),
            pvms_code VARCHAR(255),
            pvms_section_id INT,
            pvms_subsection_id INT,
            strength VARCHAR(255),
            drug_short_name VARCHAR(255),
            ved_category INT,
            edl_flag INT,
            is_cold INT,
            drug_standard VARCHAR(255),
            cpa_code VARCHAR(255),
            is_valid INT DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rate_contracts (
            id INT PRIMARY KEY AUTO_INCREMENT,
            rc_no VARCHAR(255) NOT NULL,
            item_id INT,
            supplier_id INT,
            base_id INT,
            contract_type VARCHAR(255),
            quantity REAL,
            ordered_qty REAL DEFAULT 0,
            rate REAL,
            rate_inc_tax REAL,
            sgst_tax REAL DEFAULT 0,
            cgst_tax REAL DEFAULT 0,
            igst_tax REAL DEFAULT 0,
            security_amount REAL DEFAULT 0,
            contract_date DATE,
            contract_from_date DATE,
            contract_to_date DATE,
            delivery_lead_time INT,
            delivery_days INT,
            tender_no VARCHAR(255),
            tender_date DATE,
            quotation_no VARCHAR(255),
            quotation_date DATE,
            status VARCHAR(50) DEFAULT 'active',
            remarks VARCHAR(255),
            FOREIGN KEY (item_id) REFERENCES items(id),
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
            FOREIGN KEY (base_id) REFERENCES bases(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INT PRIMARY KEY AUTO_INCREMENT,
            item_id INT,
            base_id INT,
            quantity REAL DEFAULT 0,
            threshold REAL DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items(id),
            FOREIGN KEY (base_id) REFERENCES bases(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS consumption (
            id INT PRIMARY KEY AUTO_INCREMENT,
            item_id INT,
            base_id INT,
            quantity_used REAL,
            date DATE,
            FOREIGN KEY (item_id) REFERENCES items(id),
            FOREIGN KEY (base_id) REFERENCES bases(id)
        )
    """)

    conn.commit()
    conn.close()

def seed_data():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM bases")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    bases = [
        ("Delhi Hospital", "Delhi"),
        ("Mumbai Hospital", "Mumbai"),
        ("Chennai Hospital", "Chennai"),
    ]
    cursor.executemany("INSERT INTO bases (name, location) VALUES (%s, %s)", bases)

    suppliers = [
        ("Sun Pharma Industries Ltd", "Vadodara, Gujarat", "supply@sunpharma.com", "9876541001", "AABCS1234D", "AABCS12345", "24AABCS1234D1Z1", "HDFC Bank", "Vadodara Branch", "HDFC0001111", "11112222333"),
        ("Cipla Limited", "Mumbai, Maharashtra", "orders@cipla.com", "9876541002", "AAACL5678E", "AAACL56789", "27AAACL5678E1Z2", "ICICI Bank", "BKC Branch", "ICIC0002222", "22223333444"),
    ]
    cursor.executemany("""
        INSERT INTO suppliers (name, address, email, phone, pan_no, tan_no, gstn_no, bank_name, branch_name, ifsc_code, account_no)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, suppliers)

    items = [
        ("Paracetamol 500mg", "Analgesic", "Paracetamol IP 500mg", "IP 2022", 36, "tablets", "strip of 10", "010101", 1, 1, "500mg", "PCM", 2, 1, 0, "IP", "CPA-001", 1),
        ("Amoxicillin 500mg", "Antibiotic", "Amoxicillin Trihydrate IP 500mg", "IP 2022", 24, "capsules", "strip of 10", "020101", 2, 1, "500mg", "AMOX", 1, 1, 0, "IP", "CPA-002", 1),
    ]
    cursor.executemany("""
        INSERT INTO items (name, category, composition, specification, shelf_life, unit, packing_unit,
                           pvms_code, pvms_section_id, pvms_subsection_id, strength, drug_short_name,
                           ved_category, edl_flag, is_cold, drug_standard, cpa_code, is_valid)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, items)

    conn.commit()
    conn.close()

def get_all_inventory():
    conn = get_connection()
    cursor = get_cursor(conn)
    cursor.execute("""
        SELECT
            i.id, i.name as item, i.category, i.unit, i.strength,
            i.pvms_code, i.cpa_code, i.drug_short_name,
            i.ved_category, i.edl_flag, i.is_cold,
            i.drug_standard, i.shelf_life,
            inv.quantity, inv.threshold,
            b.name as base
        FROM inventory inv
        JOIN items i ON inv.item_id = i.id
        JOIN bases b ON inv.base_id = b.id
        ORDER BY i.name, b.name
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_low_stock():
    conn = get_connection()
    cursor = get_cursor(conn)
    cursor.execute("""
        SELECT
            i.name as item, i.unit, inv.quantity,
            inv.threshold, b.name as base,
            ROUND(inv.quantity * 100.0 / inv.threshold) as stock_pct
        FROM inventory inv
        JOIN items i ON inv.item_id = i.id
        JOIN bases b ON inv.base_id = b.id
        WHERE inv.quantity < inv.threshold
        ORDER BY stock_pct ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_active_contracts():
    conn = get_connection()
    cursor = get_cursor(conn)
    cursor.execute("""
        SELECT
            rc.rc_no, i.name as item, s.name as supplier,
            b.name as base, rc.contract_type,
            rc.quantity, rc.ordered_qty,
            rc.rate, rc.rate_inc_tax,
            rc.contract_to_date, rc.delivery_days
        FROM rate_contracts rc
        JOIN items i ON rc.item_id = i.id
        JOIN suppliers s ON rc.supplier_id = s.id
        JOIN bases b ON rc.base_id = b.id
        WHERE rc.status = 'active'
        ORDER BY rc.contract_to_date ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_cold_storage_items():
    conn = get_connection()
    cursor = get_cursor(conn)
    cursor.execute("""
        SELECT i.name, i.pvms_code, inv.quantity, b.name as base
        FROM inventory inv
        JOIN items i ON inv.item_id = i.id
        JOIN bases b ON inv.base_id = b.id
        WHERE i.is_cold = 1
        ORDER BY i.name
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_items_by_ved(ved_cat):
    conn = get_connection()
    cursor = get_cursor(conn)
    cursor.execute("""
        SELECT i.name, inv.quantity, b.name as base
        FROM inventory inv
        JOIN items i ON inv.item_id = i.id
        JOIN bases b ON inv.base_id = b.id
        WHERE i.ved_category = %s
        ORDER BY i.name
    """, (ved_cat,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_edl_items():
    conn = get_connection()
    cursor = get_cursor(conn)
    cursor.execute("""
        SELECT i.name, i.pvms_code, inv.quantity, b.name as base
        FROM inventory inv
        JOIN items i ON inv.item_id = i.id
        JOIN bases b ON inv.base_id = b.id
        WHERE i.edl_flag = 1
        ORDER BY i.name
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_drug_details(name_query):
    conn = get_connection()
    cursor = get_cursor(conn)
    cursor.execute("""
        SELECT 
            i.name, i.strength, i.pvms_code, i.category,
            i.composition, i.specification, i.shelf_life,
            i.cpa_code, i.drug_standard, i.ved_category,
            i.edl_flag, i.is_cold, inv.quantity, b.name as base
        FROM inventory inv
        JOIN items i ON inv.item_id = i.id
        JOIN bases b ON inv.base_id = b.id
        WHERE i.name LIKE %s
        ORDER BY i.name
    """, (f"%{name_query}%",))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_item_by_pvms(pvms_code):
    conn = get_connection()
    cursor = get_cursor(conn)
    cursor.execute("""
        SELECT i.name, i.strength, inv.quantity, b.name as base
        FROM inventory inv
        JOIN items i ON inv.item_id = i.id
        JOIN bases b ON inv.base_id = b.id
        WHERE i.pvms_code = %s
        ORDER BY i.name
    """, (pvms_code,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_items_by_pvms_section(section_id):
    conn = get_connection()
    cursor = get_cursor(conn)
    cursor.execute("""
        SELECT i.name, i.pvms_code, i.strength, i.ved_category, i.edl_flag, i.is_cold
        FROM items i
        WHERE i.pvms_section_id = %s
        ORDER BY i.name
    """, (section_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows
