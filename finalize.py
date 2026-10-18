"""Apply replica-only presentation fixes after capture."""
from pathlib import Path
import re
root=Path(__file__).parent/'source'
count=0
fonts={}
fontdir=root/'external/fonts.googleapis.com'
if fontdir.exists():
 for p in fontdir.rglob('*'):
  if p.is_file() and p.suffix!='.css':
   new=p.with_name(p.name+'.css');fonts['/'+str(p.relative_to(root))]='/'+str(new.relative_to(root));p.rename(new)

for p in root.rglob('index.html'):
 s=p.read_text()
 s=re.sub(r'<script\b[^>]*src="/wp-content/plugins/contact-form-7/includes/(?:swv/)?js/index\.js[^"]*"[^>]*></script>','',s)
 s=re.sub(r'\sdata-nectar-img-srcset="[^"]*"','',s)
 for old,new in fonts.items():s=s.replace(old,new)
 # Remove a broken upstream Slick initializer that uses jQuery before its alias exists.
 s=re.sub(r'\$\(document\)\.ready\(function\(\)\{\s*\$\(\x27\.slick-track\x27\)\.slick\(\{\s*speed:\s*500\s*\}\);\s*\}\);','',s)
 # WordPress embeds these endpoints for server-backed plugins; presentation stays local.
 s=s.replace('https://westernequipments.com/wp-json/','/unavailable-api/').replace('https:\\/\\/westernequipments.com\\/wp-json\\/','/unavailable-api/')
 p.write_text(s);count+=1
print('Finalized',count,'pages')
