"""Capture public pages and their presentation assets for a self-contained replica."""
import concurrent.futures as cf
import json, re, time, hashlib, subprocess
from pathlib import Path
from urllib.parse import urljoin, urlsplit, unquote
import requests
from bs4 import BeautifulSoup
BASE='https://westernequipments.com/'
ROOT=Path(__file__).parent/'dist'
CACHE=Path(__file__).parent/'.capture'
CACHE.mkdir(exist_ok=True)
ROOT.mkdir(exist_ok=True)
errors=[]; pages={}; assets={}; seen=set()
BLOCK=('googletagmanager','stats.wp.com','google-site-kit','woocommerce-analytics','activity-tracker','sourcebuster','order-attribution','wp-content-copy-protector','ajax-search-for-woocommerce/assets/js/search.min.js')
def fetch(url):
    key=CACHE/hashlib.sha256(url.encode()).hexdigest()
    if key.exists(): return key.read_bytes()
    if urlsplit(url).path.rstrip('/').split('/')[-1].find('.')<0 and urlsplit(url).netloc=='westernequipments.com' and not urlsplit(url).path.startswith(('/wp-content/','/wp-includes/')): return None
    r=subprocess.run(['curl','-fsSL','--connect-timeout','8','--max-time','25',url],capture_output=True)
    if r.returncode==0:
        key.write_bytes(r.stdout);return r.stdout
    errors.append([url,r.stderr.decode()[-300:]]);return None

def ispage(u):
    p=urlsplit(u)
    return p.netloc=='westernequipments.com' and not p.query and not re.search(r'\.[a-zA-Z0-9]{2,5}$',p.path) and not any(v in p.path for v in ['/wp-','/feed','/author/','/category/','/western2023/','/page/'])
def pageurl(u): return BASE.rstrip('/')+(urlsplit(u).path or '/')
def asseturl(u):
    u=urljoin(BASE,u).replace('&amp;','&')
    return u if not any(v in u for v in BLOCK) else None
def localasset(u):
    p=urlsplit(u)
    if p.netloc=='westernequipments.com': return p.path
    return '/external/'+p.netloc+p.path+('-'+hashlib.sha256(p.query.encode()).hexdigest()[:8] if p.query else '')
def refs(s,base):
    out=set()
    for x in s.select('[src],[srcset],[data-src],[data-srcset],[data-bg]'):
        for a in ['src','data-src','data-bg']:
            v=x.get(a,'')
            if v and not v.startswith(('data:','#')): out.add(urljoin(base,v))
        for a in ['srcset','data-srcset']:
            for v in x.get(a,'').split(','):
                if v.strip(): out.add(urljoin(base,v.strip().split()[0]))
    for x in s.select('link[href]'):
        if any(v in x.get('rel',[]) for v in ['stylesheet','icon','preload']): out.add(urljoin(base,x['href']))
    for v in re.findall(r'url\(\s*[\'\"]?([^\)\'\"\s]+)',str(s)):
        if not v.startswith('data:'): out.add(urljoin(base,v))
    for x in s.select('a[href]'):
        if re.search(r'\.(?:pdf|jpg|png|webp)(?:\?|$)',x['href'],re.I):out.add(urljoin(base,x['href']))
    for x in s.select('[data-menu-img-src]'):out.add(urljoin(base,x['data-menu-img-src']))
    return {asseturl(x) for x in out if asseturl(x)}
def prepare(url,data):
    s=BeautifulSoup(data,'html.parser')
    for x in s.select('[srcset],[data-srcset]'):
        v=x.get('srcset') or x.get('data-srcset','')
        if not x.get('src') or x.get('src','').startswith('data:'):
            choices=[z.strip().split()[0] for z in v.split(',') if z.strip() and not z.strip().startswith(('1x','2x'))]
            if choices:x['src']=choices[-1]
        x.attrs.pop('srcset',None);x.attrs.pop('data-srcset',None)
    for x in list(s.select('script')):
        content=x.get('src','') or x.get_text()
        if any(v in content for v in BLOCK) or ('gtag(' in content) or '_stq' in content: x.decompose()
    for x in list(s.select('link')):
        if any(v in x.get('rel',[]) for v in ['canonical','alternate','dns-prefetch','shortlink']):x.decompose()
    for x in list(s.select('script[type="application/ld+json"]')): x.decompose()
    for x in s.select('meta[property^="og:"],meta[name^="twitter:"]'): x.decompose()
    return s
queue=[BASE]
with cf.ThreadPoolExecutor(max_workers=8) as pool:
    while queue and len(pages)<400:
        batch=[u for u in dict.fromkeys(queue) if u not in pages][:400-len(pages)]
        queue=[]
        for u,data in zip(batch,pool.map(fetch,batch)):
            if not data: continue
            s=prepare(u,data);pages[u]=str(s)
            for a in s.select('a[href]'):
                v=urljoin(u,a['href'])
                if ispage(v) and pageurl(v) not in pages: queue.append(pageurl(v))
            for v in refs(s,u): assets[v]=localasset(v)
        print('Pages captured:',len(pages),'queued:',len(set(queue)),'assets:',len(assets),flush=True)
    pending=set(assets)
    while pending:
        batch=list(pending-seen);pending=set();seen.update(batch)
        for u,data in zip(batch,pool.map(fetch,batch)):
            if data is None:continue
            path=ROOT/unquote(assets[u]).lstrip('/');path.parent.mkdir(parents=True,exist_ok=True)
            if '.css' in urlsplit(u).path or 'fonts.googleapis.com' in u:
                css=data.decode('utf-8','replace')
                def repl(m):
                    v=m.group(1).strip(' \"\'')
                    if v.startswith(('data:','#')):return m.group(0)
                    a=asseturl(urljoin(u,v))
                    if not a:return m.group(0)
                    assets[a]=localasset(a)
                    if a not in seen: pending.add(a)
                    return 'url("'+assets[a]+'")'
                data=re.sub(r'url\(([^)]+)\)',repl,css).encode()
            path.write_bytes(data)
        print('Assets captured:',len(seen),'additional:',len(pending),flush=True)
# Replace all presentation asset references, longest URL first, including escaped variants.
search=[]
for u,html in pages.items():
    s=BeautifulSoup(html,'html.parser')
    for x in s.select('[src],[srcset],[data-src],[data-srcset],[data-bg],link[href]'):
        for a in ['src','data-src','data-bg','href']:
            v=x.get(a)
            if v and urljoin(u,v) in assets:x[a]=assets[urljoin(u,v)]
        for a in ['srcset','data-srcset']:
            if x.has_attr(a):x[a]=', '.join(assets.get(urljoin(u,v.strip().split()[0]),v.strip().split()[0])+(' '+' '.join(v.strip().split()[1:]) if len(v.strip().split())>1 else '') for v in x[a].split(',') if v.strip())
    for x in s.select('a[href]'):
        v=urljoin(u,x['href']); p=urlsplit(v)
        if p.netloc=='westernequipments.com':
            x['href']=p.path+('?' +p.query if p.query else '')+('#'+p.fragment if p.fragment else '')
            if x['href'].startswith('/western2023/'):x['href']=x['href'].replace('/western2023','',1)
    for x in s.select('form'):x['action']='#'
    tag=s.new_tag('script',src='/replica.js');s.body.append(tag)
    html=str(s)
    for prefix in ['https://westernequipments.com','http://westernequipments.com','//westernequipments.com']:
        html=html.replace(prefix+'/wp-content/','/wp-content/').replace(prefix+'/wp-includes/','/wp-includes/')
    p=ROOT/unquote(urlsplit(u).path).lstrip('/')/'index.html';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(html)
    title=s.title.get_text().split(' - ')[0] if s.title else u
    search.append({'title':title,'url':urlsplit(u).path})
(ROOT/'search-index.json').write_text(json.dumps(search))
(Path(__file__).parent/'capture-report.json').write_text(json.dumps({'pages':len(pages),'assets':len(seen),'errors':errors},indent=2))
print('DONE',len(pages),'pages;',len(seen),'assets;',len(errors),'failed requests',flush=True)
