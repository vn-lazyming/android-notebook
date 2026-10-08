// pen & paper: write the file path + page number at the top of the sheet,
// and label each code slip with its language. styling is in paper.css.
(() => {
  const main = document.querySelector('.content main');
  if (!main) return;

  // mdBook already renders the edit link, it ends in src/<file>.md
  const edit = document.querySelector('a[rel="edit"]');
  const src = edit && decodeURIComponent(edit.href.split('/edit/main/')[1] || '');
  if (src) {
    const head = document.createElement('div');
    head.className = 'nb-head';
    head.setAttribute('aria-hidden', 'true');
    const path = document.createElement('span');
    path.textContent = '~/android-notebook/src/' + src.split('/').pop();
    head.append(path);
    const no = src.match(/(\d+)-[^/]*$/);
    if (no) {
      const tag = document.createElement('span');
      tag.className = 'no';
      tag.textContent = 'No. ' + no[1];
      head.append(tag);
    }
    main.prepend(head);
  }

  for (const code of main.querySelectorAll('pre > code')) {
    const lang = [...code.classList].find(c => c.startsWith('language-'));
    if (lang) code.dataset.lang = lang.slice('language-'.length);
  }
})();
