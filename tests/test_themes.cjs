'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const api = require('../web/themes.js');
const css = fs.readFileSync(path.join(__dirname, '../web/themes.css'), 'utf8');
const style = fs.readFileSync(path.join(__dirname, '../web/style.css'), 'utf8');
function palette(id) {
  const block = css.match(new RegExp(':root\\[data-theme="'+id+'"\\][^{]*\\{([^}]+)\\}'));
  assert.ok(block, 'palette '+id);
  return Object.fromEntries([...block[1].matchAll(/--([\w-]+):\s*(#[0-9a-f]+);/g)].map(m=>[m[1],m[2]]));
}
function luminance(hex) {
  const c = [1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);
  return c[0]*.2126+c[1]*.7152+c[2]*.0722;
}
function ratio(a,b) { const x=luminance(a),y=luminance(b); return (Math.max(x,y)+.05)/(Math.min(x,y)+.05); }
function harness({blocked=false,cached=null}={}) {
  let stored=cached;
  const attrs={},meta={};
  const context={document:{documentElement:{setAttribute:(k,v)=>attrs[k]=v},querySelector:()=>({setAttribute:(k,v)=>meta[k]=v})},
    getComputedStyle:()=>({getPropertyValue:()=> '#111111'}),localStorage:{getItem(){if(blocked)throw Error('blocked');return stored;},setItem(k,v){if(blocked)throw Error('blocked');stored=v;}}};
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/themes.js'),'utf8'),context);
  return {api:context.LabThemes,attrs,meta,stored:()=>stored};
}
function fakeContainer() {
  const listeners={},label={textContent:''};
  const buttons=api.themes.map(theme=>({attrs:{'data-theme-choice':theme.id},tabIndex:-1,focused:false,
    getAttribute(k){return this.attrs[k];},setAttribute(k,v){this.attrs[k]=v;},focus(){this.focused=true;},closest(){return this;}}));
  return {buttons,label,listeners,querySelectorAll:()=>buttons,querySelector:()=>label,
    addEventListener:(k,v)=>listeners[k]=v,removeEventListener:(k,v)=>{if(listeners[k]===v)delete listeners[k];}};
}
test('catalog contains exactly four stable immutable themes',()=>{
 assert.deepEqual(api.themes.map(t=>t.id),['emerald','arctic','amethyst','copper']);
 assert.deepEqual(api.themes.map(t=>t.name),['Émeraude','Arctique','Améthyste','Cuivre']);
 assert.ok(Object.isFrozen(api.themes));assert.ok(api.themes.every(Object.isFrozen));
});
test('unrecognized and hostile IDs normalize safely',()=>{
 for(const id of [null,undefined,'',{},'__proto__','<img src=x onerror=x()>'])assert.equal(api.normalize(id),'emerald');
 assert.equal(api.normalize('arctic'),'arctic');
 assert.ok(!api.render('<script>').includes('<script>'));
});
test('apply updates root, native browser bar and cache',()=>{
 const h=harness();assert.equal(h.api.apply('copper'),'copper');
 assert.equal(h.attrs['data-theme'],'copper');assert.equal(h.stored(),'copper');assert.equal(h.meta.content,'#111111');
});
test('cached theme survives a new module session',()=>{
 const first=harness();first.api.apply('amethyst');const next=harness({cached:first.stored()});
 assert.equal(next.api.restoreCache(),'amethyst');assert.equal(next.attrs['data-theme'],'amethyst');
});
test('invalid cache and blocked storage remain usable',()=>{
 assert.equal(harness({cached:'invalid'}).api.restoreCache(),'emerald');
 const h=harness({blocked:true});assert.equal(h.api.restoreCache(),'emerald');assert.equal(h.api.apply('arctic'),'arctic');
});
test('renderer exposes accessible radio selection and four visual previews',()=>{
 const html=api.render('arctic');assert.equal((html.match(/role="radio"/g)||[]).length,4);
 assert.equal((html.match(/aria-checked="true"/g)||[]).length,1);
 assert.ok(html.includes('role="radiogroup"'));assert.equal((html.match(/data-preview-theme=/g)||[]).length,4);
 assert.equal((html.match(/tabindex="0"/g)||[]).length,1);
});
test('binding selects once per change and releases events',()=>{
 const c=fakeContainer(),selected=[];const dispose=api.bind(c,{theme:'emerald',onSelect:id=>selected.push(id)});
 c.listeners.click({target:c.buttons[2]});c.listeners.click({target:c.buttons[2]});
 assert.deepEqual(selected,['amethyst']);assert.equal(c.label.textContent,'Améthyste');assert.equal(c.buttons[2].attrs['aria-checked'],'true');
 assert.equal(c.buttons[0].attrs['aria-checked'],'false');assert.equal(c.buttons[2].tabIndex,0);
 dispose();assert.deepEqual(Object.keys(c.listeners),[]);
});
test('arrow keys wrap and Home/End maintain focus and selection',()=>{
 const c=fakeContainer(),selected=[];api.bind(c,{theme:'emerald',onSelect:id=>selected.push(id)});
 let prevented=0;const press=(i,key)=>c.listeners.keydown({target:c.buttons[i],key,preventDefault(){prevented++;}});
 press(0,'ArrowLeft');assert.equal(selected.at(-1),'copper');assert.ok(c.buttons[3].focused);
 press(3,'ArrowRight');assert.equal(selected.at(-1),'emerald');press(0,'End');assert.equal(selected.at(-1),'copper');press(3,'Home');assert.equal(selected.at(-1),'emerald');
 assert.equal(prevented,4);
});
test('unrelated and modified keys preserve application shortcuts',()=>{
 const c=fakeContainer(),selected=[];api.bind(c,{theme:'emerald',onSelect:id=>selected.push(id)});
 c.listeners.keydown({target:c.buttons[0],key:'ArrowRight',ctrlKey:true});
 c.listeners.keydown({target:c.buttons[0],key:'s'});c.listeners.click({target:{closest:()=>null}});
 assert.deepEqual(selected,[]);
});
test('color literals are fully centralized outside layout stylesheet',()=>{
 assert.ok(!/#[0-9a-f]{3,8}\b|\brgba?\(/i.test(style));
 for(const id of api.themes.map(t=>t.id)) {
   const p=palette(id);assert.ok(Object.keys(p).length>=50);
   for(const [,token]of style.matchAll(/var\(--([\w-]+)\)/g))assert.ok(token==='mono'||p[token],`${id}: ${token}`);
   for(const token of ['er-node','er-header','er-edge','er-grid','er-selected','er-focus','shadow','editor-bg'])assert.ok(p[token]);
 }
});
for(const {id}of api.themes)test(id+' text, semantic states and editor meet 4.5:1 contrast',()=>{
 const p=palette(id);
 for(const [fg,bg]of [['text','bg'],['text','surface'],['muted','surface'],['muted','hover-bg'],['accent','active-bg'],['primary-text','accent'],['error','error-bg'],['warning','warning-bg'],['notice-text','notice-bg'],['success-text','success-bg'],['terminal-text','terminal-bg'],['syntax-comment','editor-bg'],['syntax-string','editor-bg'],['syntax-number','editor-bg'],['gutter','editor-bg'],['text','er-node'],['text','er-header']]) {
  assert.ok(ratio(p[fg],p[bg])>=4.5,`${id} ${fg}/${bg}: ${ratio(p[fg],p[bg]).toFixed(2)}`);
 }
});
