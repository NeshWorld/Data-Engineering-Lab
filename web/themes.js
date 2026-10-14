(function (root, factory) {
  'use strict';
  const api = factory(root);
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.LabThemes = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function (root) {
  'use strict';
  const CACHE_KEY = 'data-engineering-lab.theme.v1';
  const themes = Object.freeze([
    Object.freeze({id:'emerald',name:'Émeraude',description:'Verts doux et repères lumineux.'}),
    Object.freeze({id:'arctic',name:'Arctique',description:'Bleus clairs sur un fond polaire profond.'}),
    Object.freeze({id:'amethyst',name:'Améthyste',description:'Violets feutrés et accents lavande.'}),
    Object.freeze({id:'copper',name:'Cuivre',description:'Tons chauds et accents ambrés.'})
  ]);
  const normalize = id => themes.some(theme => theme.id === id) ? id : 'emerald';
  function apply(id) {
    id = normalize(id);
    if (root.document) {
      root.document.documentElement.setAttribute('data-theme', id);
      const meta = root.document.querySelector('meta[name="theme-color"]');
      if (meta && root.getComputedStyle) {
        const color = root.getComputedStyle(root.document.documentElement).getPropertyValue('--bg').trim();
        if (color) meta.setAttribute('content', color);
      }
    }
    try { if (root.localStorage) root.localStorage.setItem(CACHE_KEY, id); } catch (_) {}
    return id;
  }
  function restoreCache() {
    let id = 'emerald';
    try { if (root.localStorage) id = root.localStorage.getItem(CACHE_KEY); } catch (_) {}
    return apply(id);
  }
  function render(selectedId) {
    const id = normalize(selectedId);
    return '<section class="panel appearance-panel" aria-labelledby="appearance-heading"><div class="panel-body">' +
      '<h2 id="appearance-heading">Apparence</h2><p class="theme-intro">Choisissez les couleurs de votre laboratoire. L’aperçu s’applique immédiatement à tous les ateliers.</p>' +
      '<div class="theme-grid" role="radiogroup" aria-label="Thème du laboratoire" aria-describedby="theme-help">' +
      themes.map(theme => '<button type="button" class="theme-card" role="radio" data-theme-choice="' + theme.id +
        '" aria-checked="' + (id === theme.id) + '" tabindex="' + (id === theme.id ? '0' : '-1') + '">' +
        '<span class="theme-preview" data-preview-theme="' + theme.id + '" aria-hidden="true">' +
        '<span class="theme-preview-sidebar"><i></i><i></i><i></i><i></i></span><span class="theme-preview-main"><span class="theme-preview-heading"></span><span class="theme-preview-line"></span><span class="theme-preview-panel"><span class="theme-preview-code"></span><span class="theme-preview-code"></span></span></span></span>' +
        '<span class="theme-card-caption"><span class="theme-card-copy"><span class="theme-card-name">' + theme.name +
        '</span><span class="theme-card-description">' + theme.description +
        '</span></span><span class="theme-card-check" aria-hidden="true">✓</span></span></button>').join('') +
      '</div><p class="appearance-current">Thème sélectionné : <strong data-theme-current>' + themes.find(theme => theme.id === id).name +
      '</strong></p><p id="theme-help" class="theme-help">Utilisez les flèches pour parcourir les thèmes. Votre choix est conservé dans les paramètres de ce laboratoire.</p></div></section>';
  }
  function bind(container, options) {
    options = options || {};
    const buttons = Array.from(container.querySelectorAll('[data-theme-choice]'));
    let current = normalize(options.theme);
    function refresh(id) {
      current = normalize(id);
      for (const button of buttons) {
        const selected = button.getAttribute('data-theme-choice') === current;
        button.setAttribute('aria-checked', String(selected));
        button.tabIndex = selected ? 0 : -1;
      }
      const label = container.querySelector('[data-theme-current]');
      if (label) label.textContent = themes.find(theme => theme.id === current).name;
    }
    function select(id) {
      id = normalize(id);
      if (id === current) return;
      refresh(id);
      apply(id);
      if (typeof options.onSelect === 'function') options.onSelect(id);
    }
    function targetButton(event) {
      const target = event.target && event.target.closest ? event.target.closest('[data-theme-choice]') : null;
      return target && buttons.includes(target) ? target : null;
    }
    function click(event) {
      const button = targetButton(event);
      if (button) select(button.getAttribute('data-theme-choice'));
    }
    function keydown(event) {
      const button = targetButton(event);
      if (!button || event.altKey || event.ctrlKey || event.metaKey) return;
      const index = buttons.indexOf(button);
      let next;
      if (event.key === 'ArrowRight' || event.key === 'ArrowDown') next = (index + 1) % buttons.length;
      else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') next = (index + buttons.length - 1) % buttons.length;
      else if (event.key === 'Home') next = 0;
      else if (event.key === 'End') next = buttons.length - 1;
      else return;
      event.preventDefault();
      buttons[next].focus();
      select(buttons[next].getAttribute('data-theme-choice'));
    }
    refresh(current);
    container.addEventListener('click', click);
    container.addEventListener('keydown', keydown);
    return function dispose() {
      container.removeEventListener('click', click);
      container.removeEventListener('keydown', keydown);
    };
  }
  return Object.freeze({themes,apply,restoreCache,render,bind,normalize,CACHE_KEY});
});

