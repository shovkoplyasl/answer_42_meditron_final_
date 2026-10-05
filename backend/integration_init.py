"""Idempotent schema initialization from SQL; never executes DROP statements."""
import re
from pathlib import Path
from sqlalchemy import text
from database import engine

ROOT=Path(__file__).resolve().parent

async def initialize():
    original=(ROOT/'database/schema.sql').read_text(encoding='utf-8')
    # The supplied schema ends with mistakenly appended Python. Use SQL CREATEs only.
    sql=original.split('# =',1)[0]
    creates=[s.strip() for s in sql.split(';') if re.match(r'^\s*create\s+(table|index)\s',s,re.I)]
    assert len([s for s in creates if s.lower().startswith('create table')])==16
    async with engine.begin() as conn:
        for s in creates:
            s=re.sub(r'create\s+(table|index)\s+',r'create \1 if not exists ',s,flags=re.I)
            if engine.dialect.name=='sqlite':
                s=re.sub(r'\bserial\b','integer',s,flags=re.I)
                s=re.sub(r'\btimestamptz\b','timestamp',s,flags=re.I)
                s=re.sub(r'\bjsonb\b','text',s,flags=re.I)
            await conn.execute(text(s))
    from scripts.seed_routing_rules import seed
    await seed()
