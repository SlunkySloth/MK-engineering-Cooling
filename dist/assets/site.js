/* Site behaviour: navigation, search, carousels, gallery, catalogue filters,
   compare and enquiry forms. Every feature is optional: pages work without JS. */
(() => {
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const store = {
    get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} },
  };
  const SITE = window.SITE || {};

  /* Header shadow */
  const header = $('.header');
  const onScroll = () => header && header.classList.toggle('is-scrolled', scrollY > 8);
  addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* Mobile drawer */
  const drawer = $('#drawer');
  const toggleDrawer = open => {
    if (!drawer) return;
    drawer.classList.toggle('is-open', open);
    drawer.setAttribute('aria-hidden', String(!open));
    document.body.style.overflow = open ? 'hidden' : '';
    $$('[data-drawer-open]').forEach(b => b.setAttribute('aria-expanded', String(open)));
    if (open) $('.drawer__head button', drawer)?.focus();
  };
  $$('[data-drawer-open]').forEach(b => b.addEventListener('click', () => toggleDrawer(true)));
  $$('[data-drawer-close]').forEach(b => b.addEventListener('click', () => toggleDrawer(false)));
  drawer?.addEventListener('click', e => { if (e.target.closest('a')) toggleDrawer(false); });

  /* Close desktop menus on Escape */
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && document.activeElement?.closest('.nav__item')) document.activeElement.blur();
    if (e.key === 'Escape' && drawer?.classList.contains('is-open')) toggleDrawer(false);
  });

  /* Search palette */
  const searchDialog = $('#search');
  let index = null;
  const loadIndex = () => index || (index = fetch('/search-index.json').then(r => r.json()).catch(() => []));
  const norm = s => s.toLowerCase().normalize('NFKD').replace(/[^\w\s.]/g, ' ');
  const compact = s => s.toLowerCase().replace(/[^a-z0-9]/g, '');
  const openSearch = () => {
    if (!searchDialog) return;
    loadIndex();
    searchDialog.showModal();
    const input = $('input', searchDialog);
    input.select();
    renderResults(input.value);
  };
  let selected = 0;
  async function renderResults(q) {
    const list = $('.results', searchDialog);
    const items = await loadIndex();
    const terms = norm(q).split(/\s+/).filter(Boolean);
    let hits;
    if (!terms.length) hits = items.filter(i => i.k === 'Category' && !i.c).slice(0, 8);
    else {
      const cq = compact(q);
      hits = items.map(i => {
        const hay = norm(i.t + ' ' + (i.c || '') + ' ' + (i.s || ''));
        if (!terms.every(t => hay.includes(t)) && !compact(i.t).includes(cq)) return null;
        const t = norm(i.t);
        const score = (compact(i.t).startsWith(cq) ? 0 : t.includes(terms[0]) ? 1 : 2) + (i.k === 'Product' ? 0 : .5);
        return [score, i];
      }).filter(Boolean).sort((a, b) => a[0] - b[0]).slice(0, 30).map(x => x[1]);
    }
    selected = 0;
    list.replaceChildren(...hits.map((h, n) => {
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.href = h.u;
      a.setAttribute('role', 'option');
      a.setAttribute('aria-selected', String(n === 0));
      if (h.i) { const img = new Image(44, 44); img.src = h.i; img.alt = ''; img.loading = 'lazy'; a.append(img); }
      else { const ph = document.createElement('span'); ph.className = 'results__ph'; a.append(ph); }
      const txt = document.createElement('span');
      const strong = document.createElement('strong'); strong.textContent = h.t;
      const small = document.createElement('small'); small.textContent = [h.k, h.c].filter(Boolean).join(' · ');
      txt.append(strong, small); a.append(txt); li.append(a);
      return li;
    }));
    if (!hits.length) {
      const li = document.createElement('li'); li.className = 'results__empty';
      li.textContent = `No results for “${q}”. Try a model number like D300 or a category like “visi cooler”.`;
      list.append(li);
    }
  }
  if (searchDialog) {
    const input = $('input', searchDialog);
    input.addEventListener('input', () => renderResults(input.value));
    input.addEventListener('keydown', e => {
      const links = $$('.results a', searchDialog);
      if (!links.length) return;
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        selected = (selected + (e.key === 'ArrowDown' ? 1 : -1) + links.length) % links.length;
        links.forEach((l, n) => l.setAttribute('aria-selected', String(n === selected)));
        links[selected].scrollIntoView({ block: 'nearest' });
      } else if (e.key === 'Enter') { e.preventDefault(); location.href = links[selected].href; }
    });
    searchDialog.addEventListener('click', e => { if (e.target === searchDialog) searchDialog.close(); });
  }
  $$('[data-search-open]').forEach(b => b.addEventListener('click', openSearch));
  document.addEventListener('keydown', e => {
    const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName);
    if ((e.key === '/' && !typing) || (e.key.toLowerCase() === 'k' && (e.metaKey || e.ctrlKey))) { e.preventDefault(); openSearch(); }
  });

  /* Generic dialog close buttons */
  $$('[data-close]').forEach(b => b.addEventListener('click', () => b.closest('dialog').close()));
  $$('dialog').forEach(d => d.addEventListener('click', e => { if (e.target === d) d.close(); }));

  /* Carousels */
  $$('[data-carousel]').forEach(root => {
    const track = $('.carousel__track', root);
    const slides = $$('.carousel__slide', track);
    const dots = $('.carousel__dots', root);
    if (slides.length < 2) return;
    let current = 0, timer;
    const go = n => { current = (n + slides.length) % slides.length; track.scrollTo({ left: slides[current].offsetLeft, behavior: 'smooth' }); };
    slides.forEach((_, n) => {
      const b = document.createElement('button');
      b.type = 'button'; b.setAttribute('aria-label', `Show slide ${n + 1}`);
      b.addEventListener('click', () => { go(n); restart(); });
      dots.append(b);
    });
    const sync = () => {
      current = Math.round(track.scrollLeft / track.clientWidth);
      $$('button', dots).forEach((b, n) => b.setAttribute('aria-current', String(n === current)));
    };
    track.addEventListener('scroll', () => requestAnimationFrame(sync), { passive: true });
    $('[data-prev]', root)?.addEventListener('click', () => { go(current - 1); restart(); });
    $('[data-next]', root)?.addEventListener('click', () => { go(current + 1); restart(); });
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
    const restart = () => { clearInterval(timer); if (!reduce) timer = setInterval(() => !document.hidden && go(current + 1), 6000); };
    root.addEventListener('pointerenter', () => clearInterval(timer));
    root.addEventListener('pointerleave', restart);
    root.addEventListener('focusin', () => clearInterval(timer));
    sync(); restart();
  });

  /* Product gallery + lightbox */
  const gallery = $('[data-gallery]');
  if (gallery) {
    const main = $('.gallery__main img', gallery);
    const thumbs = $$('.thumbs button', gallery);
    thumbs.forEach(t => t.addEventListener('click', () => {
      main.src = t.dataset.src; main.srcset = t.dataset.srcset || '';
      thumbs.forEach(x => x.setAttribute('aria-current', String(x === t)));
    }));
    const lb = $('#lightbox');
    $('.gallery__main', gallery).addEventListener('click', () => {
      const current = thumbs.find(t => t.getAttribute('aria-current') === 'true');
      const img = $('img', lb);
      img.src = current?.dataset.large || main.src; img.alt = main.alt;
      lb.showModal();
    });
  }

  /* Hotspots: link dots and list items */
  $$('[data-hotspots]').forEach(root => {
    const dots = $$('.dot', root), items = $$('.feature-list li', root);
    const activate = n => { dots.forEach((d, i) => d.classList.toggle('is-active', i === n)); items.forEach((d, i) => d.classList.toggle('is-active', i === n)); };
    [...dots, ...items].forEach(el => {
      const n = +el.dataset.n;
      el.addEventListener('mouseenter', () => activate(n));
      el.addEventListener('focus', () => activate(n));
      el.addEventListener('click', () => activate(n));
    });
  });

  /* Catalogue filtering */
  $$('[data-catalog]').forEach(root => {
    const cards = $$('.product-card', root);
    const grid = $('.products', root);
    const q = $('[data-filter-q]', root), sort = $('[data-filter-sort]', root);
    const chips = $$('[data-filter-cat]', root);
    const count = $('.count', root), empty = $('.empty', root);
    const params = new URLSearchParams(location.search);
    let cat = params.get('cat') || '';
    if (q && params.get('q')) q.value = params.get('q');
    const original = cards.slice();
    const apply = () => {
      const terms = (q?.value || '').toLowerCase().split(/\s+/).filter(Boolean);
      let shown = 0;
      cards.forEach(c => {
        const ok = (!cat || c.dataset.cats.split(' ').includes(cat)) && terms.every(t => c.dataset.search.includes(t));
        c.hidden = !ok; if (ok) shown++;
      });
      chips.forEach(ch => ch.setAttribute('aria-pressed', String(ch.dataset.filterCat === cat)));
      if (count) count.textContent = `${shown} ${shown === 1 ? 'product' : 'products'}`;
      if (empty) empty.hidden = shown > 0;
      const p = new URLSearchParams(location.search);
      q?.value ? p.set('q', q.value) : p.delete('q');
      cat ? p.set('cat', cat) : p.delete('cat');
      history.replaceState(null, '', location.pathname + (p.toString() ? '?' + p : '') + location.hash);
    };
    const reorder = () => {
      const v = sort?.value;
      const list = v === 'az' || v === 'za'
        ? original.slice().sort((a, b) => a.dataset.name.localeCompare(b.dataset.name, undefined, { numeric: true }) * (v === 'za' ? -1 : 1))
        : original;
      grid.append(...list);
    };
    q?.addEventListener('input', apply);
    sort?.addEventListener('change', reorder);
    chips.forEach(ch => ch.addEventListener('click', () => { cat = ch.dataset.filterCat; apply(); }));
    $('[data-filters-toggle]', root)?.addEventListener('click', e => {
      const sb = $('.sidebar', root); const open = sb.classList.toggle('is-open');
      e.currentTarget.setAttribute('aria-expanded', String(open));
    });
    apply();
  });

  /* Compare */
  const MAX = 4;
  const tray = $('#tray');
  const getCompare = () => store.get('compare', []).filter(Boolean);
  const setCompare = list => { store.set('compare', list.slice(0, MAX)); syncCompare(); };
  function syncCompare() {
    const list = getCompare();
    $$('[data-compare]').forEach(el => {
      const on = list.includes(el.dataset.compare);
      if (el.type === 'checkbox') { el.checked = on; el.disabled = !on && list.length >= MAX; }
      else { el.setAttribute('aria-pressed', String(on)); $('span', el).textContent = on ? 'Added to compare' : 'Add to compare'; }
    });
    if (tray) {
      tray.hidden = list.length === 0 || location.pathname === '/compare/';
      $('[data-tray-count]', tray).textContent = `${list.length} of ${MAX} selected`;
    }
  }
  document.addEventListener('change', e => {
    const el = e.target.closest('input[data-compare]');
    if (!el) return;
    const list = getCompare().filter(x => x !== el.dataset.compare);
    setCompare(el.checked ? [...list, el.dataset.compare] : list);
  });
  document.addEventListener('click', e => {
    const el = e.target.closest('button[data-compare]');
    if (!el) return;
    const list = getCompare();
    setCompare(list.includes(el.dataset.compare) ? list.filter(x => x !== el.dataset.compare) : [...list, el.dataset.compare]);
  });
  $('[data-tray-clear]')?.addEventListener('click', () => setCompare([]));
  addEventListener('storage', syncCompare);
  syncCompare();

  const compareRoot = $('#compare-root');
  if (compareRoot) {
    const render = async () => {
      const list = getCompare();
      const data = list.length ? await fetch('/products.json').then(r => r.json()) : {};
      const items = list.map(id => data[id]).filter(Boolean);
      $('#compare-empty').hidden = items.length > 0;
      compareRoot.hidden = items.length === 0;
      if (!items.length) return;
      const labels = [];
      items.forEach(p => p.specs.forEach(([k]) => { if (k && !labels.includes(k)) labels.push(k); }));
      const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
      const val = (p, k) => (p.specs.find(([l]) => l === k) || [, '—'])[1];
      const head = items.map(p => `<th class="compare-head"><img src="${esc(p.img)}" alt="" width="120" height="120"><a href="${esc(p.url)}">${esc(p.name)}</a><div class="muted">${esc(p.cat)}</div><button type="button" data-remove="${esc(p.url)}">Remove</button></th>`).join('');
      const rows = labels.map(k => {
        const vals = items.map(p => val(p, k));
        const diff = new Set(vals.map(v => v.replace(/<[^>]+>/g, '').trim())).size > 1;
        return `<tr class="${diff && items.length > 1 ? 'is-diff' : ''}"><th scope="row">${k}</th>${vals.map(v => `<td>${v}</td>`).join('')}</tr>`;
      }).join('');
      compareRoot.innerHTML = `<div class="compare-scroll"><table class="compare-table"><thead><tr><th></th>${head}</tr></thead><tbody>${rows}</tbody></table></div><p class="form-note" style="margin-top:12px">Rows with differing values are highlighted.</p>`;
      $$('[data-remove]', compareRoot).forEach(b => b.addEventListener('click', () => { setCompare(getCompare().filter(x => x !== b.dataset.remove)); render(); }));
    };
    render();
  }

  /* Enquiry forms: no server, so compose an email in the visitor's mail app */
  const enquiry = $('#enquiry');
  $$('[data-enquire]').forEach(b => b.addEventListener('click', () => {
    if (!enquiry) return;
    const product = b.dataset.enquire || '';
    $('[name="product"]', enquiry).value = product;
    $('[data-enquiry-title]', enquiry).textContent = product ? `Enquire about ${product}` : 'Request a quote';
    $('.form-status', enquiry)?.remove();
    enquiry.showModal();
    $('[name="name"]', enquiry).focus();
  }));
  $$('form[data-mailto]').forEach(form => form.addEventListener('submit', e => {
    e.preventDefault();
    if (!form.reportValidity()) return;
    const fd = new FormData(form);
    const lines = [];
    for (const [k, v] of fd.entries()) {
      if (!String(v).trim()) continue;
      const label = form.querySelector(`[name="${k}"]`)?.dataset.label || k;
      lines.push(`${label}: ${v}`);
    }
    const subject = form.dataset.subject + (fd.get('product') ? ` – ${fd.get('product')}` : '');
    const href = `mailto:${SITE.email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(lines.join('\n'))}`;
    location.href = href;
    let status = $('.form-status', form);
    if (!status) { status = document.createElement('p'); status.className = 'form-status'; status.setAttribute('role', 'status'); form.append(status); }
    status.innerHTML = `Your email app should open with the details filled in. If it doesn't, email <a href="mailto:${SITE.email}">${SITE.email}</a> or call ${SITE.phone}.`;
  }));

  /* Share */
  $$('[data-share]').forEach(b => b.addEventListener('click', async () => {
    const data = { title: document.title, url: location.href };
    try {
      if (navigator.share) await navigator.share(data);
      else { await navigator.clipboard.writeText(location.href); $('span', b).textContent = 'Link copied'; setTimeout(() => $('span', b).textContent = 'Share', 2000); }
    } catch {}
  }));
})();
