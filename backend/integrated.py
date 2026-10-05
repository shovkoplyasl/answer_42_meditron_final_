"""Thin UI integration layer; FINAL models and NLP remain the source of truth."""
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime,timedelta,timezone
from collections import defaultdict
import asyncio
import json
import os
import secrets

from fastapi import FastAPI,Depends,HTTPException,Request
from fastapi.responses import FileResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import main as core
import models,schemas
from database import get_db
from integration_init import initialize
from integration_access import Accounts,AccessBoundary,COOKIE

ROOT=Path(__file__).resolve().parents[1]
DATA=Path(os.environ.get('INTEGRATION_DATA',ROOT/'local-data'));DATA.mkdir(parents=True,exist_ok=True)
accounts=Accounts(DATA/'access.sqlite3')
with accounts.db() as db:
    missing=db.execute('SELECT count(*) FROM users').fetchone()[0]==0
if missing:
    password=secrets.token_urlsafe(15)
    accounts.create_user('staff',password,'staff','Координатор')
    (DATA/'LOCAL_ACCOUNTS.txt').write_text('Локальный демонстрационный вход. Не публикуйте пароль.\n\nstaff\t'+password+'\n',encoding='utf-8')

@asynccontextmanager
async def lifespan(app):
    await initialize()
    async with core.lifespan(core.app):yield

app=FastAPI(title='СМ-Клиника — единый стенд',lifespan=lifespan,docs_url=None,openapi_url=None)
app.add_middleware(AccessBoundary,accounts=accounts)
app.state.accounts=accounts

@app.get('/')
def index():return FileResponse(ROOT/'frontend/dist/index.html')

@app.get('/api/auth/session')
def session(request:Request):return request.state.session or {'user':None}

@app.post('/api/auth/login')
def login(request:Request):
    p=request.state.payload
    result,code=accounts.login(p.get('username'),p.get('password'),request.client.host)
    if not result:return JSONResponse({'error':'Неверный логин или пароль' if code!=429 else 'Повторите через 5 минут'},status_code=code)
    response=JSONResponse({'user':result['user'],'csrf':result['csrf']})
    response.set_cookie(COOKIE,result['token'],httponly=True,samesite='strict',max_age=28800)
    return response

@app.post('/api/auth/logout')
def logout(request:Request):
    accounts.logout(request.state.session_token)
    response=JSONResponse({'ok':True});response.delete_cookie(COOKIE);return response

def event(route_id,kind,**payload):
    return models.RouteEvent(route_id=route_id,event_type=kind,description=json.dumps(payload,ensure_ascii=False),source='coordinator')

def asutc(t):return t.replace(tzinfo=timezone.utc) if t.tzinfo is None else t

def formatdate(t):return t.strftime('%d.%m.%Y %H:%M') if t else '—'

@app.get('/api/v1/ui/patients')
async def cards(db:AsyncSession=Depends(get_db)):
    protocols=(await db.scalars(select(models.Protocol).order_by(models.Protocol.id.desc()))).all()
    findings=(await db.scalars(select(models.Finding))).all()
    routes=(await db.scalars(select(models.Route).order_by(models.Route.id))).all()
    events=(await db.scalars(select(models.RouteEvent).order_by(models.RouteEvent.id))).all()
    notes=(await db.scalars(select(models.Notification))).all()
    findings_by=defaultdict(list);route_protocol={};events_by=defaultdict(list);notes_by=defaultdict(list)
    for f in findings:findings_by[f.protocol_id].append(f)
    for e in events:
        events_by[e.route_id].append(e)
        try:pid=json.loads(e.description or '{}').get('protocol_id')
        except (ValueError,AttributeError):pid=None
        if pid:route_protocol[e.route_id]=pid
    links=(await db.execute(select(models.RouteTrigger.route_id,models.Trigger.protocol_id).join(models.Trigger,models.Trigger.id==models.RouteTrigger.trigger_id))).all()
    for rid,pid in links:route_protocol[rid]=pid
    for n in notes:notes_by[n.route_id].append(n)
    concepts=json.loads((ROOT/'backend/config/concepts.json').read_text(encoding='utf-8'))
    out=[]
    for p in protocols:
        rs=[r for r in routes if route_protocol.get(r.id)==p.id and r.status!='cancelled']
        r=rs[-1] if rs else None
        fs=findings_by[p.id];es=events_by[r.id] if r else [];ns=notes_by[r.id] if r else []
        stage='Протокол загружен'
        if r:stage='Запись предложена' if r.status=='planned' else 'Требуется проверка'
        if ns:stage='Уведомление создано'
        if r and r.status=='booked':stage='Запись зарегистрирована'
        comments=[];highlights=[]
        labels={'affirmed':'Указано в протоколе','negated':'Отрицается','suspected':'Предположение','uncertain':'Неоднозначно','historical':'Анамнез'}
        for f in fs:
            label=concepts.get(f.finding_type,{}).get('label',f.finding_type)
            msg=f'{label}: {labels.get(f.value,f.value or "")}'+(f'; категория {f.category}' if f.category else '')+(f'; сторона {f.side}' if f.side else '')
            comments.append(msg)
            if f.evidence_text:highlights.append({'id':str(f.id),'text':f.evidence_text,'comment':msg})
        if r:comments.append(r.next_step)
        if not fs:comments.append('Целевые признаки не обнаружены. Это не означает отсутствие заболеваний.')
        out.append({'id':str(p.id),'patientId':p.patient_id,'protocolId':p.id,'routeId':r.id if r else None,
                    'routes':[{'id':x.id,'specialist':x.specialist_type,'status':x.status} for x in rs],
                    'fio':f'Пациент №{p.patient_id}','gender':'—','birthDate':'—','attendingDoctorFio':'—','attendingDoctorSpec':'—',
                    'protocolDate':formatdate(p.protocol_date),'protocolDateISO':p.protocol_date.isoformat() if p.protocol_date else '',
                    'fileName':p.file_name,'routeDate':formatdate(r.created_at) if r else '—',
                    'humanInterference':any(e.event_type=='route.updated' for e in es),'pushCount':len(ns),
                    'targetDoctorSpec':r.specialist_type if r else 'Не назначен','csScore':None,'aiComment':'\n'.join(comments),
                    'protocolFullText':p.doc_text,'highlights':highlights,'stage':stage,
                    'status':'Требует консилиума' if r and r.status=='manual_review' else 'В работе' if r else 'Новое',
                    'urgency':'Не определена','city':'—','canNotify':bool(r and r.status=='planned')})
    return out

import_lock=asyncio.Lock()
@app.post('/api/v1/ui/import-demo')
async def import_demo(db:AsyncSession=Depends(get_db)):
    async with import_lock:
        corpus=json.loads((ROOT/'backend/data/private/corpus.json').read_text(encoding='utf-8'))
        names=set((await db.scalars(select(models.Protocol.file_name))).all());created=0
        for d in corpus:
            name='demo:'+d['id']+':'+d['filename']
            if name in names:continue
            patient=await core.create_patient(db)
            await core.analyze_protocol(schemas.ProtocolAnalyzeRequest(patient_id=patient['id'],protocol_text=d['text'],file_name=name),db)
            created+=1
        return {'created':created,'total':len(corpus)}

class EditRoute(BaseModel):
    specialist:str=Field(min_length=2,max_length=255)
    reason:str=Field(min_length=3,max_length=1000)
    protocol_id:int

@app.post('/api/v1/ui/route')
async def edit_route(p:EditRoute,db:AsyncSession=Depends(get_db)):
    protocol=await db.get(models.Protocol,p.protocol_id)
    if not protocol:raise HTTPException(404,'Протокол не найден')
    existing=(await cards(db))
    card=next(x for x in existing if x['protocolId']==p.protocol_id)
    r=await db.get(models.Route,card['routeId']) if card['routeId'] else None
    if r and r.status=='booked':raise HTTPException(409,'Маршрут уже записан: смена врача требует отмены записи')
    if not p.specialist.strip() or not p.reason.strip():raise HTTPException(422,'Укажите врача и причину')
    if not r:
        r=models.Route(patient_id=protocol.patient_id,status='planned',specialist_type=p.specialist,next_step='Консультация по решению координатора')
        db.add(r);await db.flush()
    r.specialist_type=p.specialist.strip();r.status='planned'
    db.add(event(r.id,'route.updated',protocol_id=p.protocol_id,reason=p.reason))
    await db.commit();return {'route_id':r.id}

NEUTRAL='В личном кабинете доступен следующий шаг. Откройте кабинет, чтобы посмотреть информацию и выбрать время.'

async def active_route(rid,db):
    r=await db.get(models.Route,rid,with_for_update=True)
    if not r:raise HTTPException(404,'Маршрут не найден')
    if r.status!='planned':raise HTTPException(409,'Сначала подтвердите маршрут; запись или уведомление сейчас недоступны')
    return r

@app.post('/api/v1/ui/routes/{rid}/notification')
async def notify(rid:int,db:AsyncSession=Depends(get_db)):
    await active_route(rid,db)
    latest=await db.scalar(select(models.Notification).where(models.Notification.route_id==rid).order_by(models.Notification.id.desc()))
    if latest and datetime.now(timezone.utc)-asutc(latest.created_at)<timedelta(hours=24):
        return {'id':latest.id,'message':latest.message_text,'external_delivery':False,'duplicate':True}
    n=models.Notification(route_id=rid,channel='local_preview',status='created',message_text=NEUTRAL)
    db.add(n);db.add(event(rid,'notification.created'));await db.commit()
    return {'id':n.id,'message':NEUTRAL,'external_delivery':False,'duplicate':False}

def offered(r):
    day=datetime.now(timezone.utc).date()+timedelta(days=1)
    return [{'id':f'{day.isoformat()}-{h}','date':datetime.combine(day,datetime.min.time(),tzinfo=timezone.utc).replace(hour=h).isoformat(),
             'label':f'{day.strftime("%d.%m.%Y")} {h:02}:00 UTC','doctor':'Демонстрационный врач','specialist':r.specialist_type,
             'clinic':'Учебное расписание'} for h in (9,12,15)]

@app.get('/api/v1/ui/routes/{rid}/slots')
async def slots(rid:int,db:AsyncSession=Depends(get_db)):
    r=await active_route(rid,db);return {'demo':True,'slots':offered(r)}

class Booking(BaseModel):slot_id:str
@app.post('/api/v1/ui/routes/{rid}/book')
async def book(rid:int,p:Booking,db:AsyncSession=Depends(get_db)):
    r=await active_route(rid,db)
    slot=next((s for s in offered(r) if s['id']==p.slot_id),None)
    if not slot:raise HTTPException(409,'Выберите доступное демонстрационное время')
    a=models.Appointment(route_id=rid,doctor_name=slot['doctor'],doctor_type=r.specialist_type,clinic=slot['clinic'],appointment_type='demo',
                         appointment_date=datetime.fromisoformat(slot['date']),external_slot_id=slot['id'],status='planned',is_previous_doctor=False)
    db.add(a);r.status='booked';db.add(event(rid,'appointment.booked',slot=slot['id']))
    await db.commit();return {'id':a.id,'demo':True,'message':'Запись сохранена локально; в клинику не передана'}

@app.post('/api/v1/ui/routes/{rid}/callback')
async def callback(rid:int,db:AsyncSession=Depends(get_db)):
    await active_route(rid,db);db.add(event(rid,'callback.requested'));await db.commit()
    return {'message':'Заявка сохранена в журнале; внешняя передача оператору не подключена'}

if (ROOT/'frontend/dist/assets').exists():app.mount('/assets',StaticFiles(directory=ROOT/'frontend/dist/assets'),name='assets')
@app.get('/favicon.svg')
def favicon():return FileResponse(ROOT/'frontend/public/favicon.svg')
app.mount('/',core.app)
