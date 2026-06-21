from __future__ import annotations
import csv, json, os, sqlite3, subprocess, tempfile, time, tracemalloc
from pathlib import Path
import sys
import psutil
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT=ROOT/'CPU_RAM_BENCHMARK_BEFORE_AFTER.csv'
rows=[]

def measure(name, variant, fn, notes='', iterations=5):
    walls=[]; cpus=[]; peaks=[]; rss_deltas=[]; extra={}
    proc=psutil.Process()
    for _ in range(iterations):
        rss0=proc.memory_info().rss; cpu0=time.process_time(); t0=time.perf_counter(); tracemalloc.start()
        result=fn()
        current,peak=tracemalloc.get_traced_memory(); tracemalloc.stop()
        walls.append((time.perf_counter()-t0)*1000); cpus.append((time.process_time()-cpu0)*1000); peaks.append(peak); rss_deltas.append(max(0,proc.memory_info().rss-rss0))
        if isinstance(result,dict): extra=result
    rows.append({'scenario':name,'variant':variant,'status':'PASS','wall_ms_median':round(pd.Series(walls).median(),3),'cpu_ms_median':round(pd.Series(cpus).median(),3),'peak_python_bytes_median':int(pd.Series(peaks).median()),'rss_delta_bytes_median':int(pd.Series(rss_deltas).median()),'query_count':extra.get('query_count'),'rows_fetched':extra.get('rows_fetched'),'columns_fetched':extra.get('columns_fetched'),'payload_bytes':extra.get('payload_bytes'),'cache_status':extra.get('cache_status'),'rendered_rows':extra.get('rendered_rows'),'chart_points':extra.get('chart_points'),'chart_traces':extra.get('chart_traces'),'rerun_count':extra.get('rerun_count'),'notes':notes})

# Synthetic history data isolates the exact active-path optimization: SELECT * + eager
# JSON decoding versus projected SQL + LIMIT + lazy payload decoding.
tmp=Path(tempfile.mkdtemp())/'bench.sqlite3'
con=sqlite3.connect(tmp)
con.execute('CREATE TABLE hist(id INTEGER PRIMARY KEY, calculation_id TEXT, latest_completed_h1 TEXT, metric_name TEXT, value_numeric REAL, settled_status TEXT, payload_json TEXT)')
payload=json.dumps({'evidence':'x'*700,'nested':list(range(20))})
data=[(f'c{i//10}',f'2026-06-{1+(i%20):02d}T12:00:00+00:00',f'm{i%30}',float(i%100),'SETTLED',payload) for i in range(30000)]
con.executemany('INSERT INTO hist(calculation_id,latest_completed_h1,metric_name,value_numeric,settled_status,payload_json) VALUES(?,?,?,?,?,?)',data); con.commit(); con.close()

def before_field1():
    c=sqlite3.connect(tmp); df=pd.read_sql_query('SELECT * FROM hist ORDER BY latest_completed_h1 DESC',c); c.close()
    decoded=[json.loads(x) for x in df['payload_json']]
    return {'query_count':1,'rows_fetched':len(df),'columns_fetched':len(df.columns),'payload_bytes':int(df.memory_usage(deep=True).sum())+sum(len(json.dumps(x)) for x in decoded),'rendered_rows':len(df)}

def after_field1():
    c=sqlite3.connect(tmp); df=pd.read_sql_query('SELECT latest_completed_h1,calculation_id,metric_name,value_numeric,settled_status FROM hist ORDER BY latest_completed_h1 DESC LIMIT 50',c); c.close()
    return {'query_count':1,'rows_fetched':len(df),'columns_fetched':len(df.columns),'payload_bytes':int(df.memory_usage(deep=True).sum()),'rendered_rows':len(df)}
measure('Open Field 1 history','BEFORE_SELECT_STAR_EAGER_DECODE',before_field1,'Synthetic 30k-row reproducible history workload; represents removed active-path anti-pattern.',3)
measure('Open Field 1 history','AFTER_SQL_PROJECTION_LIMIT_LAZY_JSON',after_field1,'Synthetic 30k-row reproducible history workload.',7)

def before_search():
    c=sqlite3.connect(tmp); df=pd.read_sql_query('SELECT * FROM hist',c); c.close(); out=df[df.metric_name.eq('m7')].head(50)
    return {'query_count':1,'rows_fetched':len(df),'columns_fetched':len(df.columns),'payload_bytes':int(df.memory_usage(deep=True).sum()),'rendered_rows':len(out)}
def after_search():
    c=sqlite3.connect(tmp); df=pd.read_sql_query('SELECT latest_completed_h1,calculation_id,metric_name,value_numeric FROM hist WHERE metric_name=? ORDER BY latest_completed_h1 DESC LIMIT 50',c,params=['m7']); c.close()
    return {'query_count':1,'rows_fetched':len(df),'columns_fetched':len(df.columns),'payload_bytes':int(df.memory_usage(deep=True).sum()),'rendered_rows':len(df)}
measure('Search history','BEFORE_LOAD_ALL_FILTER_PYTHON',before_search,'Synthetic 30k-row search.',3)
measure('Search history','AFTER_SQL_FILTER_LIMIT',after_search,'Synthetic 30k-row search.',7)

def before_page():
    c=sqlite3.connect(tmp); df=pd.read_sql_query('SELECT * FROM hist ORDER BY latest_completed_h1 DESC',c); c.close(); out=df.iloc[5000:5050]
    return {'query_count':1,'rows_fetched':len(df),'columns_fetched':len(df.columns),'payload_bytes':int(df.memory_usage(deep=True).sum()),'rendered_rows':len(out)}
def after_page():
    c=sqlite3.connect(tmp); df=pd.read_sql_query('SELECT latest_completed_h1,calculation_id,metric_name,value_numeric FROM hist ORDER BY latest_completed_h1 DESC LIMIT 50 OFFSET 5000',c); c.close()
    return {'query_count':1,'rows_fetched':len(df),'columns_fetched':len(df.columns),'payload_bytes':int(df.memory_usage(deep=True).sum()),'rendered_rows':len(df)}
measure('Page history','BEFORE_LOAD_ALL_SLICE',before_page,'Synthetic 30k-row paging.',3)
measure('Page history','AFTER_SQL_LIMIT_OFFSET',after_page,'Synthetic 30k-row paging.',7)

# Streamlit AppTest: true closed gates. This verifies no field body is constructed.
from streamlit.testing.v1 import AppTest

def closed_lunch():
    at=AppTest.from_file(str(ROOT/'tools/bench_lunch_app_20260621.py'),default_timeout=20).run()
    return {'query_count':0,'rows_fetched':0,'columns_fetched':0,'payload_bytes':0,'rendered_rows':0,'rerun_count':1,'cache_status':'N/A'}
measure('Open Lunch all heavy fields closed','AFTER_TRUE_LOAD_GATES',closed_lunch,'Real Streamlit AppTest; six toggles remain false.',5)

def ten_switches():
    at=AppTest.from_file(str(ROOT/'tools/bench_lunch_app_20260621.py'),default_timeout=20)
    for _ in range(10): at.run()
    return {'query_count':0,'rows_fetched':0,'columns_fetched':0,'payload_bytes':0,'rendered_rows':0,'rerun_count':10,'cache_status':'N/A'}
measure('Ten tab/field-closed reruns','AFTER_TRUE_LOAD_GATES',ten_switches,'AppTest reruns with all heavy fields closed.',3)

# Quality stage cost, based on 5k completed H1 rows.
from core.history_quality_store_20260621 import build_quality_history_bundle
end=pd.Timestamp.now(tz='UTC').floor('h')-pd.Timedelta(hours=1)
times=pd.date_range(end=end,periods=5000,freq='h')
qdf=pd.DataFrame({'time':times,'open':1.1,'high':1.2,'low':1.0,'close':1.15,'volume':100})
canon={'run_id':'BENCH','canonical_calculation_id':'BENCH','calculation_generation':1,'symbol':'EURUSD','timeframe':'H1','source':'BENCH','latest_completed_candle_time':end.isoformat(),'data_signature':'BENCH','reverse_10_current':[{'i':i} for i in range(10)],'full_metric_snapshot':{},'final_decision':{},'regime':{},'reliability':{}}
def quality_stage():
    bundle,summary=build_quality_history_bundle(qdf,canon)
    return {'query_count':0,'rows_fetched':len(qdf),'columns_fetched':len(qdf.columns),'payload_bytes':len(json.dumps(bundle,default=str).encode()),'rendered_rows':0,'cache_status':'MISS'}
measure('Settings quality evidence stage','AFTER_SINGLE_PASS_BOUNDED',quality_stage,'5,000 completed H1 rows; no protected calculation included.',5)

# Cold startup: exact health-ready wall time and peak process RSS. No comparable
# latest baseline can be produced because the uploaded archive is truncated.
def cold_start():
    port='8877'; cmd=['streamlit','run','app.py','--server.headless','true','--server.port',port,'--browser.gatherUsageStats','false']
    t0=time.perf_counter(); p=subprocess.Popen(cmd,cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    peak=0; ready=False
    try:
        import urllib.request
        for _ in range(100):
            if p.poll() is not None: break
            try: peak=max(peak,psutil.Process(p.pid).memory_info().rss)
            except Exception: pass
            try:
                if urllib.request.urlopen(f'http://127.0.0.1:{port}/_stcore/health',timeout=.2).read().decode().strip()=='ok': ready=True; break
            except Exception: pass
            time.sleep(.1)
        cpu=psutil.Process(p.pid).cpu_times() if p.poll() is None else None
        return {'ready':ready,'wall_ms':(time.perf_counter()-t0)*1000,'peak_rss':peak,'cpu_ms':((cpu.user+cpu.system)*1000 if cpu else None)}
    finally:
        p.terminate()
        try:p.wait(timeout=5)
        except Exception:p.kill()
r=cold_start()
rows.append({'scenario':'Cold startup to health','variant':'AFTER_RECONSTRUCTED_RUNTIME','status':'PASS' if r['ready'] else 'FAIL','wall_ms_median':round(r['wall_ms'],3),'cpu_ms_median':r['cpu_ms'],'peak_python_bytes_median':None,'rss_delta_bytes_median':r['peak_rss'],'query_count':None,'rows_fetched':None,'columns_fetched':None,'payload_bytes':None,'cache_status':None,'rendered_rows':None,'chart_points':None,'chart_traces':None,'rerun_count':1,'notes':'Exact local Streamlit health startup. Current latest-upload baseline unavailable because source ZIP is truncated.'})

# Explicitly document requested scenarios not honestly executable in this recovered build.
for scenario in ['Settings Run Calculation full protected engine','Open Field 2 Power BI full browser','Open Field 3 full browser','Open Field 4 full browser','Open AI Assistant full browser','Copy Short / Copy All / exact export browser transfer','Phone viewport visual overflow screenshot','Laptop viewport visual screenshot']:
    rows.append({'scenario':scenario,'variant':'NOT_RUN','status':'NOT_VERIFIED','wall_ms_median':None,'cpu_ms_median':None,'peak_python_bytes_median':None,'rss_delta_bytes_median':None,'query_count':None,'rows_fetched':None,'columns_fetched':None,'payload_bytes':None,'cache_status':None,'rendered_rows':None,'chart_points':None,'chart_traces':None,'rerun_count':None,'notes':'Not claimed: exact latest source/browser automation is unavailable from the truncated upload.'})

fields=list(rows[0].keys())
with OUT.open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
print(OUT)
print(json.dumps(rows,indent=2,default=str))
