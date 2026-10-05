"""Original FINAL tests + integration scenarios, all against a fresh disposable SQLite DB."""
from pathlib import Path
import os,sys,tempfile,json,asyncio,io,zipfile

ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'python-deps'),str(ROOT/'backend')]

def main():
    with tempfile.TemporaryDirectory(prefix='clinic-integration-') as folder:
        os.environ['DATABASE_URL']='sqlite+aiosqlite:///'+(Path(folder)/'test.db').as_posix()
        os.environ['INTEGRATION_DATA']=folder
        from integration_init import initialize
        asyncio.run(initialize())
        import pytest
        result=pytest.main([str(ROOT/'backend/tests'),'--noconftest','-q','-p','no:cacheprovider'])
        if result:raise SystemExit(result)
        from fastapi.testclient import TestClient
        import integrated
        results=[]
        def check(name,ok):
            assert ok,name
            results.append(name)
        with TestClient(integrated.app,base_url='http://127.0.0.1:8050') as c:
            check('anonymous access blocked',c.get('/api/v1/ui/patients').status_code==401)
            check('original API also protected',c.post('/api/v1/patients',json={}).status_code==401)
            password=next(s.split('\t')[1] for s in (Path(folder)/'LOCAL_ACCOUNTS.txt').read_text(encoding='utf-8').splitlines() if s.startswith('staff\t'))
            r=c.post('/api/auth/login',json={'username':'staff','password':password})
            check('real login',r.status_code==200)
            check('CSRF required',c.post('/api/v1/patients',json={}).status_code==403)
            c.headers['X-CSRF-Token']=r.json()['csrf']
            check('cross-site blocked',c.post('/api/v1/patients',json={},headers={'Origin':'https://example.com'}).status_code==403)
            pid=c.post('/api/v1/patients',json={}).json()['id']
            def analyze(text):
                r=c.post('/api/v1/analyze',json={'patient_id':pid,'protocol_text':text})
                assert r.status_code==200,r.text
                return r.json()
            result=analyze('УЗИ малого таза. Полип эндометрия.')
            protocol_id=result['protocol_id'];rid=result['routes'][0]['id']
            check('specialist mapping preserved',result['routes'][0]['specialist']=='Оперирующий гинеколог')
            check('evidence saved',bool(result['findings'][0]['evidence_text']))
            detail=c.get(f'/api/v1/protocols/{protocol_id}').json()
            check('route linked to protocol',detail['routes'][0]['id']==rid)
            review=analyze('УЗИ малого таза. Миома матки.')
            rows=c.get('/api/v1/ui/patients').json()
            card=next(x for x in rows if x['protocolId']==protocol_id)
            review_card=next(x for x in rows if x['protocolId']==review['protocol_id'])
            check('manual review tied to its protocol',review_card['routeId']!=rid and review_card['targetDoctorSpec']=='Координатор')
            check('no invented probability',card['csScore'] is None)
            check('negation creates no route',analyze('УЗИ желчного пузыря. Конкременты не выявлены.')['routes']==[])
            check('foreign patient gives 404',c.post('/api/v1/analyze',json={'patient_id':999999,'protocol_text':'Миома матки.'}).status_code==404)
            check('invalid DOCX rejected',c.post(f'/api/v1/analyze/file?patient_id={pid}',files={'file':('bad.docx',b'bad')}).status_code==422)
            stream=io.BytesIO()
            with zipfile.ZipFile(stream,'w') as z:z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>УЗИ малого таза. Полип эндометрия.</w:t></w:r></w:p></w:body></w:document>')
            check('multipart upload through auth layer',c.post(f'/api/v1/analyze/file?patient_id={pid}',files={'file':('protocol.docx',stream.getvalue())}).status_code==200)
            edited=c.post('/api/v1/ui/route',json={'protocol_id':protocol_id,'specialist':'Гинеколог','reason':'Решение координатора'})
            check('manual route correction saved',edited.status_code==200)
            note=c.post(f'/api/v1/ui/routes/{rid}/notification',json={}).json()
            check('notification saved without false delivery',note['external_delivery'] is False and note['id']>0)
            again=c.post(f'/api/v1/ui/routes/{rid}/notification',json={}).json()
            check('notification duplicate suppressed',again['duplicate'] and again['id']==note['id'])
            slots=c.get(f'/api/v1/ui/routes/{rid}/slots').json()['slots']
            check('invented slot rejected',c.post(f'/api/v1/ui/routes/{rid}/book',json={'slot_id':'invalid'}).status_code==409)
            booked=c.post(f'/api/v1/ui/routes/{rid}/book',json={'slot_id':slots[0]['id']})
            check('booking persisted',booked.status_code==200 and c.get(f'/api/v1/routes/{rid}/appointments').json()[0]['id']==booked.json()['id'])
            check('duplicate booking blocked',c.post(f'/api/v1/ui/routes/{rid}/book',json={'slot_id':slots[0]['id']}).status_code==409)
            check('booked route cannot send booking reminder',c.post(f'/api/v1/ui/routes/{rid}/notification',json={}).status_code==409)
            row=next(x for x in c.get('/api/v1/ui/patients').json() if x['protocolId']==protocol_id)
            check('UI reflects persisted changes',row['stage']=='Запись зарегистрирована' and row['humanInterference'] and row['pushCount']==1)
            imp=c.post('/api/v1/ui/import-demo',json={});check('89 corpus protocols imported',imp.status_code==200 and imp.json()['created']==89)
            check('corpus import idempotent',c.post('/api/v1/ui/import-demo',json={}).json()['created']==0)
            check('logout revokes access',c.post('/api/auth/logout',json={}).status_code==200 and c.get('/api/v1/ui/patients').status_code==401)
        (ROOT/'verification.json').write_text(json.dumps({'original_tests':17,'integration_checks':len(results),'passed':results,'database':'isolated SQLite','postgresql_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
        print('INTEGRATION CHECKS PASSED:',len(results))

if __name__=='__main__':main()
