import os,tempfile
from pathlib import Path
os.environ['DEPLOYLAB_DB']=str(Path(tempfile.gettempdir())/'deploylab_pytest.sqlite3')
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def test_health_readiness():
    assert client.get('/health').json()['status']=='healthy'
    assert client.get('/ready').json()['database']=='connected'

def test_dashboard():
    data=client.get('/api/overview').json()
    assert len(data['pipeline'])==6
    assert len(data['releases'])>=6

def test_prometheus_metric_export():
    body=client.get('/metrics').text
    assert 'deploylab_requests_total' in body and 'deploylab_uptime_seconds' in body

def test_simulated_release_and_rollback():
    r=client.post('/api/simulate/deploy',json={'version':'v9.0.1','environment':'staging'})
    assert r.status_code==201 and r.json()['status']=='simulated'
    rows=client.get('/api/overview').json()['releases']
    created=next(row for row in rows if row['version']=='v9.0.1')
    assert client.post(f'/api/simulate/rollback/{created["id"]}').json()['status']=='rolled_back'
    assert client.post(f'/api/simulate/rollback/{created["id"]}').status_code==409

def test_invalid_version_and_missing_release():
    assert client.post('/api/simulate/deploy',json={'version':'bad','environment':'staging'}).status_code==422
    assert client.post('/api/simulate/rollback/9999999').status_code==404
