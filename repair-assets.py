"""Fill asset references stored in lazy loading and custom data attributes."""
from pathlib import Path
import re,json,subprocess,concurrent.futures as cf
from urllib.parse import unquote,urlsplit
r=Path(__file__).parent/'source';refs=set()
for p in r.rglob('*'):
 if not p.is_file() or p.suffix not in {'.html','.css'}:continue
 s=p.read_text(errors='replace')
 for v in re.findall(r'(/wp-(?:content|includes)/[^\s\"\'<>\\,;)]+)',s):
  v=urlsplit(v).path
  if re.search(r'\.(?:png|jpe?g|webp|svg|gif|css|js|woff2?|ttf|eot|pdf)$',v,re.I) and not (r/unquote(v).lstrip('/')).exists():refs.add(v)
print('Additional lazy-loading assets:',len(refs),flush=True)
def get(v):
 p=r/unquote(v).lstrip('/');p.parent.mkdir(parents=True,exist_ok=True)
 result=subprocess.run(['curl','-fsSL','--connect-timeout','8','--max-time','30','https://westernequipments.com'+v],capture_output=True)
 if result.returncode==0:p.write_bytes(result.stdout);return None
 return v
with cf.ThreadPoolExecutor(max_workers=8) as ex:failed=[x for x in ex.map(get,sorted(refs)) if x]
(Path(__file__).parent/'asset-repair-report.json').write_text(json.dumps({'requested':len(refs),'failed':failed},indent=2))
print('Asset repair failures:',len(failed),flush=True)
