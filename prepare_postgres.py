from pathlib import Path
import secrets

path=Path(__file__).resolve().parent/'.env.postgres'
if not path.exists():
    password=secrets.token_urlsafe(24)
    path.write_text('POSTGRES_DB=clinic\nPOSTGRES_USER=clinic\nPOSTGRES_PASSWORD='+password+'\nDATABASE_URL=postgresql+asyncpg://clinic:'+password+'@127.0.0.1:55432/clinic\n',encoding='utf-8')
print('PostgreSQL configuration ready.')
