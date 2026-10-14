'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {transform: edit, context, History, createSession} = require('../web/python-editor.js');
const state = (text, start = text.length, end = start) => ({text, start, end});
for (const [open, close] of [['(',')'],['[',']'],['{','}'],['"','"'],["'","'"]]) {
  test(`pair ${open}${close} insertion, selection, deletion`, () => {
    assert.deepEqual(edit(state(''), open), state(open + close, 1));
    assert.deepEqual(edit(state('hello', 1, 4), open), state('h' + open + 'ell' + close + 'o', 2, 5));
    assert.deepEqual(edit(state(open + close, 1), 'Backspace'), state(''));
  });
  test(`existing closer ${close} skipped`, () => {
    assert.deepEqual(edit(state(open + close, 1), close), state(open + close, 2));
  });
}
test('nested pairs preserve correct closing order', () => {
  let s = edit(state(''), '(');
  s = edit(s, '['); s = edit(s, '{');
  assert.deepEqual(s, state('([{}])', 3));
  for (const closer of ['}',']',')']) s = edit(s, closer);
  assert.deepEqual(s, state('([{}])', 6));
  assert.equal(edit(state(')'), ')'), null);
  assert.equal(edit(state('(]', 1), ']'), null);
});
test('pairs and quotes do not autocomplete in comments or strings', () => {
  for (const text of ['# comment ', 'x = "inside ', "x = 'inside ", 'x = """multi\n']) {
    for (const key of ['(', '[', '{', '"', "'"]) assert.equal(edit(state(text), key), null, text + key);
  }
  assert.equal(edit(state('"()"', 2), 'Backspace'), null);
  assert.equal(edit(state('"[x]"', 3), ']'), null);
});
test('escaped quote stays literal; opposite quote stays literal', () => {
  assert.equal(edit(state('"a\\"', 3), '"'), null);
  assert.equal(edit(state('"a', 2), "'"), null);
  assert.equal(context('"a\\"b"').mode, 'code');
  assert.equal(context('# "').mode, 'comment');
  assert.equal(context('# "\n').mode, 'code');
});
test('Python prefixes permit quote pairs without pairing inside identifiers', () => {
  for (const prefix of ['r', 'b', 'f', 'u', 'fr', 'rf', 'rb', 'br', 'x = f']) assert.deepEqual(edit(state(prefix), '"'), state(prefix + '""', prefix.length + 1));
  assert.equal(edit(state('name'), '"'), null);
  assert.equal(edit(state('names', 2), '"'), null);
  assert.deepEqual(edit(state('call', 0), '('), state('()call', 1));
  assert.equal(edit(state('été'), '"'), null);
  assert.equal(edit(state('éfr'), '"'), null);
  assert.equal(edit(state('été', 0), '"'), null);
});
test('triple quotes expand, close and delete coherently', () => {
  for (const quote of ['"', "'"]) {
    let s = edit(state(''), quote);
    s = edit(s, quote); s = edit(s, quote);
    assert.deepEqual(s, state(quote.repeat(6), 3));
    assert.deepEqual(edit(s, quote), state(quote.repeat(6), 6));
    assert.deepEqual(edit(s, 'Backspace'), state(''));
    assert.equal(context(quote.repeat(3) + 'abc\nxyz').triple, true);
    assert.equal(context(quote.repeat(3) + 'abc' + quote.repeat(3)).mode, 'code');
  }
});
test('Enter indents block colon and preserves existing indentation', () => {
  assert.deepEqual(edit(state('if True:'), 'Enter'), state('if True:\n    '));
  assert.deepEqual(edit(state('    while ready:'), 'Enter'), state('    while ready:\n        '));
  assert.deepEqual(edit(state('    total = 1'), 'Enter'), state('    total = 1\n    '));
  assert.deepEqual(edit(state('\tprint(1)'), 'Enter'), state('\tprint(1)\n\t'));
  assert.deepEqual(edit(state('if yes: # comment'), 'Enter'), state('if yes: # comment\n    '));
  assert.deepEqual(edit(state('print("colon:")'), 'Enter'), state('print("colon:")\n'));
  assert.deepEqual(edit(state('"colon:'), 'Enter'), state('"colon:\n'));
  assert.deepEqual(edit(state('# comment:'), 'Enter'), state('# comment:\n'));
});
for (const [open, close] of [['(',')'],['[',']'],['{','}']]) {
  test(`Enter expands ${open}${close} on three lines`, () => {
    assert.deepEqual(edit(state(open + close, 1), 'Enter'), state(open + '\n    \n' + close, 6));
    const text = '    x = ' + open + close;
    assert.deepEqual(edit(state(text, text.length - 1), 'Enter'), state('    x = ' + open + '\n        \n    ' + close, 18));
    assert.deepEqual(edit(state(open + '  ' + close, 2), 'Enter'), state(open + '\n    \n' + close, 6));
  });
}
test('Enter replaces selection and never creates mismatched closing line', () => {
  assert.deepEqual(edit(state('if a:\n    old', 10, 13), 'Enter'), state('if a:\n    \n    ', 15));
  assert.deepEqual(edit(state('(]', 1), 'Enter'), state('(\n]', 2));
  assert.deepEqual(edit(state('"()"', 2), 'Enter'), state('"(\n)"', 3));
});
test('Tab indents selection, supports outdent and preserves focus escape', () => {
  assert.deepEqual(edit(state('a', 1), 'Tab'), state('a    '));
  assert.deepEqual(edit(state('a\nb\nc', 0, 4), 'Tab'), state('    a\n    b\nc', 4, 12));
  assert.deepEqual(edit(state('    a\n  b', 0, 9), 'Tab', {shiftKey:true}), state('a\nb', 0, 3));
  assert.equal(edit(state('a'), 'Tab', {shiftKey:true}), null);
  assert.equal(edit(state('a'), 'Tab', {escapeTab:true}), null);
});
test('control shortcuts, AltGr and IME are left to browser', () => {
  for (const options of [{ctrlKey:true}, {metaKey:true}, {altKey:true}, {ctrlKey:true,altKey:true}, {composing:true}]) {
    assert.equal(edit(state(''), '(', options), null);
    assert.equal(edit(state('if yes:'), 'Enter', options), null);
  }
});
test('history stores text and selections, redo branches and bounds', () => {
  const h = new History(state('abc', 1, 2), 3);
  h.commit(state('a(x)c', 2, 3));
  h.commit(state('a(xy)c', 4));
  assert.deepEqual(h.undo(), state('a(x)c', 2, 3));
  assert.deepEqual(h.undo(), state('abc', 1, 2));
  assert.deepEqual(h.redo(), state('a(x)c', 2, 3));
  h.commit(state('changed'));
  assert.deepEqual(h.redo(), state('changed'));
  h.commit(state('again')); h.commit(state('last'));
  assert.equal(h.states.length, 3);
  h.undo(); h.undo(); assert.deepEqual(h.undo(), state('changed'));
  h.selection(state('changed', 1)); assert.deepEqual(h.current(), state('changed', 1));
  h.selection(state('different', 2)); assert.deepEqual(h.current(), state('changed', 1));
});
class Textarea extends EventTarget {
  constructor(value='') {super(); this.value=value; this.selectionStart=0; this.selectionEnd=0; this.dataset={}; this.scrollTop=80; this.scrollLeft=20; this.ownerDocument={defaultView:{Event}};}
  setSelectionRange(start,end) {this.selectionStart=start; this.selectionEnd=end;}
  emit(type, props={}) {const e=new Event(type,{bubbles:true,cancelable:true}); for(const [k,v] of Object.entries(props))Object.defineProperty(e,k,{value:v});this.dispatchEvent(e);return e;}
  key(key,props={}) {return this.emit('keydown',{key,...props});}
  native(text, inputType='insertText') {
    this.emit('beforeinput',{inputType,data:text});
    const start=this.selectionStart;this.value=this.value.slice(0,start)+text+this.value.slice(this.selectionEnd);this.setSelectionRange(start+text.length,start+text.length);this.emit('input',{inputType,data:text});
  }
}
test('session dispatches normal inputs and undo redo restores wrapped selection', () => {
  const a=new Textarea('abc'), s=createSession('abc'); s.attach(a);
  let inputs=0;a.addEventListener('input',()=>inputs++);
  a.setSelectionRange(0,3);
  assert.equal(a.key('(').defaultPrevented,true);
  assert.deepEqual(s.getState(),state('(abc)',1,4));
  a.key('z',{ctrlKey:true});assert.deepEqual(s.getState(),state('abc',0,3));
  a.key('z',{ctrlKey:true,shiftKey:true});assert.deepEqual(s.getState(),state('(abc)',1,4));
  a.key('z',{ctrlKey:true});a.key('y',{ctrlKey:true});
  assert.equal(inputs,5);assert.equal(a.scrollTop,80);assert.equal(a.scrollLeft,20);
});
test('native typing/paste participates in the same undo history as pairs', () => {
  const a=new Textarea(), s=createSession(); s.attach(a);
  a.key('(');a.native('one\ntwo','insertFromPaste');
  assert.equal(a.value,'(one\ntwo)');
  a.key('z',{ctrlKey:true});assert.equal(a.value,'()');assert.equal(a.selectionStart,1);
  a.key('z',{ctrlKey:true});assert.equal(a.value,'');
  a.key('y',{ctrlKey:true});a.key('y',{ctrlKey:true});assert.equal(a.value,'(one\ntwo)');
});
test('composition stays native and becomes one undo transaction', () => {
  const a=new Textarea(), s=createSession();s.attach(a);
  a.emit('compositionstart');assert.equal(a.key('(').defaultPrevented,false);
  a.value='n';a.setSelectionRange(1,1);a.emit('input',{isComposing:true});
  a.value='你';a.emit('input',{isComposing:true});a.emit('compositionend');a.emit('input');
  a.key('z',{ctrlKey:true});assert.equal(a.value,'');a.key('y',{ctrlKey:true});assert.equal(a.value,'你');
});
test('dispose and attach preserve document history and selection without duplicate handlers', () => {
  const a=new Textarea(), s=createSession();const dispose=s.attach(a);
  a.key('{');a.native('x');dispose();dispose();
  assert.equal(a.dataset.pythonEditor,undefined);assert.equal(a.key('[').defaultPrevented,false);
  const b=new Textarea(a.value);s.attach(b);
  assert.equal(b.selectionStart,2);b.key('z',{ctrlKey:true});assert.equal(b.value,'{}');
  b.key('z',{ctrlKey:true});assert.equal(b.value,'');
  s.attach(b);b.key('[');assert.equal(b.value,'[]');
  const c=new Textarea('external change');s.attach(c);c.key('z',{ctrlKey:true});assert.equal(c.value,'external change');
});
test('session preserves Ctrl Enter / save and Escape Tab / Shift Tab navigation', () => {
  const a=new Textarea(), s=createSession();s.attach(a);
  assert.equal(a.key('Enter',{ctrlKey:true}).defaultPrevented,false);
  assert.equal(a.key('s',{ctrlKey:true}).defaultPrevented,false);
  assert.equal(a.key('Tab',{shiftKey:true}).defaultPrevented,false);
  a.key('Escape');assert.equal(a.key('Tab').defaultPrevented,false);
  assert.equal(a.key('Tab').defaultPrevented,true);assert.equal(a.value,'    ');
});
test('browser menu undo/redo input events share history', () => {
  const a=new Textarea(), s=createSession();s.attach(a);a.key('(');
  assert.equal(a.emit('beforeinput',{inputType:'historyUndo'}).defaultPrevented,true);assert.equal(a.value,'');
  assert.equal(a.emit('beforeinput',{inputType:'historyRedo'}).defaultPrevented,true);assert.equal(a.value,'()');
});
test('mixed malformed documents keep edits in bounds without mutating source', () => {
  let seed=0x12345678;
  const random=n=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed%n;};
  const chars=['a','é','_','1',' ', '\n', '\t','(',')','[',']','{','}',"'",'"','#','\\',':'];
  const keys=['(',')','[',']','{','}',"'",'"','Enter','Backspace','Tab'];
  for(let iteration=0;iteration<2000;iteration++) {
    let text='';for(let i=0,n=random(60);i<n;i++)text+=chars[random(chars.length)];
    const start=random(text.length+1),end=start+random(text.length-start+1);
    const original=Object.freeze(state(text,start,end));
    const result=edit(original,keys[random(keys.length)],{shiftKey:Boolean(random(2))});
    assert.equal(original.text,text);
    if(result) {
      assert.equal(typeof result.text,'string');
      assert.ok(Number.isInteger(result.start)&&result.start>=0&&result.start<=result.text.length);
      assert.ok(Number.isInteger(result.end)&&result.end>=result.start&&result.end<=result.text.length);
    }
  }
});
