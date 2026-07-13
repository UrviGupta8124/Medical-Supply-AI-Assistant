import sqlite3, os

db_path = os.path.join('c:/Users/gupta/Downloads/urvashi/projects/med','medicines.db')
conn = sqlite3.connect(db_path)
rows = conn.execute("SELECT id, role, content FROM conversation_log ORDER BY id DESC LIMIT 10").fetchall()
with open("logs_output.txt", "w", encoding="utf-8") as f:
    f.write("=== CONVERSATION LOGS (LAST 10) ===\n")
    for r in rows:
        f.write(f"[{r[0]}] {r[1].upper()}: {r[2][:100]}\n")
conn.close()
