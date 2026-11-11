"""DeployLab: release simulation + real health checks and Prometheus metrics.
No cloud deployment or real deployment is performed by demo endpoints.
"""
from __future__ import annotations
import os, sqlite3, time
from contextlib import closing
from pathlib import Path
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field

ROOT=Path(__file__).resolve().parents[1]
DB=Path(os.getenv('DEPLOYLAB_DB',str(ROOT/'data'/'deploylab.sqlite3')))
DB.parent.mkdir(parents=True,exist_ok=True)
app=FastAPI(title='DeployLab release lab',version='1.0.0')
START=time.time()
REQUESTS={'health':0,'api':0,'deploy':0}

def dbconn():
    db=sqlite3.connect(DB)
    db.row_factory=sqlite3.Row
    return db

def initialize():
    with closing(dbconn()) as db:
        db.executescript('''CREATE TABLE IF NOT EXISTS releases(id INTEGER PRIMARY KEY AUTOINCREMENT, version TEXT NOT NULL, environment TEXT NOT NULL, status TEXT NOT NULL, action TEXT NOT NULL, actor TEXT NOT NULL, created_at TEXT NOT NULL, notes TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, message TEXT NOT NULL, created_at TEXT NOT NULL);
        ''')
        if not db.execute('SELECT 1 FROM releases LIMIT 1').fetchone():
            fixtures=[
              ('v2.8.4','production','success','deploy','GitHub Actions','2026-11-11 09:42','Mejoras de caché y observabilidad'),
              ('v2.8.3','production','success','deploy','GitHub Actions','2026-11-10 16:24','Hotfix de paginación en catálogo'),
              ('v2.8.2','staging','success','deploy','CI Pipeline','2026-11-10 11:15','Validación de pruebas de integración'),
              ('v2.8.1','production','rolled_back','rollback','Ops Team','2026-11-09 14:07','Reversión por aumento de errores'),
              ('v2.8.0','production','success','deploy','GitHub Actions','2026-11-07 10:16','Release de base y migraciones'),
              ('v2.7.9','staging','success','deploy','CI Pipeline','2026-11-06 15:41','Preproducción'),
            ]
            db.executemany('INSERT INTO releases(version,environment,status,action,actor,created_at,notes) VALUES(?,?,?,?,?,?,?)',fixtures)
            db.executemany('INSERT INTO audit(message,created_at) VALUES(?,?)',[
              ('v2.8.4 desplegada a producción (demo)','2026-11-11 09:42'),
              ('Pipeline #184 completado: 6/6 etapas','2026-11-11 09:38'),
              ('Monitoreo validado: health /ready','2026-11-11 09:36'),
              ('v2.8.1 revertida por operador','2026-11-09 14:07'),
            ])
        db.commit()
initialize()

def all_releases():
    with closing(dbconn()) as db:
        releases=[dict(x) for x in db.execute('SELECT * FROM releases ORDER BY created_at DESC, id DESC')]
        audit=[dict(x) for x in db.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 10')]
    # The seeded example has the most recent release first by ID; newest simulated actions append.
    return releases, audit

@app.get('/')
def index():return FileResponse(ROOT/'web'/'index.html')
@app.get('/assets/{name}')
def assets(name:str):
    if name not in ('app.css','app.js'):raise HTTPException(404)
    return FileResponse(ROOT/'web'/name)

@app.get('/health')
def health():
    REQUESTS['health']+=1
    return {'status':'healthy','service':'retail-api','version':'2.8.4'}

@app.get('/ready')
def ready():
    try:
        with closing(dbconn()) as db: db.execute('SELECT 1').fetchone()
        return {'status':'ready','database':'connected'}
    except sqlite3.Error: raise HTTPException(503,'Database unavailable')

@app.get('/api/overview')
def overview():
    REQUESTS['api']+=1
    releases,audit=all_releases()
    return {
      'service':'retail-api','environment':'production', 'releases':releases,'audit':audit,
      'stats':{'uptime':'99.98%','latency':42,'requests':'2.4M','deployments':len(releases),'errors':'0.12%'},
      'traffic':[47,62,58,73,67,88,84,94,72,103,96,114,98,111,106,128,120,117,131,126],
      'latencyTrend':[52,48,49,55,46,43,44,52,48,41,40,46,42,39,43,38],
      'pipeline':[
        {'name':'Source checkout','time':'3 s','status':'success'},
        {'name':'Install dependencies','time':'11 s','status':'success'},
        {'name':'Unit & API tests','time':'14 s','status':'success'},
        {'name':'Security scan','time':'7 s','status':'success'},
        {'name':'Docker image build','time':'22 s','status':'success'},
        {'name':'Image validation','time':'5 s','status':'success'},
      ],
      'services':[{'name':'retail-api','version':'2.8.4','healthy':True,'port':'8000'},
                  {'name':'prometheus','version':'v2.55','healthy':True,'port':'9090'},
                  {'name':'sqlite-store','version':'3.x','healthy':True,'port':'local'}]
    }

class ReleaseRequest(BaseModel):
    version:str=Field(min_length=2,max_length=32,pattern=r'^v\d+\.\d+\.\d+$')
    environment:str=Field(default='staging',pattern=r'^(staging|production)$')
    notes:str=Field(default='Demo local, sin infraestructura externa',max_length=160)

@app.post('/api/simulate/deploy',status_code=201)
def simulate_deploy(req:ReleaseRequest):
    """Records a simulated release; never calls Docker, cloud or Kubernetes."""
    now=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')
    with closing(dbconn()) as db:
        db.execute('INSERT INTO releases(version,environment,status,action,actor,created_at,notes) VALUES(?,?,?,?,?,?,?)',
                   (req.version,req.environment,'success','deploy','Local simulator',now,req.notes))
        db.execute('INSERT INTO audit(message,created_at) VALUES(?,?)',(f'Simulación de despliegue {req.version} a {req.environment}',now))
        db.commit()
    REQUESTS['deploy']+=1
    return {'status':'simulated','environment':req.environment,'version':req.version}

@app.post('/api/simulate/rollback/{release_id}')
def simulate_rollback(release_id:int):
    now=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')
    with closing(dbconn()) as db:
        row=db.execute('SELECT * FROM releases WHERE id=?',(release_id,)).fetchone()
        if not row:raise HTTPException(404,'Release not found')
        if row['status']=='rolled_back': raise HTTPException(409,'Already rolled back')
        db.execute('UPDATE releases SET status=? WHERE id=?',('rolled_back',release_id))
        db.execute('INSERT INTO audit(message,created_at) VALUES(?,?)',(f'Rollback simulado: {row["version"]} en {row["environment"]}',now))
        db.commit()
    return {'status':'rolled_back','release_id':release_id}

@app.get('/metrics',response_class=PlainTextResponse)
def metrics():
    REQUESTS['api']+=1
    seconds=int(time.time()-START)
    return ('# HELP deploylab_requests_total HTTP requests by type\n# TYPE deploylab_requests_total counter\n'
            + ''.join('deploylab_requests_total{type="%s"} %s\n'%(k,v) for k,v in REQUESTS.items())
            + '# HELP deploylab_uptime_seconds Seconds since app boot\n# TYPE deploylab_uptime_seconds gauge\n'
            + f'deploylab_uptime_seconds {seconds}\n')
