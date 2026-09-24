import sqlite3
from backend.config import DB_PATH

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    def add_col(table, col, col_type):
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
            print(f"Added {col} to {table}")
        except Exception as e:
            print(f"Skipping {table}.{col}: {e}")

    add_col("transitions", "sme_country", "VARCHAR(100) DEFAULT 'India'")
    add_col("transitions", "receiver_country", "VARCHAR(100) DEFAULT 'India'")
    add_col("transitions", "sme_timezone", "VARCHAR(50) DEFAULT 'Asia/Kolkata'")
    add_col("transitions", "receiver_timezone", "VARCHAR(50) DEFAULT 'Asia/Kolkata'")
    add_col("transitions", "sme_shift_start", "TIME DEFAULT '08:00:00'")
    add_col("transitions", "sme_shift_end", "TIME DEFAULT '17:00:00'")
    add_col("transitions", "receiver_shift_start", "TIME DEFAULT '08:00:00'")
    add_col("transitions", "receiver_shift_end", "TIME DEFAULT '17:00:00'")
    add_col("transitions", "custom_shifts_enabled", "BOOLEAN DEFAULT 0")

    add_col("project_profiles", "project_category", "VARCHAR(100) DEFAULT 'development_and_ams'")
    add_col("project_profiles", "intended_levels", "JSON DEFAULT '[\"L1\", \"L2\", \"L3\"]'")

    add_col("stakeholders", "level", "VARCHAR(20) DEFAULT 'L1'")
    add_col("kt_sessions", "receiver_id", "VARCHAR(36)")

    conn.commit()
    conn.close()
    print("Database migration completed successfully.")

if __name__ == "__main__":
    migrate()

