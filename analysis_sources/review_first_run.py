import csv, json, sys, importlib.util, zipfile, xml.etree.ElementTree as ET
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
root=Path.cwd()
spec=importlib.util.spec_from_file_location('summary',root/'s-pie/summarize.py'); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
for aqm in ['Red','CoDel','Pie','Spie']:
 p=root/f'data/result/{aqm}/s1-{aqm}-seed1-r1.csv'
 rows=list(mod.rows(p)); keys={(r['end_s'],r['flow']) for r in rows}
 assert len(rows)==len(keys)==3000
 assert all(abs(float(r['goodput_mbps'])-int(r['payload_bytes'])*8/1e6)<1e-8 for r in rows)
 results=[mod.summarize(p,a,b) for a,b in [(0,30),(0,20),(5,20)]]
 old={r['metric']:r['value'] for r in mod.rows(p.with_name(p.stem+'-summary.csv'))}
 for k,v in results[0].items():
  try: assert abs(float(v)-float(old[k]))<1e-8
  except ValueError: assert str(v)==old[k]
 trace={}
 for kind in ['queue','rtt','drops','link']:
  rr=list(mod.rows(p.with_name(p.stem+'-'+kind+'.csv'))); tt=[int(r['time_ns']) for r in rr]
  assert tt==sorted(tt)
  trace[kind]={'rows':len(rr),'end_s':tt[-1]/1e9}
  if kind=='queue':
   trace[kind]['min']=min(int(r['packets']) for r in rr); trace[kind]['max']=max(int(r['packets']) for r in rr)
  if kind=='rtt': trace[kind]['flow_count']=len({r['flow'] for r in rr})
 per=[]
 for end in [5,20]:
  rr=[r for r in rows if int(r['end_s'])==end]; x=[int(r['payload_bytes']) for r in rr]
  per.append({'end_s':end,'goodput':sum(x)*8/1e6,'jain':sum(x)**2/(100*sum(v*v for v in x))})
 print(json.dumps({'aqm':aqm,'checks':'passed','trace':trace,'windows':results,'point_windows':per}))
with zipfile.ZipFile(root/'Report NS3 DGHNM.docx') as z:
 tree=ET.fromstring(z.read('word/document.xml')); ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
 text=[''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in tree.findall('.//w:p',ns)]
 print('CURRENT_DOCX_TEXT\n'+'\n'.join(text))

