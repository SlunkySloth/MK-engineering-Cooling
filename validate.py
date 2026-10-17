from pathlib import Path
from urllib.parse import urlsplit,unquote
from bs4 import BeautifulSoup
import json
root=Path(__file__).parent/'dist';missing={};links={};count=0
for p in root.rglob('index.html'):
 count+=1;s=BeautifulSoup(p.read_text(),'html.parser')
 for x in s.select('img[src],script[src],link[rel="stylesheet"][href]'):
  v=x.get('src') or x.get('href','')
  if v.startswith('/') and not v.startswith('//'):
   f=root/unquote(urlsplit(v).path).lstrip('/')
   if not f.exists():missing.setdefault(v,[]).append(str(p.relative_to(root)))
 for a in s.select('a[href]'):
  v=a['href']
  if v.startswith('/') and not v.startswith('//') and not urlsplit(v).query:
   f=root/unquote(urlsplit(v).path).lstrip('/')
   if not f.exists(): links.setdefault(v,[]).append(str(p.relative_to(root)))
report={'pages':count,'missing_assets':missing,'missing_link_targets':links}
(Path(__file__).parent/'validation-report.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'pages':count,'missing_assets':len(missing),'missing_link_targets':len(links)}))
