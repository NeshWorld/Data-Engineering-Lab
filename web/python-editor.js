/* Local Python textarea ergonomics; sessions are owned by the document view. */
(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.LabPythonEditor = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const PAIRS = Object.freeze({'(': ')', '[': ']', '{': '}', '"': '"', "'": "'"});
  const OPEN = '([{', CLOSE = ')]}', INDENT = '    ';
  function normalize(state) {
    const text = String(state.text ?? '');
    const start = Math.max(0, Math.min(text.length, Number(state.start) || 0));
    const end = Math.max(start, Math.min(text.length, Number(state.end) || start));
    return {text, start, end};
  }
  function replace(state, from, to, insert, start, end = start) {
    return {text: state.text.slice(0, from) + insert + state.text.slice(to), start, end};
  }
  // Punctuation inside strings/comments must not affect structural editing.
  function context(text, position = text.length) {
    let mode = 'code', quote = '', triple = false, escaped = false, lastCode = '';
    const stack = [];
    for (let i = 0; i < position; i++) {
      const ch = text[i];
      if (mode === 'comment') {if (ch === '\n') {mode = 'code'; lastCode = '';} continue;}
      if (mode === 'string') {
        if (escaped) {escaped = false; continue;}
        if (ch === '\\') {escaped = true; continue;}
        if (ch === quote) {
          if (triple) {
            if (i + 2 < position && text.slice(i, i + 3) === quote.repeat(3)) {mode = 'code'; i += 2; quote = ''; triple = false;}
          } else {mode = 'code'; quote = '';}
        } else if (ch === '\n' && !triple) {mode = 'code'; quote = '';}
        continue;
      }
      if (ch === '#') {mode = 'comment'; continue;}
      if (ch === '"' || ch === "'") {
        lastCode = 'string'; mode = 'string'; quote = ch;
        triple = i + 2 < position && text.slice(i, i + 3) === ch.repeat(3);
        if (triple) i += 2;
        continue;
      }
      if (ch === '\n') lastCode = '';
      else if (!/\s/.test(ch)) lastCode = ch;
      if (OPEN.includes(ch)) stack.push(ch);
      else if (CLOSE.includes(ch) && stack.at(-1) === OPEN[CLOSE.indexOf(ch)]) stack.pop();
    }
    return {mode, quote, triple, escaped, stack, lastCode};
  }
  function indentSelection(s, outdent = false) {
    const lineStart = s.text.lastIndexOf('\n', s.start - 1) + 1;
    const last = s.end > s.start && s.text[s.end - 1] === '\n' ? s.end - 1 : s.end;
    const tail = s.text.indexOf('\n', last), lineEnd = tail < 0 ? s.text.length : tail;
    let delta = 0, firstDelta = 0;
    const output = s.text.slice(lineStart, lineEnd).split('\n').map((line, i) => {
      const size = outdent ? (line.startsWith('\t') ? 1 : Math.min(4, (line.match(/^ */) || [''])[0].length)) : 4;
      const change = outdent ? -size : size;
      if (!i) firstDelta = change;
      delta += change;
      return outdent ? line.slice(size) : INDENT + line;
    }).join('\n');
    return replace(s, lineStart, lineEnd, output, Math.max(lineStart, s.start + firstDelta), Math.max(lineStart, s.end + delta));
  }
  // null means ordinary browser editing. The reducer never changes its input.
  function transform(input, key, options = {}) {
    const s = normalize(input), {text, start, end} = s;
    if (options.composing || options.altKey || options.ctrlKey || options.metaKey) return null;
    if (key === 'Tab') {
      if (options.escapeTab || (options.shiftKey && start === end)) return null;
      if (start !== end && text.slice(start, end).includes('\n')) return indentSelection(s, Boolean(options.shiftKey));
      if (options.shiftKey) return indentSelection(s, true);
      return replace(s, start, end, INDENT, start + 4);
    }
    const ctx = context(text, start);
    if (key === 'Enter') {
      const lineStart = text.lastIndexOf('\n', start - 1) + 1;
      const leading = (text.slice(lineStart, start).match(/^[\t ]*/) || [''])[0];
      if (ctx.mode === 'code') {
        const leftGap = (text.slice(lineStart, start).match(/[\t ]*$/) || [''])[0].length;
        const rightGap = (text.slice(end).match(/^[\t ]*/) || [''])[0].length;
        const left = start - leftGap, right = end + rightGap;
        if (start === end && OPEN.includes(text[left - 1] || '\0') && PAIRS[text[left - 1]] === text[right]) {
          const inserted = '\n' + leading + INDENT + '\n' + leading;
          return replace(s, left, right, inserted, left + 1 + leading.length + 4);
        }
      }
      const extra = (ctx.mode === 'code' || ctx.mode === 'comment') && ctx.lastCode === ':' ? INDENT : '';
      const insert = '\n' + leading + extra;
      return replace(s, start, end, insert, start + insert.length);
    }
    if (key === 'Backspace' && start === end && start > 0) {
      const quote = text[start - 1];
      if ((quote === '"' || quote === "'") && text.slice(start - 3, start) === quote.repeat(3) && text.slice(start, start + 3) === quote.repeat(3) && context(text, start - 3).mode === 'code') return replace(s, start - 3, start + 3, '', start - 3);
      if (PAIRS[text[start - 1]] === text[start] && context(text, start - 1).mode === 'code') return replace(s, start - 1, start + 1, '', start - 1);
    }
    if (Object.hasOwn(PAIRS, key)) {
      if (start !== end) return replace(s, start, end, key + text.slice(start, end) + PAIRS[key], start + 1, end + 1);
      const isQuote = key === '"' || key === "'";
      if (isQuote && ctx.mode === 'string' && ctx.quote === key && !ctx.escaped && text[start] === key) {
        const advance = ctx.triple && text.slice(start, start + 3) === key.repeat(3) ? 3 : 1;
        return {...s, start: start + advance, end: start + advance};
      }
      if (ctx.mode !== 'code') return null;
      if (isQuote) {
        if (text.slice(Math.max(0, start - 2), start) === key.repeat(2) && context(text, start - 2).mode === 'code') return replace(s, start - 2, start, key.repeat(6), start + 1);
        const identifier = /[\p{L}\p{N}\p{M}_]/u;
        const prefix = (text.slice(0, start).match(/[\p{L}\p{N}\p{M}_]+$/u) || [''])[0];
        if (identifier.test(text[start] || '') || (identifier.test(text[start - 1] || '') && !/^(?:[rubf]|br|rb|fr|rf)$/i.test(prefix))) return null;
      }
      return replace(s, start, end, key + PAIRS[key], start + 1);
    }
    if (CLOSE.includes(key) && start === end && ctx.mode === 'code' && text[start] === key && PAIRS[ctx.stack.at(-1)] === key) return {...s, start: start + 1, end: start + 1};
    return null;
  }
  class History {
    constructor(initial, limit = 300) {this.limit = Math.max(2, limit); this.reset(initial);}
    reset(state) {this.states = [normalize(state)]; this.index = 0;}
    current() {return {...this.states[this.index]};}
    selection(state) {const s = normalize(state); if (s.text === this.states[this.index].text) this.states[this.index] = s;}
    commit(state) {
      const s = normalize(state);
      if (s.text === this.states[this.index].text) {this.selection(s); return false;}
      this.states.splice(this.index + 1); this.states.push(s);
      if (this.states.length > this.limit) this.states.shift();
      this.index = this.states.length - 1;
      return true;
    }
    undo() {if (this.index > 0) this.index--; return this.current();}
    redo() {if (this.index + 1 < this.states.length) this.index++; return this.current();}
  }
  function createSession(initialText = '') {
    const history = new History({text: initialText, start: 0, end: 0});
    let detach = null;
    function attach(textarea) {
      if (detach) detach();
      const read = () => ({text: textarea.value, start: textarea.selectionStart, end: textarea.selectionEnd});
      if (textarea.value !== history.current().text) history.reset(read());
      else {const s = history.current(); textarea.setSelectionRange(s.start, s.end);}
      let emitting = false, composing = false, disposed = false;
      const listeners = [];
      const listen = (name, fn) => {textarea.addEventListener(name, fn); listeners.push([name, fn]);};
      const dispatch = () => {
        emitting = true;
        try {const EventClass = textarea.ownerDocument?.defaultView?.Event || Event; textarea.dispatchEvent(new EventClass('input', {bubbles: true}));}
        finally {emitting = false;}
      };
      const show = s => {
        const top = textarea.scrollTop, left = textarea.scrollLeft;
        textarea.value = s.text; textarea.setSelectionRange(s.start, s.end);
        textarea.scrollTop = top; textarea.scrollLeft = left; dispatch();
      };
      const selection = () => {if (!composing) history.selection(read());};
      const travel = direction => {selection(); show(direction === 'undo' ? history.undo() : history.redo());};
      listen('keydown', event => {
        if (event.isComposing || composing || event.keyCode === 229) return;
        if (event.key === 'Escape') {textarea.dataset.tabEscape = 'true'; return;}
        const primary = (event.ctrlKey || event.metaKey) && !event.altKey;
        if (primary && (event.key.toLowerCase() === 'z' || event.key.toLowerCase() === 'y')) {
          event.preventDefault(); travel(event.key.toLowerCase() === 'y' || event.shiftKey ? 'redo' : 'undo'); return;
        }
        const escapeTab = Boolean(textarea.dataset.tabEscape);
        if (event.key === 'Tab') delete textarea.dataset.tabEscape;
        const before = read();
        const after = transform(before, event.key, {shiftKey: event.shiftKey, altKey: event.altKey, ctrlKey: event.ctrlKey, metaKey: event.metaKey, escapeTab});
        if (!after) return;
        event.preventDefault(); history.selection(before); history.commit(after); show(after);
      });
      listen('beforeinput', event => {
        if (emitting || composing || event.isComposing) return;
        if (event.inputType === 'historyUndo' || event.inputType === 'historyRedo') {
          if (!event.cancelable) return;
          event.preventDefault(); travel(event.inputType === 'historyUndo' ? 'undo' : 'redo');
        } else selection();
      });
      listen('input', event => {if (!emitting && !composing && !event.isComposing) history.commit(read());});
      listen('compositionstart', () => {selection(); composing = true;});
      listen('compositionend', () => {composing = false; history.commit(read());});
      for (const type of ['select', 'click', 'keyup', 'blur']) listen(type, selection);
      textarea.dataset.pythonEditor = 'true';
      detach = () => {
        if (disposed) return;
        disposed = true;
        if (composing) history.commit(read()); else selection();
        for (const [name, fn] of listeners) textarea.removeEventListener(name, fn);
        delete textarea.dataset.pythonEditor; detach = null;
      };
      return detach;
    }
    return {attach, getState: () => history.current()};
  }
  return {createSession, transform, context, History};
});
