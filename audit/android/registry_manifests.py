import json,urllib.request,urllib.parse,concurrent.futures
from pathlib import Path
root=Path(__file__).resolve().parent
records=json.loads((root/'package-inspection.json').read_text())
def fetch(item):
 k,v=item;n,version=k.rsplit('@',1)
 url='https://registry.npmjs.org/'+urllib.parse.quote(n,safe='')+'/'+urllib.parse.quote(version,safe='')
 try:
  with urllib.request.urlopen(url,timeout=45) as r: data=json.load(r)
  return k,{'url':url,'manifest':{x:data[x] for x in ['name','version','scripts','bin','os','cpu','libc','gypfile','binary','dependencies','optionalDependencies','peerDependencies','bundledDependencies','bundleDependencies','dist','license'] if x in data}}
 except Exception as e:return k,{'url':url,'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
 result=dict(pool.map(fetch,[(k,v) for k,v in records.items() if not v['installed']]))
(root/'registry-manifests.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
print('Manifests',len(result),'errors',sum('error' in v for v in result.values()))

if any("error" in v for v in result.values()): raise SystemExit(1)
for key, value in result.items():
    if value['manifest']['dist']['integrity'] != records[key]['metadata']['resolution']['integrity']:
        raise RuntimeError(f'Registry/lock integrity mismatch: {key}')
