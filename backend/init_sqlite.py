import sqlite3

with open('database/schema.sql', 'r', encoding='utf-8') as f:
    sql = f.read()

# Адаптируем синтаксис PostgreSQL под SQLite на лету
sql = sql.replace(' cascade;', ';')
sql = sql.replace('serial', 'integer')
sql = sql.replace('timestamptz', 'timestamp')
sql = sql.replace('jsonb', 'text')

conn = sqlite3.connect('test.db')
conn.executescript(sql)
conn.close()
print("База test.db успешно создана!")
