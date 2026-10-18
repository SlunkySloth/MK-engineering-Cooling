"""Responsive WebP derivatives of the captured images.

Templates call `Images.get(src, widths)`; each call registers the sizes it
needs and returns the URLs plus intrinsic dimensions. `Images.render()` then
writes any missing files in parallel. Output lives in dist/img/ and is reused
between builds when the source has not changed.
"""
import hashlib
import re
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image, ImageSequence

SIZE_SUFFIX = re.compile(r'-(\d+)x(\d+)(?=\.\w+$)')


def _convert(job):
    src, dst, width = job
    with Image.open(src) as im:
        if getattr(im, 'is_animated', False):
            im = next(ImageSequence.Iterator(im)).copy()
        im = im.convert('RGBA') if im.mode in ('P', 'LA', 'RGBA', 'PA') or 'transparency' in im.info else im.convert('RGB')
        if im.width > width:
            im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        if im.mode == 'RGBA' and im.getextrema()[3][0] == 255:
            im = im.convert('RGB')
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_suffix('.tmp')
        im.save(tmp, 'WEBP', quality=80, method=5)
        tmp.replace(dst)
    return dst


class Images:
    def __init__(self, source: Path, out: Path):
        self.source = source
        self.out = out
        self.jobs = {}
        self.sizes = {}

    def resolve(self, src):
        """Best local file for a site path, preferring the full-size original."""
        if not src or not src.startswith('/'):
            return None
        rel = src.split('?')[0].lstrip('/')
        f = self.source / rel
        full = self.source / SIZE_SUFFIX.sub('', rel)
        if full.exists():
            return full
        return f if f.exists() else None

    def dims(self, f):
        if f not in self.sizes:
            with Image.open(f) as im:
                self.sizes[f] = im.size
        return self.sizes[f]

    def get(self, src, widths=(480, 960)):
        f = self.resolve(src)
        if not f:
            return None
        w0, h0 = self.dims(f)
        widths = sorted({min(w, w0) for w in widths})
        stem = re.sub(r'[^A-Za-z0-9_-]+', '-', f.stem)[:60]
        tag = hashlib.sha1(str(f.relative_to(self.source)).encode()).hexdigest()[:8]
        urls = []
        for w in widths:
            name = f'{stem}-{tag}-{w}.webp'
            self.jobs[self.out / name] = (f, w)
            urls.append((f'/img/{name}', w))
        return {
            'src': urls[-1][0] if len(urls) == 1 else urls[min(1, len(urls) - 1)][0],
            'srcset': ', '.join(f'{u} {w}w' for u, w in urls),
            'width': widths[-1],
            'height': round(h0 * widths[-1] / w0),
            'ratio': w0 / h0,
        }

    def render(self):
        todo = [(src, dst, w) for dst, (src, w) in self.jobs.items()
                if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime]
        if todo:
            with ProcessPoolExecutor() as pool:
                list(pool.map(_convert, todo, chunksize=4))
        keep = set(self.jobs)
        removed = 0
        for f in self.out.glob('*.webp'):
            if f not in keep:
                f.unlink()
                removed += 1
        return len(todo), len(keep), removed
