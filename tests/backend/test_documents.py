import io
from datetime import timedelta
from unittest.mock import patch
from pypdf import PdfWriter
from app import db
from app.pilot.models import Document,Job,now
from app.pilot.worker import run_once,TerminalFailure,parse_pdf,scan_clamav
from conftest import api,register,create_asset


def pdf():
    output = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100,height=100)
    writer.write(output)
    return output.getvalue()


def upload(client,asset,content=None,name='manual.pdf'):
    csrf = client.get('/api/v1/csrf').get_json()['csrf_token']
    return client.post('/api/v1/documents',data={'asset_id':str(asset['id']),'title':'Pump manual','file':(io.BytesIO(content if content is not None else pdf()),name)},headers={'X-CSRF-Token':csrf},content_type='multipart/form-data')


def test_private_quarantine_ready_reader_delete(app,client,owner):
    asset = create_asset(client)
    app.config['TEST_SCANNER'] = lambda content: True
    app.config['TEST_PARSER'] = lambda content: ['Verified text page']
    response = upload(client,asset)
    assert response.status_code==202,response.get_json()
    document = response.get_json()['document']
    assert document['status']=='quarantined'
    path = f"/api/v1/documents/{document['id']}"
    assert client.get(path+'/download').status_code==409
    assert client.get(path+'/pages/1').status_code==409
    assert run_once(app)['state']=='done'
    assert client.get(path).get_json()['document']['status']=='ready'
    assert client.get(path+'/pages/1').get_json()['text']=='Verified text page'
    downloaded = client.get(path+'/download')
    assert downloaded.status_code==200
    assert downloaded.headers['Content-Disposition'].startswith('attachment;')
    assert downloaded.data.startswith(b'%PDF-')
    other = app.test_client()
    register(app,other,'other@example.test','Other','Plant B')
    assert other.get(path).status_code==404
    assert other.get(path+'/download').status_code==404
    assert other.get(path+'/pages/1').status_code==404
    assert upload(other,asset).status_code==404
    assert api(client,f"/documents/{document['id']}",method='DELETE').status_code==200
    assert client.get(path+'/download').status_code==404
    assert client.get(path+'/pages/1').status_code==404


def test_scanner_failure_never_ready_and_lease_retry(app,client,owner):
    asset = create_asset(client)
    document = upload(client,asset).get_json()['document']
    def unavailable(content):
        raise OSError('Scanner offline')
    app.config['TEST_SCANNER'] = unavailable
    app.config['TEST_PARSER'] = lambda content:['Never accessed']
    assert run_once(app)['state']=='queued'
    row = client.get(f"/api/v1/documents/{document['id']}").get_json()['document']
    assert row['status']=='failed'
    assert 'queued for retry' in row['error']
    assert client.get(f"/api/v1/documents/{document['id']}/download").status_code==409
    with app.app_context():
        job = db.session.execute(db.select(Job).where(Job.kind=='document')).scalar_one()
        job.state = 'running'
        job.lease_until = now()-timedelta(seconds=1)
        job.lease_token = 'abandoned'
        db.session.commit()
    app.config['TEST_SCANNER'] = lambda content: True
    assert run_once(app)['state']=='done'
    assert client.get(f"/api/v1/documents/{document['id']}").get_json()['document']['status']=='ready'


def test_malware_invalid_pdf_and_delete_cancel_worker(app,client,owner):
    asset = create_asset(client)
    assert upload(client,asset,b'not pdf').status_code==400
    assert upload(client,asset,pdf(),'manual.exe').status_code==400
    app.config['PDF_MAX_BYTES']=10
    assert upload(client,asset).status_code==413
    app.config['PDF_MAX_BYTES']=10*1024*1024
    document = upload(client,asset).get_json()['document']
    def infected(content):
        raise TerminalFailure('Malware detected')
    app.config['TEST_SCANNER'] = infected
    assert run_once(app)['state']=='failed'
    assert client.get(f"/api/v1/documents/{document['id']}/download").status_code==409
    another = upload(client,asset).get_json()['document']
    assert api(client,f"/documents/{another['id']}",method='DELETE').status_code==200
    assert run_once(app)['processed']==0


def test_actual_isolated_parser_caps_and_active_content(app):
    with app.app_context():
        assert parse_pdf(pdf())==['']
        from app.pilot.sandbox_runner import ParserUnavailable, ParserRejected
        with patch('app.pilot.sandbox_runner._bounded_process',side_effect=ParserUnavailable('bounded timeout')):
            try:
                parse_pdf(pdf())
            except ParserUnavailable:
                pass
            else:
                raise AssertionError('Parser did not propagate timeout')
        writer = PdfWriter()
        writer.add_blank_page(width=100,height=100)
        from pypdf.generic import DictionaryObject, NameObject, TextStringObject
        writer._root_object[NameObject('/OpenAction')] = DictionaryObject({NameObject('/S'):NameObject('/JavaScript'),NameObject('/JS'):TextStringObject('app.alert("unsafe")')})
        output = io.BytesIO()
        writer.write(output)
        try:
            parse_pdf(output.getvalue())
        except ParserRejected as error:
            assert 'active content' in str(error)
        else:
            raise AssertionError('PDF active content was accepted')


def test_scanner_no_silent_clean_verdict(app):
    class FakeSocket:
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def settimeout(self,*args): pass
        def sendall(self,*args): pass
        def recv(self,*args): return b'stream: ERROR\0'
    with app.app_context(),patch('app.pilot.worker.socket.create_connection',return_value=FakeSocket()):
        try:
            scan_clamav(pdf())
        except RuntimeError as error:
            assert 'clean verdict' in str(error)
        else:
            raise AssertionError('Invalid scanner reply marked clean')
