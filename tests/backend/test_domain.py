from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy.exc import IntegrityError
from app import db
from app.models import Asset, Location
from app.pilot.models import WorkEvent, WorkOrder, Membership
from conftest import api,register,mail_token,create_asset


def test_registry_two_tenants_hierarchy_and_revision(app,client,owner):
    site = api(client,'/locations',{'name':'Site A','type':'Site'}).get_json()['location']
    area = api(client,'/locations',{'name':'Area A','type':'Area','parent_id':site['id']}).get_json()['location']
    assert api(client,'/locations',{'name':'Wrong','type':'Line','parent_id':site['id']}).status_code==400
    asset = create_asset(client)
    assert asset['telemetry_status']=='not_connected'
    with app.app_context():
        assert db.session.get(Asset,asset['id']).to_dict()['template_name'] is None
    assert api(client,f"/assets/{asset['id']}",{'revision':1,'location_id':area['id']},'PATCH').status_code==200
    assert api(client,f"/assets/{asset['id']}",{'revision':1,'name':'Stale'},'PATCH').status_code==409
    assert api(client,'/assets',{'code':'PUMP-01','name':'Duplicate'}).status_code==409
    other = app.test_client()
    other_owner = register(app,other,'other@example.test','Other','Plant B')
    same = create_asset(other)
    assert same['name']==asset['name']
    assert other.get(f"/api/v1/assets/{asset['id']}").status_code==404
    assert api(other,'/assets',{'code':'P2','name':'Foreign','location_id':area['id']}).status_code==404
    with app.app_context():
        foreign = Asset(company_id=other_owner['company']['id'],location_id=area['id'],name='DB foreign',code='DB',criticality='medium')
        db.session.add(foreign)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_assigned_work_order_lifecycle_replay_and_export(app,client,owner):
    asset = create_asset(client)
    tech = app.test_client()
    assert api(client,'/invitations',{'email':'tech@example.test','role':'technician'}).status_code==201
    assert api(tech,'/invitations/accept',{'token':mail_token(app,'invite'),'name':'Technician','password':'Technician-safe-password-89!'}).status_code==200
    assert api(tech,'/auth/login',{'email':'tech@example.test','password':'Technician-safe-password-89!'}).status_code==200
    tid = tech.get('/api/v1/auth/me').get_json()['membership']['id']
    body = {'asset_id':asset['id'],'title':'=unsafe formula','assignee_id':tid,'checklist':[{'text':'Inspect belt'}]}
    created = api(client,'/work-orders',body,key='create-order-001')
    assert created.status_code==201,created.get_json()
    order = created.get_json()['work_order']
    assert api(client,'/work-orders',body,key='create-order-001').get_json()==created.get_json()
    assert api(client,'/work-orders',{**body,'title':'Mismatch'},key='create-order-001').status_code==409
    path = f"/work-orders/{order['id']}/transition"
    assert api(client,path,{'revision':1,'action':'start'},key='start-denied-001').status_code==403
    assert api(tech,path,{'revision':1,'action':'approve'},key='approve-denied-001').status_code==403
    assert api(tech,path,{'revision':1,'action':'start'},key='start-order-001').status_code==200
    assert api(tech,path,{'revision':1,'action':'block','notes':'Stale'},key='stale-order-001').status_code==409
    assert api(tech,path,{'revision':2,'action':'block'},key='block-empty-001').status_code==400
    assert api(tech,path,{'revision':2,'action':'block','notes':'Waiting for access'},key='block-order-001').status_code==200
    assert api(tech,path,{'revision':3,'action':'resume'},key='resume-order-001').status_code==200
    assert api(tech,path,{'revision':4,'action':'submit','notes':'Checked'},key='submit-incomplete-001').status_code==400
    payload = {'revision':4,'action':'submit','notes':'Belt checked and safe','checklist':[{'text':'Inspect belt','completed':True}],'labor_minutes':25}
    assert api(tech,path,payload,key='submit-order-001').status_code==200
    assert api(client,path,{'revision':5,'action':'approve','notes':'Reviewed'},key='approve-order-001').status_code==200
    history = client.get(f"/api/v1/work-orders/{order['id']}").get_json()
    assert history['work_order']['status']=='completed'
    assert history['work_order']['completion_notes']=='Belt checked and safe'
    assert [e['action'] for e in history['events']]==['create','start','block','resume','submit','approve']
    exported = tech.get(f"/api/v1/work-orders/{order['id']}/export")
    assert exported.status_code==200
    assert "'=unsafe formula" in exported.text
    assert 'Belt checked and safe' in exported.text
    assert api(client,f"/assets/{asset['id']}",method='DELETE').status_code==200
    assert client.get(f"/api/v1/work-orders/{order['id']}").status_code==200
    summary = client.get('/api/v1/summary').get_json()
    assert summary['asset_count']==0 and summary['completed_work_order_count']==1
    assert api(client,path,{'revision':6,'action':'reopen','notes':'Follow up'},key='reopen-order-001').status_code==200


def test_foreign_job_links_and_viewer_mutations(app,client,owner):
    asset = create_asset(client)
    other = app.test_client()
    second = register(app,other,'other@example.test','Other','Plant B')
    foreign = create_asset(other,code='FOREIGN')
    assert api(client,'/work-orders',{'asset_id':foreign['id'],'title':'Foreign'},key='foreign-order-001').status_code==404
    assert api(client,'/work-orders',{'asset_id':asset['id'],'title':'Foreign assignee','assignee_id':second['membership']['id']},key='foreign-order-002').status_code==404
    viewer = app.test_client()
    assert api(client,'/invitations',{'email':'viewer@example.test','role':'viewer'}).status_code==201
    assert api(viewer,'/invitations/accept',{'token':mail_token(app,'invite'),'name':'Viewer','password':'Viewer-safe-password-89!'}).status_code==200
    assert api(viewer,'/auth/login',{'email':'viewer@example.test','password':'Viewer-safe-password-89!'}).status_code==200
    assert viewer.get('/api/v1/assets').status_code==200
    assert api(viewer,'/work-orders',{'asset_id':asset['id'],'title':'Denied'},key='viewer-order-001').status_code==403
    assert api(client,'/work-orders',{'asset_id':asset['id'],'title':'Missing key'}).status_code==400


def test_parallel_maintenance_idempotency(app,client,owner):
    asset = create_asset(client)
    # Share an authenticated cookie across isolated clients, not Flask test-client objects.
    cookie = client.get_cookie('machivital_session').value
    body = {'asset_id':asset['id'],'title':'Only one order'}
    def create(_):
        worker = app.test_client()
        worker.set_cookie('machivital_session',cookie)
        return api(worker,'/work-orders',body,key='parallel-create-001')
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create,range(2)))
    assert [r.status_code for r in results]==[201,201]
    assert results[0].get_json()==results[1].get_json()
    with app.app_context():
        assert len(db.session.execute(db.select(WorkOrder)).scalars().all())==1
        assert len(db.session.execute(db.select(WorkEvent)).scalars().all())==1
