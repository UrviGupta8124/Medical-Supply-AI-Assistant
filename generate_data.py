# ============================================
# Supply AI System
# File: generate_data.py
# Description: Seeding script to initialize MySQL/SQLite
# ============================================

from core.database import create_tables, seed_data

if __name__ == '__main__':
    create_tables()
    seed_data()
    print("✅ Database tables successfully created and seeded.")
