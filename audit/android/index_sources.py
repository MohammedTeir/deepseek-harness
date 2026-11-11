from pathlib import Path
import json,re,subprocess,hashlib,collections
root=Path(__file__).resolve().parents[2]; out=root/'audit/android'
tracked=subprocess.check_output(['git','ls-files','apps','packages','native','vendor','python'],text=True).splitlines()
modules=collections.defaultdict(list); platform=[]; native=[]
for name in tracked:
 p=root/name
 if p.suffix in {'.c','.cc','.cpp','.rs','.gyp'} or p.name in {'CMakeLists.txt','Cargo.toml','prebuilds.json'}:native.append(name)
 if p.suffix not in {'.ts','.tsx','.js','.mjs','.cjs'} or '/src/' not in name:continue
 text=p.read_text()
 for i,line in enumerate(text.splitlines(),1):
  for m in re.findall(r'[\'\"]node:([a-z_/]+)[\'\"]',line):modules[m].append(f'{name}:{i}')
  if re.search(r'process.platform|/bin/bash|/proc/|node-pty|koffi|child_process',line):platform.append({'file':name,'line':i,'text':line.strip()})
(out/'source-api-index.json').write_text(json.dumps({'nodeModules':modules,'platformSites':platform,'nativeSourceAndMatrices':native},indent=2,sort_keys=True)+'\n')
g=json.load(open(out/'dependency-graph.json'));ins=json.load(open(out/'package-inspection.json'))
adj=collections.defaultdict(list)
for e in g['edges']:adj[e['from']].append(e)
roots=['apps/cli','packages/bundle/sdk-minimal','apps/web','apps/desktop']
paths={}
for r in roots:
 start='workspace:'+r;seen={start:[]};q=collections.deque([start])
 while q:
  n=q.popleft()
  for e in adj[n]:
   if r not in ['apps/web','apps/desktop'] and e['kind']=='devDependencies':continue
   if e['to'] not in seen:seen[e['to']]=seen[n]+[{'name':e['name'],'kind':e['kind'],'to':e['to']}];q.append(e['to'])
 paths[r]={n:p for n,p in seen.items() if n.startswith('package:') and (ins[g['nodes'][n]['key']]['payloads'] or ins[g['nodes'][n]['key']]['signals'] or any(x in g['nodes'][n]['metadata'] for x in ['os','cpu','libc']))}
(out/'native-dependency-paths.json').write_text(json.dumps(paths,indent=2,sort_keys=True)+'\n')
print('Node API modules',len(modules),'platform sites',len(platform),'native source/matrices',len(native),'native paths', {k:len(v) for k,v in paths.items()})
