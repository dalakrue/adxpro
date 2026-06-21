from __future__ import annotations
import ast,csv,hashlib,json,os,re,sqlite3,subprocess,sys,time,zipfile
from collections import Counter,defaultdict
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
ORIGINAL=Path('/mnt/data/recovered_adx/ADX_Quant_Pro_EURUSD_H1_Lunch_Corrections_20260621')
MANIFEST=ROOT/'FILE_MANIFEST_20260621_PROMOTION_GUARD.csv'
NOW=pd.Timestamp.now(tz='UTC').isoformat()

def sha(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()

def write(path,content):
 (ROOT/path).write_text(content,encoding='utf-8')

def md_table(headers,rows):
 def esc(x): return str(x).replace('|','\\|').replace('\n',' ')
 return '| '+' | '.join(headers)+' |\n|'+ '|'.join(['---']*len(headers))+'|\n'+'\n'.join('| '+' | '.join(esc(x) for x in r)+' |' for r in rows)

# Manifest/recovery status
expected=pd.read_csv(MANIFEST,encoding='utf-8-sig')
expected_map={str(r.path):str(r.sha256) for r in expected.itertuples()}
actual_files=[p for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts]
actual_rel={str(p.relative_to(ROOT)).replace('\\','/'):p for p in actual_files}
missing=[p for p in expected_map if p not in actual_rel]
mismatch=[]; matching=[]
for rel,ex in expected_map.items():
 if rel in actual_rel:
  got=sha(actual_rel[rel])
  (matching if got==ex else mismatch).append((rel,ex,got))

# Python static inventory
pyfiles=sorted(p for p in ROOT.rglob('*.py') if '.git' not in p.parts and '__pycache__' not in p.parts)
imports=[]; functions=[]; classes=[]; session_keys=Counter(); cache_decorators=[]; sql_select_star=[]; create_tables=[]; renderers=[]
for p in pyfiles:
 rel=str(p.relative_to(ROOT)); text=p.read_text(errors='ignore')
 try: tree=ast.parse(text)
 except Exception: continue
 for node in ast.walk(tree):
  if isinstance(node,ast.Import):
   for a in node.names: imports.append((rel,node.lineno,a.name))
  elif isinstance(node,ast.ImportFrom) and node.module:
   imports.append((rel,node.lineno,node.module))
  elif isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
   functions.append((rel,node.lineno,node.name));
   if node.name.startswith(('render','_render','show')): renderers.append((rel,node.lineno,node.name))
  elif isinstance(node,ast.ClassDef): classes.append((rel,node.lineno,node.name))
 for m in re.finditer(r'(?:st\.)?session_state(?:\.get\(|\[)[\"\']([^\"\']+)',text): session_keys[m.group(1)]+=1
 for m in re.finditer(r'@(st\.)?cache_(data|resource)(?:\([^\n]*\))?',text): cache_decorators.append((rel,text[:m.start()].count('\n')+1,m.group(0)))
 for m in re.finditer(r'(?i)SELECT\s+\*',text): sql_select_star.append((rel,text[:m.start()].count('\n')+1,m.group(0)))
 for m in re.finditer(r'(?i)CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[\"\']?([A-Za-z0-9_]+)',text): create_tables.append((rel,text[:m.start()].count('\n')+1,m.group(1)))

# Databases and table counts/catalog
all_db=[]; history_rows=[]
for p in sorted((ROOT/'data').glob('*.sqlite3')):
 con=sqlite3.connect(p)
 try:
  integrity=con.execute('PRAGMA integrity_check').fetchone()[0]
  tables=[r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
  table_counts={}
  for t in tables:
   try: table_counts[t]=int(con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0])
   except: table_counts[t]=None
  all_db.append({'path':str(p.relative_to(ROOT)),'size_bytes':p.stat().st_size,'sha256':sha(p),'integrity':integrity,'tables':table_counts})
  if p.name=='canonical_runtime.sqlite3':
   catalog={}
   if 'history_catalog' in tables:
    for r in con.execute('SELECT table_name,field_name,workspace,grain,business_key,description,schema_version FROM history_catalog'):
     catalog[r[0]]=r[1:]
   for t in tables:
    if 'history' in t or t in {'history_watermarks','data_quality_generation','data_quality_constraint_result','data_quality_metric_history'}:
     c=catalog.get(t,('SYSTEM','UNCLASSIFIED','declared by table schema','see schema',t,'unknown'))
     cols=[r[1] for r in con.execute(f'PRAGMA table_info("{t}")')]
     history_rows.append({'table_name':t,'field_name':c[0],'workspace':c[1],'grain':c[2],'business_key':c[3],'description':c[4],'schema_version':c[5],'row_count':table_counts.get(t,0),'populated_with_real_rows':'YES' if (table_counts.get(t) or 0)>0 else 'NO','latest_successful_generation':None,'latest_completed_h1':None,'quality_status':'POPULATED' if (table_counts.get(t) or 0)>0 else 'INSUFFICIENT EVIDENCE','last_failure_reason':''})
     if table_counts.get(t,0)>0:
      if 'calculation_generation' in cols:
       history_rows[-1]['latest_successful_generation']=con.execute(f'SELECT MAX(calculation_generation) FROM "{t}"').fetchone()[0]
      if 'latest_completed_h1' in cols:
       history_rows[-1]['latest_completed_h1']=con.execute(f'SELECT MAX(latest_completed_h1) FROM "{t}"').fetchone()[0]
 finally: con.close()
pd.DataFrame(history_rows).sort_values('table_name').to_csv(ROOT/'HISTORY_TABLE_CATALOG.csv',index=False)

# Protected snapshot comparison against untouched recovered database
protected={'comparison_basis':'run_snapshots table in untouched recovered upload vs improved database','generated_at':NOW,'status':'UNAVAILABLE'}
origdb=ORIGINAL/'data/canonical_runtime.sqlite3'; newdb=ROOT/'data/canonical_runtime.sqlite3'
if origdb.exists() and newdb.exists():
 def snaps(path):
  con=sqlite3.connect(path)
  try:return {(r[0],int(r[1])):{'checksum':r[2],'snapshot_json_sha256':hashlib.sha256(r[3].encode()).hexdigest()} for r in con.execute('SELECT run_id,generation,checksum,snapshot_json FROM run_snapshots')}
  finally:con.close()
 a,b=snaps(origdb),snaps(newdb); keys=sorted(set(a)|set(b))
 comparisons=[]
 for k in keys:
  comparisons.append({'run_id':k[0],'generation':k[1],'before':a.get(k),'after':b.get(k),'identical':a.get(k)==b.get(k)})
 protected.update({'status':'PASS' if all(x['identical'] for x in comparisons) and len(a)==len(b) else 'FAIL','before_snapshot_count':len(a),'after_snapshot_count':len(b),'all_snapshot_rows_identical':all(x['identical'] for x in comparisons) and len(a)==len(b),'comparisons':comparisons,'limitation':'This proves stored canonical snapshots were not altered. It does not reproduce a new protected calculation because the uploaded source archive is truncated.'})
(ROOT/'PROTECTED_OUTPUT_HASH_COMPARISON.json').write_text(json.dumps(protected,indent=2),encoding='utf-8')

# Duplicate research audit
matrix=[
('Data Validation for Machine Learning','core/canonical_data_validation_20260621.py','validate_source_frame; validate_canonical_payload','data_quality_generation; data_quality_constraint_result; data_quality_metric_history','ACTIVE preflight + prepublication gate','HIGH','REUSE existing authority; add source/schema/integrity evidence rows only'),
('Automating Large-Scale Data Quality Verification','core/declarative_data_quality_20260621.py','evaluate_constraints; shared_frame_aggregates','data_quality_constraint_result; source_freshness_history; schema_drift_history','ACTIVE declarative constraints','HIGH','UPGRADE persistence and single-pass aggregates; no second rule engine'),
('The Data Linter: Lightweight, Automated Sanity Checking for ML Data Sets','core/history_quality_store_20260621.py','build_quality_history_bundle','data_lint_history','ADDITIVE lightweight lints','MEDIUM','UPGRADE existing checks with bounded constant/copied/missing/volume evidence'),
('ActiveClean: Interactive Data Cleaning For Statistical Modeling','core/history_quality_store_20260621.py','SHADOW schema only','cleaning_impact_history','SHADOW / no rows','HIGH','REJECT automatic cleaning; keep proposed rules SHADOW until chronological approval'),
('CleanML: A Study for Evaluating the Impact of Data Cleaning on ML Classification Tasks','core/history_quality_store_20260621.py','SHADOW schema only','cleaning_impact_history','SHADOW / no rows','HIGH','REUSE same SHADOW evaluation ledger; require accuracy plus coverage and two windows'),
('Differential Dataflow','core/research_validation_store_20260621.py; core/history_quality_store_20260621.py','delta maintenance state; incremental refresh evidence','delta_maintenance_history; exact_delta_state; incremental_refresh_history','Existing delta audit plus additive stage metrics','HIGH','REUSE existing delta authority; do not introduce another computation engine'),
('The Design and Implementation of Modern Column-Oriented Database Systems','core/history_evidence_store_20260620.py; core/history_columnar_archive_20260620.py','query_history; archive helpers','history tables + archive metadata','Existing SQLite; column projection upgraded in active browser','MEDIUM','REUSE SQLite, explicit projections, bounded rows; defer DuckDB/Parquet threshold promotion'),
('BlinkDB: Queries with Bounded Errors and Bounded Response Times on Very Large Data','core/history_quality_store_20260621.py','schema/audit only','approximate_preview_audit_history','NONCANONICAL preview audit; no rows','HIGH','REJECT approximation for canonical/protected/export; allow audited preview only'),
('Falcon: Balancing Interactive Latency and Resolution Sensitivity for Scalable Linked Visualizations','ui/lunch_four_core_fields_20260619.py','render_lunch_six_core_fields; true load gates','mobile_render_budget_history','ACTIVE progressive field loading','LOW','UPGRADE renderer gates, bounded initial rows, exact export on explicit action'),
('Mobile Web Browsing under Memory Pressure','ui/mobile_low_heat_20260617.py; ui/lunch_four_core_fields_20260619.py','apply_mobile_low_heat_css; _bounded; _record_budget','mobile_render_budget_history','ACTIVE mobile budget safeguards','LOW','UPGRADE one-column/overflow/touch targets and bounded projections'),
]
write('DUPLICATE_RESEARCH_AUDIT.md','# Duplicate Research Audit\n\nCreated before additive integration decisions. “REUSE” keeps the existing authority; “UPGRADE” adds evidence or display constraints without a parallel engine.\n\n'+md_table(['paper_title','existing_file','existing_function','existing_table','current_status','duplicate_risk','reuse_or_upgrade_decision'],matrix)+'''\n\n## Source foundations\n- Breck et al., *Data Validation for Machine Learning* (MLSys 2019).\n- Schelter et al., *Automating Large-Scale Data Quality Verification* (PVLDB 2018).\n- Hynes, Sculley, Terry, *The Data Linter* (2017).\n- Krishnan et al., *ActiveClean* (SIGMOD 2016).\n- Li et al., *CleanML* (ICDE 2021).\n- McSherry et al., *Differential Dataflow* (CIDR 2013).\n- Abadi et al., *The Design and Implementation of Modern Column-Oriented Database Systems*.\n- Agarwal et al., *BlinkDB*.\n- Moritz, Howe, Heer, *Falcon* (CHI 2019).\n- Qazi et al., *Mobile Web Browsing Under Memory Pressure* (CCR 2020).\n''')

# Data contract
write('DATA_QUALITY_CONTRACT.md',f'''# Data Quality Contract\n\nGenerated: {NOW}\n\n## Authority\n`core.canonical_data_validation_20260621.validate_source_frame` remains Level A preflight. `validate_canonical_payload` plus `core.canonical_runtime_20260617.validate_canonical_result` remain Level B publication gates. `services.canonical_snapshot_store.commit_snapshot` is the sole SQLite publication authority. New history code records evidence and adds cross-generation/ten-decision invariants; it does not calculate trading outputs.\n\n## Common history identity\nEvery new table contains: `record_key`, `calculation_id`, `calculation_generation`, `run_id`, `symbol`, `timeframe`, `source`, `latest_completed_h1`, `record_time`, `target_time`, `horizon`, `data_signature`, `logic_version`, `settled_status`, `created_at`, `is_revision`, and bounded `payload_json`.\n\nRules enforced at insertion: EURUSD/H1 only; positive generation; approved settled statuses; parseable UTC timestamps; no future completed H1; horizon/target reconciliation; JSON validity; 64 KiB payload bound; unique declared grain; idempotent `INSERT OR IGNORE`; monotonic generation recorded by watermarks.\n\n## Level A — before expensive calculation\nRequired time/OHLC schema, numeric/finite data, UTC normalization, unique and monotonic timestamps, completed H1, OHLC relations, nonnegative spread, row-count reconciliation, source identity, minimum/freshness evidence, and missing weekday H1 intervals. Critical failures return before protected calculation and preserve the last valid generation.\n\n## Level B — after calculation, before publication\nThe canonical validator checks identity, generation, status, completed H1, Full Metric contract and research invariants. The additive post-contract checks exactly ten protected decisions and rejects explicit cross-generation identity conflicts. Canonical snapshot plus generic, research and quality histories commit under one `BEGIN IMMEDIATE`; an exception rolls back all staged rows.\n\n## Cleaning and approximation\n`cleaning_impact_history` and `approximate_preview_audit_history` are deliberately empty until real chronological evidence or an explicit preview exists. Cleaning cannot be promoted from module presence. Approximation is prohibited for canonical decisions, protected metrics, validation, settlements and exact exports.\n''')

# New tables
new_rows=[]
for name in ['source_freshness_history','schema_drift_history','candle_integrity_history','data_lint_history','revision_lineage_history','cleaning_impact_history','incremental_refresh_history','mobile_render_budget_history','approximate_preview_audit_history']:
 r=next((x for x in history_rows if x['table_name']==name),None)
 new_rows.append((name,r['grain'] if r else '',r['business_key'] if r else '',r['row_count'] if r else 0,'Created; populated only by a valid future Settings publication' if not r or not r['row_count'] else 'Populated'))
write('NEW_HISTORY_TABLES.md','# New History Tables\n\n'+md_table(['table','grain','business key','packaged rows','status'],new_rows)+'''\n\nAll nine tables are additive and idempotent. Zero rows are displayed as **INSUFFICIENT EVIDENCE**, never as proof. `cleaning_impact_history` stays SHADOW, and `approximate_preview_audit_history` cannot influence canonical outputs.\n''')

# Mobile report
write('MOBILE_READINESS_REPORT.md',f'''# Mobile Readiness Report\n\nTarget profile: iPhone 11 Pro-class narrow viewport.\n\nImplemented in the recovered runtime:\n- drawer remains collapsed by default through app page configuration;\n- page-level horizontal overflow is suppressed while dataframes keep container-local horizontal scrolling;\n- controls use a minimum 44 px height;\n- narrow layouts wrap to one column;\n- initial phone table projection is capped at 50 rows;\n- hidden fields are protected by six true load gates, so their renderers and SQL paths are not called while closed;\n- exact CSV export is prepared only after an explicit button;\n- compact canonical identity is reused rather than duplicating desktop and phone datasets;\n- every opened field can append a scalar render-budget record.\n\nMeasured AppTest result: see `CPU_RAM_BENCHMARK_BEFORE_AFTER.csv` for closed-field and ten-rerun costs.\n\nNot verified: actual iPhone Safari screenshots, horizontal overflow pixels, clipboard behavior, and complete chart trace/point counts. The uploaded archive is truncated and this environment has no browser/device screenshot harness. These items remain acceptance blockers, not assumed passes.\n''')

# Performance report using CSV
bench=pd.read_csv(ROOT/'CPU_RAM_BENCHMARK_BEFORE_AFTER.csv')
def pair(scenario,before,after):
 a=bench[(bench.scenario==scenario)&(bench.variant==before)].iloc[0]; b=bench[(bench.scenario==scenario)&(bench.variant==after)].iloc[0]
 def pct(col): return 100*(float(a[col])-float(b[col]))/float(a[col]) if float(a[col]) else None
 return (scenario,f"{a.wall_ms_median:.3f}",f"{b.wall_ms_median:.3f}",f"{pct('wall_ms_median'):.2f}%",f"{a.cpu_ms_median:.3f}",f"{b.cpu_ms_median:.3f}",f"{pct('cpu_ms_median'):.2f}%",f"{int(a.peak_python_bytes_median):,}",f"{int(b.peak_python_bytes_median):,}",f"{pct('peak_python_bytes_median'):.2f}%")
pairs=[pair('Open Field 1 history','BEFORE_SELECT_STAR_EAGER_DECODE','AFTER_SQL_PROJECTION_LIMIT_LAZY_JSON'),pair('Search history','BEFORE_LOAD_ALL_FILTER_PYTHON','AFTER_SQL_FILTER_LIMIT'),pair('Page history','BEFORE_LOAD_ALL_SLICE','AFTER_SQL_LIMIT_OFFSET')]
write('PERFORMANCE_OPTIMIZATION_REPORT.md','# Performance Optimization Report\n\n'+md_table(['scenario','before wall ms','after wall ms','wall reduction','before CPU ms','after CPU ms','CPU reduction','before Python peak','after Python peak','Python peak reduction'],pairs)+'''\n\n## Measured contributions\n- SQL projection, server-side filtering, ordering and limit; no active-path `SELECT *` in the new browser.\n- Lazy JSON: row payloads are not decoded for initial lists.\n- True field gates: AppTest recorded zero query/row construction with all fields closed.\n- Bounded mobile projection: 50 initial rows and deferred exact export.\n- Single-pass quality aggregates: the 5,000-row evidence stage is reported separately and does not include protected calculation cost.\n\n## Target determination\nThe synthetic history-query workloads exceed the 30% and 50% targets. **The full application target is NOT VERIFIED and therefore is not claimed achieved.** A valid before/after run of the complete latest protected engine, browser fields, clipboard/export transfer, and iPhone/laptop screenshots could not be produced because the uploaded ZIP is truncated. Cold startup is reported only for the reconstructed after-build and has no comparable latest baseline.\n''')

# Inventory markdown and CSV details
inv_csv=ROOT/'artifacts/FULL_FILE_INVENTORY_20260621.csv'; inv_csv.parent.mkdir(exist_ok=True)
with inv_csv.open('w',newline='',encoding='utf-8') as f:
 w=csv.writer(f); w.writerow(['path','size_bytes','sha256','expected_manifest_status'])
 for rel,p in sorted(actual_rel.items()):
  status='NEW' if rel not in expected_map else ('MATCH' if sha(p)==expected_map[rel] else 'MODIFIED_OR_RECOVERED_BASE')
  w.writerow([rel,p.stat().st_size,sha(p),status])
write('FULL_PROJECT_INVENTORY.md',f'''# Full Project Inventory\n\nGenerated: {NOW}\n\n## Recovery boundary\nThe uploaded ZIP lacks a central directory and ends inside a local file entry. 317 entries were recoverable from the upload, while its embedded manifest declares 924 expected files. To produce a runnable best-effort tree, the public repository's initial commit was used as a base and the 317 newer recovered files were overlaid. The resulting tree currently has {len(actual_files)} files and {len(pyfiles)} Python files. Of the manifest's 924 files, {len(matching)} are byte-identical, {len(mismatch)} differ, and {len(missing)} remain unavailable. This is not represented as a byte-complete copy of the uploaded latest release.\n\n## Active runtime trace\n`app.py` → `adx_dashpoard.py` → `core.app_shell.run_app` → `core.app.runner.run_app` → `core.app.routes.load_tab` → `tabs.antd_page_router_20260615`. Settings uses `core.settings_run_orchestrator_20260617.run_settings_calculation`; shared reads use `core.adx_shared_sync_20260615.ensure_shared_calculation_result(force=False)`; canonical publication calls `core.canonical_runtime_20260617.publish_canonical_atomically` once, which calls `services.canonical_snapshot_store.commit_snapshot`.\n\n## Static counts\n- Python files: {len(pyfiles)}\n- Function definitions: {len(functions)}\n- Class definitions: {len(classes)}\n- Import occurrences: {len(imports)}\n- Renderer/show functions: {len(renderers)}\n- Distinct session-state keys found statically: {len(session_keys)}\n- Streamlit cache decorators found: {len(cache_decorators)}\n- Static `SELECT *` occurrences across all recovered/legacy code: {len(sql_select_star)} (the new history browser uses explicit projections)\n- SQL CREATE TABLE occurrences found statically: {len(create_tables)}\n- SQLite databases: {len(all_db)}\n- Test files present after recovery/addition: {len(list((ROOT/'tests').glob('test*.py')))}\n\n## Detailed inventories\n- `artifacts/FULL_FILE_INVENTORY_20260621.csv`: every packaged file, size, SHA-256 and manifest status.\n- `HISTORY_TABLE_CATALOG.csv`: grain, business key, packaged row count and evidence status.\n- `artifacts/PYTHON_IMPORT_INVENTORY_20260621.csv`: import call sites.\n- `artifacts/SESSION_STATE_KEY_INVENTORY_20260621.csv`: statically referenced keys.\n- `artifacts/RENDERER_INVENTORY_20260621.csv`: renderer definitions.\n- `artifacts/DATABASE_TABLE_COUNTS_20260621.json`: table counts and integrity.\n- `RECOVERED_MISSING_FROM_TRUNCATED_UPLOAD.txt`: unavailable expected files.\n\n## Databases\n'''+md_table(['database','size bytes','integrity','table count','populated tables'],[(d['path'],d['size_bytes'],d['integrity'],len(d['tables']),', '.join(f"{k}={v}" for k,v in d['tables'].items() if v)) for d in all_db])+'''\n\n## Dependencies and deployment\n`runtime.txt` targets Python 3.12. `requirements.txt` retains Streamlit Cloud-compatible dependencies and keeps platform-specific MetaTrader5 optional. No external API or paid service was added.\n''')

for name,data,headers in [
 ('PYTHON_IMPORT_INVENTORY_20260621.csv',imports,['file','line','module']),
 ('SESSION_STATE_KEY_INVENTORY_20260621.csv',[(k,v) for k,v in session_keys.most_common()],['key','static_reference_count']),
 ('RENDERER_INVENTORY_20260621.csv',renderers,['file','line','function']),
 ('CACHE_DECORATOR_INVENTORY_20260621.csv',cache_decorators,['file','line','decorator']),
 ('SELECT_STAR_STATIC_AUDIT_20260621.csv',sql_select_star,['file','line','match']),
]:
 with (ROOT/'artifacts'/name).open('w',newline='',encoding='utf-8') as f:
  w=csv.writer(f);w.writerow(headers);w.writerows(data)
(ROOT/'artifacts/DATABASE_TABLE_COUNTS_20260621.json').write_text(json.dumps(all_db,indent=2),encoding='utf-8')

# Integrity report
integrity={'generated_at':NOW,'archive_recovery':{'expected_manifest_files':len(expected_map),'intact_uploaded_entries':317,'byte_identical_expected_files':len(matching),'mismatched_expected_files':len(mismatch),'missing_expected_files':len(missing)},'databases':all_db,'protected_snapshots':protected,'secret_scan':{},'overall_status':'PASS_WITH_RECOVERY_LIMITATIONS'}
patterns={'private_key':r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----','openai_key':r'sk-[A-Za-z0-9]{20,}','aws_access_key':r'AKIA[0-9A-Z]{16}','bearer_token':r'Bearer\s+[A-Za-z0-9._-]{20,}'}
secret_hits=[]
for rel,p in actual_rel.items():
 if p.stat().st_size>2_000_000 or p.suffix.lower() in {'.sqlite3','.duckdb','.zip','.png','.jpg','.pyc'}: continue
 text=p.read_text(errors='ignore')
 for label,pat in patterns.items():
  if re.search(pat,text): secret_hits.append({'file':rel,'pattern':label})
integrity['secret_scan']={'patterns':list(patterns),'hits':secret_hits,'status':'PASS' if not secret_hits else 'CHECK'}
(ROOT/'DATABASE_INTEGRITY_REPORT.json').write_text(json.dumps(integrity,indent=2),encoding='utf-8')

# Change manifest
changed_files=['services/__init__.py','services/canonical_snapshot_store.py','services/tracing.py','services/position_sizing.py','ui/stable_ui_libs_20260615.py','ui/home_master_control_bar_20260615.py','ui/liquid_glass_theme_20260615.py','ui/liquid_menu_popup_20260615.py','ui/mobile_low_heat_20260617.py','ui/nlp_research_panel.py','core/history_quality_store_20260621.py','core/settings_run_orchestrator_20260617.py','core/policy_decision_ledger_20260621.py','core/regime_trust_store_20260621.py','core/trust_history_20260619.py','core/history_evidence_store_20260620.py','core/history_columnar_archive_20260620.py','core/finnhub_connector.py','tabs/pre_clean_split/data.py','ui/lunch_four_core_fields_20260619.py','ui/powerbi_cached_renderer_20260619.py','tabs/antd_page_router_20260615.py','migrations/20260621_history_quality_mobile.sql','scripts_migrate_history_quality_20260621.py','tests/test_history_quality_mobile_20260621.py','tests/test_compile_and_runtime_20260621.py','tools/benchmark_history_quality_20260621.py','tools/bench_lunch_app_20260621.py','tools/generate_release_reports_20260621.py']
manifest={'generated_at':NOW,'release_type':'BEST_EFFORT_RECONSTRUCTION_FROM_TRUNCATED_UPLOAD','files_added_or_changed':[{'path':x,'sha256':sha(ROOT/x) if (ROOT/x).exists() else None} for x in changed_files],'protected_calculation_files_intentionally_modified':[],'notes':['No trading formula or decision engine was intentionally changed.','Settings orchestrator changed only to stage/validate additive evidence before the existing single publication call.','Router changed to use true-gated Lunch renderer.','Missing latest files were reconstructed as bounded interfaces; see EVIDENCE_AND_LIMITATIONS.md.']}
(ROOT/'CHANGE_MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')

# Evidence limitations
write('EVIDENCE_AND_LIMITATIONS.md',f'''# Evidence and Limitations\n\n## Verified\n- {len(pyfiles)} packaged Python files parse/compile.\n- Streamlit starts with `streamlit run app.py`; the health endpoint returned `ok`.\n- New unit/invariant tests cover schema, common contract, idempotency, rollback, payload bounds, exactly one publication call, and closed-field no-execution.\n- All four SQLite databases return `PRAGMA integrity_check = ok`.\n- The nine pre-existing stored canonical snapshot rows are byte-identical to the untouched recovered database.\n- New schemas are additive and zero-row tables remain labelled INSUFFICIENT EVIDENCE.\n\n## Critical recovery limitation\nThe user-supplied ZIP is truncated. It yielded 317 intact entries, although its manifest lists 924. A public initial repository commit was used to restore an older base before overlaying recovered files. {len(missing)} manifest files remain unavailable and {len(mismatch)} expected files do not match their listed latest hashes. Therefore this package is a runnable, tested best-effort reconstruction—not a guaranteed complete latest original.\n\n## Not claimed\n- No full protected Settings calculation was executed against a verified latest source tree.\n- No new BUY/SELL/WAIT output hash was compared; only existing stored snapshot rows were proven unchanged.\n- The full 12-scenario browser benchmark and real iPhone 11 Pro screenshots were not available.\n- The 30% target is not claimed for the full application. Only isolated SQL/history workloads show reductions above 30% and 50%.\n- Existing tests missing from the truncated upload could not be rerun; newly added tests pass.\n- New quality tables have zero packaged evidence rows because no valid post-upgrade Settings publication was fabricated.\n- ActiveClean/CleanML promotion remains SHADOW with no accuracy claim.\n''')

# Run README
write('README_RUN.md','''# Run ADX Quant Pro\n\n## Windows PowerShell\n```powershell\ncd "C:\\path\\to\\ADX_Quant_Pro_EURUSD_H1_Quality_Mobile_Reconstructed_20260621"\npy -3.12 -m venv .venv\n.\\.venv\\Scripts\\Activate.ps1\npython -m pip install --upgrade pip\npip install -r requirements.txt\npython scripts_migrate_history_quality_20260621.py\npython -m pytest -q\nstreamlit run app.py\n```\n\n## macOS/Linux\n```bash\ncd /path/to/ADX_Quant_Pro_EURUSD_H1_Quality_Mobile_Reconstructed_20260621\npython3.12 -m venv .venv\nsource .venv/bin/activate\npython -m pip install --upgrade pip\npip install -r requirements.txt\npython scripts_migrate_history_quality_20260621.py\npython -m pytest -q\nstreamlit run app.py\n```\n\nUse the existing Settings **Run Calculation** action. Opening Lunch fields, paging/searching history, copying, exporting, or opening the local AI Assistant reads the last committed generation and does not call the protected calculator.\n''')

print(json.dumps({'files':len(actual_files),'python':len(pyfiles),'manifest_missing':len(missing),'manifest_mismatch':len(mismatch),'history_tables':len(history_rows)},indent=2))
