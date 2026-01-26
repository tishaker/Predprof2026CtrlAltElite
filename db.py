import sqlite3
from datetime import date


def init_db():
    conn = sqlite3.connect('admission.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS programs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        max_seats INTEGER NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS applicants (
        id INTEGER PRIMARY KEY,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS competition_lists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        applicant_id INTEGER NOT NULL,
        program_id INTEGER NOT NULL,
        date DATE NOT NULL,  -- например '2025-08-01'
        priority INTEGER CHECK (priority BETWEEN 1 AND 4),
        physics_ict_score INTEGER,
        russian_score INTEGER,
        math_score INTEGER,
        achievement_score INTEGER,
        total_score INTEGER,
        has_consent BOOLEAN DEFAULT 0,
        FOREIGN KEY (applicant_id) REFERENCES applicants(id),
        FOREIGN KEY (program_id) REFERENCES programs(id),
        UNIQUE(applicant_id, program_id, date)  -- один абитуриент не может быть дважды в один день на одну программу
    )
    ''')

    programs = [
        ('ПМИ', 40),
        ('ИВТ', 50),
        ('ИТСС', 30),
        ('ИБ', 20)
    ]

    cursor.execute("SELECT COUNT(*) FROM programs")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO programs (name, max_seats) VALUES (?, ?)", programs)

    conn.commit()
    conn.close()


if __name__ == '__main__':
    init_db()
