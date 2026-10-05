"""One localhost server: built React UI + original FINAL FastAPI + integration adapter."""
from pathlib import Path
import argparse
import os
import sys
import threading
import webbrowser

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'python-deps'))
sys.path.insert(0,str(ROOT/'backend'))

def configure(postgres=False):
    from dotenv import load_dotenv
    load_dotenv(ROOT/'.env')
    if postgres:
        if not (ROOT/'.env.postgres').is_file():
            raise RuntimeError('Run START_POSTGRES.cmd first.')
        load_dotenv(ROOT/'.env.postgres',override=True)
    (ROOT/'local-data').mkdir(exist_ok=True)
    os.environ.setdefault('DATABASE_URL','sqlite+aiosqlite:///'+(ROOT/'local-data/clinic.sqlite3').as_posix())
    os.environ.setdefault('INTEGRATION_DATA',str(ROOT/'local-data'))

def main():
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8050);p.add_argument('--no-browser',action='store_true');p.add_argument('--postgres',action='store_true');args=p.parse_args()
    configure(args.postgres)
    print('СМ-Клиника: http://127.0.0.1:'+str(args.port),flush=True)
    print('Локальный пароль: '+str(ROOT/'local-data/LOCAL_ACCOUNTS.txt'),flush=True)
    if not args.no_browser:threading.Timer(2,lambda:webbrowser.open('http://127.0.0.1:'+str(args.port))).start()
    import uvicorn
    uvicorn.run('integrated:app',host='127.0.0.1',port=args.port)

if __name__=='__main__':main()
