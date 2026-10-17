/* Local-only adapters for server-backed WordPress interactions. */
(() => {
  let searchTimer;
  document.addEventListener('input', event => {
    if (!event.target.matches('input[type="search"],input[name="s"]')) return;
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => event.target.form?.dispatchEvent(new Event('submit', {bubbles:true,cancelable:true})), 200);
  });
  document.addEventListener('submit', async event => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const input = form.querySelector('input[type="search"],input[name="s"]');
    if (input) {
      const query = input.value.trim().toLowerCase();
      const index = await fetch('/search-index.json').then(r => r.json());
      let panel = form.querySelector('[data-local-results]');
      if (!panel) { panel = document.createElement('div'); panel.dataset.localResults = ''; panel.setAttribute('aria-live','polite'); form.append(panel); }
      panel.style.cssText = 'position:relative;z-index:99999;background:white;color:#333;padding:20px;max-height:55vh;overflow:auto;text-align:left;font:16px/1.6 Arial,sans-serif';
      panel.replaceChildren();
      const matches = index.filter(x => x.title.toLowerCase().includes(query)).slice(0,30);
      if (!matches.length || !query) panel.textContent = query ? 'No matching products or pages found.' : 'Enter a product or page name to search.';
      else for (const item of matches) { const a=document.createElement('a');a.href=item.url;a.textContent=item.title;a.style.cssText='display:block;color:#25467a;padding:8px;border-bottom:1px solid #eee';panel.append(a); }
    } else {
      if (!form.reportValidity()) return;
      let status = form.querySelector('[data-local-status]');
      if (!status) { status=document.createElement('p');status.dataset.localStatus='';status.setAttribute('role','status');form.append(status); }
      status.style.cssText='padding:15px;background:#f1f5fa;color:#223c65;font-size:15px';
      status.textContent='This is a website replica. Your enquiry has not been sent.';
    }
  }, true);
})();
