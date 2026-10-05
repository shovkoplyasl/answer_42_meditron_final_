"""Local accounts and an ASGI access boundary; existing clinical storage is unchanged."""
import hashlib
import hmac
import json
import secrets
import sqlite3
import time
from contextlib import contextmanager
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlsplit

from starlette.responses import JSONResponse

COOKIE = 'clinic_integrated_session'
MAX_BODY = 18 * 1024 * 1024
PUBLIC = {'/', '/app.js', '/style.css', '/portal.js', '/portal.css', '/api/health', '/health',
          '/api/auth/login', '/api/auth/session'}


class Accounts:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, salt TEXT, digest TEXT, role TEXT, name TEXT);
            CREATE TABLE IF NOT EXISTS sessions(digest TEXT PRIMARY KEY, username TEXT, csrf TEXT, expires REAL);
            CREATE TABLE IF NOT EXISTS ownership(document_id TEXT PRIMARY KEY, username TEXT);
            CREATE TABLE IF NOT EXISTS attempts(key TEXT, time REAL);
            CREATE TABLE IF NOT EXISTS security_audit(time REAL, username TEXT, action TEXT);
            CREATE TABLE IF NOT EXISTS inbox(id TEXT PRIMARY KEY, route_id TEXT, username TEXT, text TEXT, created REAL, read_at REAL);
            CREATE TABLE IF NOT EXISTS delivery(key TEXT PRIMARY KEY, last_sent REAL);
            ''')

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def create_user(self, username, password, role, name):
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 600_000).hex()
        with self.db() as db:
            db.execute('INSERT INTO users VALUES(?,?,?,?,?)', (username, salt, digest, role, name))

    def bootstrap(self):
        with self.db() as db:
            if db.execute('SELECT count(*) FROM users').fetchone()[0]:
                return
        entries = [('staff', 'staff', 'Координатор'), ('patient1', 'patient', 'Демо-пациент 1'),
                   ('patient2', 'patient', 'Демо-пациент 2')]
        lines = ['Локальные демонстрационные учётные записи. Не публикуйте этот файл.', '']
        for username, role, name in entries:
            password = secrets.token_urlsafe(15)
            self.create_user(username, password, role, name)
            lines.append(f'{username}\t{password}\t{name}')
        with self.db() as db:
            db.executemany('INSERT INTO ownership VALUES(?,?)', [('doc-018','patient1'), ('doc-039','patient2')])
        lines += ['', 'patient1: только doc-018. patient2: только doc-039.',
                  'Остальные документы доступны только сотруднику.',
                  'Пароли случайные, создаются один раз; сервер этот файл не выдаёт.']
        (self.path.parent/'LOCAL_ACCOUNTS.txt').write_text('\n'.join(lines), encoding='utf-8')

    def login(self, username, password, address):
        if not isinstance(username,str) or not isinstance(password,str) or len(username)>100 or len(password)>200:
            return None, 400
        now = time.time(); key = address
        with self.db() as db:
            db.execute('DELETE FROM attempts WHERE time<?',(now-300,))
            if db.execute('SELECT count(*) FROM attempts WHERE key=?',(key,)).fetchone()[0] >= 5:
                return None, 429
            user = db.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone()
        salt = user['salt'] if user else '00'*16
        digest = hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),600_000).hex()
        with self.db() as db:
            if not user or not hmac.compare_digest(digest,user['digest']):
                db.execute('INSERT INTO attempts VALUES(?,?)',(key,now))
                return None, 401
            token = secrets.token_urlsafe(32); csrf = secrets.token_urlsafe(32)
            db.execute('DELETE FROM sessions WHERE expires<?',(now,))
            db.execute('INSERT INTO sessions VALUES(?,?,?,?)',(self.token_hash(token),username,csrf,now+8*3600))
            db.execute('INSERT INTO security_audit VALUES(?,?,?)',(now,username,'login'))
        return {'token':token,'csrf':csrf,'user':self.public_user(user)}, 200

    @staticmethod
    def token_hash(token):
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def public_user(row):
        return {k:row[k] for k in ('username','role','name')}

    def session(self, token):
        if not token: return None
        with self.db() as db:
            row = db.execute('SELECT u.*,s.csrf FROM sessions s JOIN users u USING(username) WHERE s.digest=? AND expires>?',
                             (self.token_hash(token),time.time())).fetchone()
            return {'user':self.public_user(row),'csrf':row['csrf']} if row else None

    def logout(self, token):
        with self.db() as db:
            db.execute('DELETE FROM sessions WHERE digest=?',(self.token_hash(token),))

    def owns(self, username, document_id):
        with self.db() as db:
            return bool(db.execute('SELECT 1 FROM ownership WHERE username=? AND document_id=?',(username,document_id)).fetchone())


class AccessBoundary:
    def __init__(self, app, accounts):
        self.app=app; self.accounts=accounts

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http': return await self.app(scope,receive,send)
        headers={k.decode().lower():v.decode() for k,v in scope['headers']}
        host=headers.get('host','')
        try:parsed=urlsplit('http://'+host)
        except ValueError:parsed=urlsplit('http://invalid')
        async def protected_send(message):
            if message['type']=='http.response.start':
                if 200<=message['status']<300 and scope.get('state',{}).get('session') and scope['method']=='POST':
                    with self.accounts.db() as db:
                        db.execute('INSERT INTO security_audit VALUES(?,?,?)',(time.time(),scope['state']['session']['user']['username'],scope['method']+' '+scope['path']))
                message['headers'] += [(b'cache-control',b'no-store'),(b'x-content-type-options',b'nosniff'),
                    (b'x-frame-options',b'DENY'),(b'referrer-policy',b'no-referrer'),
                    (b'content-security-policy',b"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")]
            await send(message)
        async def error(code,text):
            await JSONResponse({'error':text},status_code=code)(scope,receive,protected_send)
        if parsed.hostname not in ('127.0.0.1','localhost') or parsed.username or parsed.password:
            return await error(403,'Доступ разрешён только через localhost')
        if headers.get('origin') and headers['origin'] != 'http://'+host:
            return await error(403,'Недопустимый источник запроса')
        if headers.get('sec-fetch-site')=='cross-site':return await error(403,'Межсайтовый запрос запрещён')
        cookie=SimpleCookie()
        try: cookie.load(headers.get('cookie',''))
        except Exception: pass
        token=cookie[COOKIE].value if COOKIE in cookie else ''
        session=self.accounts.session(token)
        path=scope['path']; method=scope['method']
        if path not in PUBLIC and not path.startswith('/assets/') and path not in ('/favicon.svg','/icons.svg'):
            if not session:return await error(401,'Войдите в личный кабинет')
            if session['user']['role']=='patient' and path not in ('/api/auth/logout',) and not path.startswith('/api/patient/'):
                return await error(403,'Функция доступна только сотруднику')
        body=b''
        if method in ('POST','PUT','PATCH','DELETE'):
            multipart = path=='/api/v1/analyze/file' and headers.get('content-type','').startswith('multipart/form-data;')
            if headers.get('content-type','').split(';')[0]!='application/json' and not multipart:return await error(415,'Нужен JSON')
            if path != '/api/auth/login':
                if not session:return await error(401,'Войдите в личный кабинет')
                if not hmac.compare_digest(headers.get('x-csrf-token',''),session['csrf']):return await error(403,'Недействительный токен запроса')
            while True:
                message=await receive()
                if message['type']=='http.disconnect':return
                body += message.get('body',b'')
                if len(body)>MAX_BODY:return await error(413,'Запрос превышает допустимый размер')
                if not message.get('more_body'):break
            try:
                payload={} if multipart else json.loads(body or b'{}')
                if not isinstance(payload,dict):raise ValueError()
            except (ValueError,UnicodeError):return await error(400,'Ожидается JSON-объект')
            scope.setdefault('state',{})['payload']=payload
        scope.setdefault('state',{}).update(session=session,session_token=token)
        delivered=False
        async def replay():
            nonlocal delivered
            if not delivered:
                delivered=True
                return {'type':'http.request','body':body,'more_body':False}
            return await receive()
        return await self.app(scope,replay if method in ('POST','PUT','PATCH','DELETE') else receive,protected_send)
