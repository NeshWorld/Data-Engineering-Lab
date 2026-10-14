'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const ER = require('../web/er-diagram.js');
const col=(name,pk_ordinal=0,extra={})=>({name,type:'INTEGER',pk:!!pk_ordinal,pk_ordinal,...extra});
const table=(name,columns=[col('id',1)],foreign_keys=[])=>({name,type:'table',count:0,columns,foreign_keys});
const fk=(id,seq,from,tableName,to,extra={})=>({id,seq,from,table:tableName,to,on_update:'CASCADE',on_delete:'RESTRICT',match:'NONE',...extra});
const near=(a,b)=>assert.ok(Math.abs(a-b)<1e-7,`${a} != ${b}`);

test('Only real foreign keys become relationships; name similarity creates none',()=>{
  const graph=ER.model([table('customers'),table('orders',[col('id',1),col('customer_id')])]);
  assert.equal(graph.nodes.length,2);assert.equal(graph.edges.length,0);
});
test('Composite foreign keys are grouped by source and SQLite id, sorted by seq',()=>{
  const graph=ER.model([table('parent',[col('b',2),col('a',1)]),table('child',[col('x'),col('y')],[fk(8,1,'y','parent','b'),fk(8,0,'x','parent','a')])]);
  assert.equal(graph.edges.length,1);assert.deepEqual(graph.edges[0].pairs,[{from:'x',to:'a'},{from:'y',to:'b'}]);assert.equal(graph.edges[0].resolved,true);
  assert.equal(graph.edges[0].on_update,'CASCADE');assert.equal(graph.edges[0].on_delete,'RESTRICT');assert.equal(graph.edges[0].match,'NONE');
});
test('Implicit REFERENCES resolves the actual primary key ordinal, not column order',()=>{
  const graph=ER.model([table('parent',[col('second',2),col('unrelated'),col('first',1)]),table('child',[col('x'),col('y')],[fk(2,1,'y','parent',null),fk(2,0,'x','parent',null)])]);
  assert.deepEqual(graph.edges[0].pairs,[{from:'x',to:'first'},{from:'y',to:'second'}]);assert.ok(graph.edges[0].resolved);
});
test('Implicit REFERENCES with mismatched key length stays unresolved',()=>{
  const graph=ER.model([table('parent',[col('a',1),col('b',2)]),table('child',[col('x')],[fk(0,0,'x','parent',null)])]);
  assert.equal(graph.edges[0].resolved,false);assert.equal(graph.edges[0].pairs[0].to,null);assert.equal(ER.edgePath(graph,graph.edges[0],ER.automaticPositions(graph)),'');
});
test('Missing parent does not create a ghost table',()=>{
  const graph=ER.model([table('child',[col('x')],[fk(0,0,'x','absent','id')])]);assert.equal(graph.nodes.length,1);assert.equal(graph.edges.length,1);assert.equal(graph.edges[0].resolved,false);
});
test('Missing explicit source or target column remains unresolved',()=>{
  for(const [from,to] of [['missing','id'],['x','missing']]){const g=ER.model([table('parent'),table('child',[col('x')],[fk(0,0,from,'parent',to)])]);assert.equal(g.edges[0].resolved,false);}
});
test('Distinct and repeated ids across tables never collapse separate constraints',()=>{
  const graph=ER.model([table('parent'),table('a',[col('x'),col('y')],[fk(0,0,'x','parent','id'),fk(1,0,'y','parent','id')]),table('b',[col('x')],[fk(0,0,'x','parent','id')])]);
  assert.equal(graph.edges.length,3);assert.equal(new Set(graph.edges.map(e=>e.id)).size,3);
});
test('Legacy rows without ids are treated as separate constraints',()=>{
  const graph=ER.model([table('parent'),table('child',[col('x'),col('y')],[{from:'x',table:'parent',to:'id'},{from:'y',table:'parent',to:'id'}])]);assert.equal(graph.edges.length,2);
});
test('Generated columns, defaults, PK ordinals and views remain in the model',()=>{
  const source={...table('computed',[col('b',2,{hidden:3,default:'42',notnull:true}),col('a',1)]),type:'view'};const node=ER.model([source]).nodes[0];
  assert.equal(node.type,'view');assert.equal(node.columns[0].hidden,3);assert.equal(node.columns[0].default,'42');assert.equal(node.columns[0].pk_ordinal,2);assert.equal(node.columns[0].notnull,true);
});
test('Automatic layout is deterministic and does not overlap table rectangles',()=>{
  const graph=ER.model(Array.from({length:24},(_,i)=>table('table_'+i,Array.from({length:1+i%7},(_,j)=>col('column_'+j,j===0?1:0)))));
  const positions=ER.automaticPositions(graph);assert.deepEqual(ER.automaticPositions(graph),positions);
  for(let i=0;i<graph.nodes.length;i++)for(let j=i+1;j<graph.nodes.length;j++){
    const a=graph.nodes[i],b=graph.nodes[j],p=positions[a.name],q=positions[b.name];assert.ok(p.x+a.width<=q.x||q.x+b.width<=p.x||p.y+a.height<=q.y||q.y+b.height<=p.y);
  }
});
test('Cyclic and self references terminate with finite positions',()=>{
  const graph=ER.model([table('a',[col('id',1),col('b')],[fk(0,0,'b','b','id')]),table('b',[col('id',1),col('a')],[fk(0,0,'a','a','id'),fk(1,0,'id','b','id')])]);
  const positions=ER.automaticPositions(graph);for(const node of graph.nodes)assert.ok(ER.validPoint(positions[node.name]));for(const edge of graph.edges)assert.ok(!ER.edgePath(graph,edge,positions).includes('NaN'));
});
test('Retained positions survive schema updates; new nodes do not overlap them',()=>{
  const graph=ER.model([table('a'),table('b'),table('new')]),saved={a:{x:600,y:20},b:{x:-200,y:900}};
  const positions=ER.initialPositions(graph,saved);assert.deepEqual(positions.a,saved.a);assert.deepEqual(positions.b,saved.b);assert.ok(positions.new.y>saved.b.y+graph.byName.get('b').height);
});
test('Invalid stored coordinates are ignored',()=>{
  const graph=ER.model([table('a')]);for(const p of [{x:Infinity,y:1},{x:'3',y:4},{x:1e9,y:1},null])assert.ok(ER.validPoint(ER.initialPositions(graph,{a:p}).a));
  assert.equal(ER.validPoint({x:NaN,y:1}),false);assert.equal(ER.validViewport({x:1,y:2,scale:0}),false);assert.equal(ER.validViewport({x:0,y:0,scale:3.1}),false);
});
test('Prototype-like and Unicode table names work without prototype mutations',()=>{
  const graph=ER.model([table('__proto__'),table('constructor'),table('toString'),table('Été "<x>"')]);
  const saved=JSON.parse('{"__proto__":{"x":123,"y":456},"constructor":{"x":99,"y":88}}');const p=ER.initialPositions(graph,saved);
  assert.equal(Object.getPrototypeOf(p),null);assert.deepEqual(p.__proto__,{x:123,y:456});assert.deepEqual(p.constructor,{x:99,y:88});assert.ok(ER.validPoint(p.toString));assert.equal({}.polluted,undefined);
  const patch=ER.snapshot(graph,p,{x:0,y:0,scale:1},'env');assert.ok(Object.hasOwn(patch.positions,'__proto__'));assert.deepEqual(patch.positions.__proto__,{x:123,y:456});
});
test('Fit viewport encloses all 50 synthetic tables within a normal workspace',()=>{
  const graph=ER.model(Array.from({length:50},(_,i)=>table('table_'+i,Array.from({length:8},(_,j)=>col('column_'+j))))),p=ER.automaticPositions(graph),view=ER.fitViewport(graph,p,900,610);
  assert.ok(ER.validViewport(view));for(const n of graph.nodes){const q=p[n.name];assert.ok(q.x*view.scale+view.x>=0);assert.ok(q.y*view.scale+view.y>=0);assert.ok((q.x+n.width)*view.scale+view.x<=900.001);assert.ok((q.y+n.height)*view.scale+view.y<=610.001);}
});
test('Empty schemas have finite fit viewport',()=>{const g=ER.model([]);assert.ok(ER.validViewport(ER.fitViewport(g,{},500,400)));assert.deepEqual(ER.bounds(g,{}),{x:0,y:0,width:1,height:1});});
test('Zoom preserves the world point beneath the pointer and respects limits',()=>{
  const v={x:-120,y:80,scale:.7},point={x:220,y:150},z=ER.zoomViewport(v,1.6,point);near((point.x-v.x)/v.scale,(point.x-z.x)/z.scale);near((point.y-v.y)/v.scale,(point.y-z.y)/z.scale);
  assert.equal(ER.zoomViewport(v,100,point).scale,3);assert.equal(ER.zoomViewport(v,.00001,point).scale,.1);
});
test('Edges attach to actual source and referenced column rows',()=>{
  const graph=ER.model([table('parent',[col('id',1),col('other')]),table('child',[col('id',1),col('x'),col('y')],[fk(0,0,'y','parent','id')])]);
  const p={parent:{x:0,y:0},child:{x:500,y:100}},path=ER.edgePath(graph,graph.edges[0],p);assert.ok(path.startsWith('M 500 200.5 '));assert.ok(path.endsWith(' 270 50.5'));
});
test('Parallel and self relationships have distinct curved paths',()=>{
  const graph=ER.model([table('a',[col('id',1),col('x')],[fk(0,0,'id','a','id'),fk(1,0,'x','a','id')]),table('b',[col('x'),col('y')],[fk(0,0,'x','a','id'),fk(1,0,'y','a','id')])]);
  const p=ER.automaticPositions(graph),paths=graph.edges.map(e=>ER.edgePath(graph,e,p));assert.equal(new Set(paths).size,4);assert.ok(paths.every(path=>path.includes(' C ')));
});
test('Save snapshots detach coordinates and retain the captured environment id',()=>{
  const g=ER.model([table('a')]),p=ER.automaticPositions(g),v={x:1,y:2,scale:.5},save=ER.snapshot(g,p,v,'original-env',true);p.a.x=999;v.x=777;
  assert.equal(save.env_id,'original-env');assert.notEqual(save.positions.a.x,999);assert.equal(save.viewport.x,1);assert.equal(save.replace_positions,true);assert.equal(Object.hasOwn(ER.snapshot(g,p,v,'next-env',false),'replace_positions'),false);
});

test('SQLite ASCII case-insensitive identifiers resolve to the actual table and column names',()=>{
  const graph=ER.model([table('Parent',[col('ID',1)]),table('Child',[col('Pid')],[fk(0,0,'PID','parent','id')])]);
  assert.equal(graph.edges[0].resolved,true);assert.equal(graph.edges[0].source,'Child');assert.equal(graph.edges[0].target,'Parent');assert.deepEqual(graph.edges[0].pairs,[{from:'Pid',to:'ID'}]);
});
test('Case-insensitive composite and implicit keys preserve primary key order',()=>{
  const graph=ER.model([table('PARENT',[col('Second',2),col('First',1)]),table('CHILD',[col('X'),col('Y')],[fk(0,1,'y','parent',null),fk(0,0,'x','PARENT',null),fk(1,0,'x','Parent','first'),fk(1,1,'Y','Parent','SECOND')])]);
  assert.equal(graph.edges.length,2);assert.ok(graph.edges.every(e=>e.resolved&&e.target==='PARENT'));for(const edge of graph.edges)assert.deepEqual(edge.pairs,[{from:'X',to:'First'},{from:'Y',to:'Second'}]);
});
test('Unicode case folding is not invented where SQLite matches only ASCII',()=>{
  const graph=ER.model([table('Été',[col('ID',1)]),table('child',[col('pid')],[fk(0,0,'pid','été','ID')])]);assert.equal(graph.edges[0].resolved,false);
});

test('Opposite-direction foreign keys between the same two columns remain visually distinct',()=>{
  const graph=ER.model([table('a',[col('id',1)],[fk(0,0,'id','b','id')]),table('b',[col('id',1)],[fk(0,0,'id','a','id')])]),p={a:{x:0,y:0},b:{x:500,y:0}};
  const paths=graph.edges.map(e=>ER.edgePath(graph,e,p));assert.notEqual(paths[0],paths[1]);assert.ok(paths[0].includes('40.5'));assert.ok(paths[1].includes('60.5'));
});

// Minimal DOM surface exercises mount lifecycle and real registered pointer handlers.
function fixtureDOM(){
  let observer;
  class Element {
    constructor(tag,doc){this.tagName=tag;this.ownerDocument=doc;this.attrs={};this.children=[];this.listeners=new Map();this.captures=new Set();this.classes=new Set();this.classList={add:(...x)=>x.forEach(v=>this.classes.add(v)),toggle:(x,on)=>on?this.classes.add(x):this.classes.delete(x)};}
    setAttribute(k,v){this.attrs[k]=String(v);}
    getAttribute(k){return this.attrs[k]??null;}
    append(...items){items.forEach(item=>{item.parentElement=this;this.children.push(item);});}
    replaceChildren(...items){this.children=[];this.append(...items);}
    addEventListener(name,fn){if(!this.listeners.has(name))this.listeners.set(name,new Set());this.listeners.get(name).add(fn);}
    removeEventListener(name,fn){this.listeners.get(name)?.delete(fn);}
    getBoundingClientRect(){return{left:0,top:0,width:900,height:610};}
    closest(selector){const key=selector.slice(1,-1);return Object.hasOwn(this.attrs,key)?this:this.parentElement?.closest(selector)||null;}
    focus(){this.focused=true;}
    setPointerCapture(id){this.captures.add(id);}
    hasPointerCapture(id){return this.captures.has(id);}
    releasePointerCapture(id){this.captures.delete(id);this.released=id;}
    emit(name,props){const event={button:0,preventDefault(){},...props};for(const fn of this.listeners.get(name)||[])fn(event);}
    set innerHTML(value){this.selectorMap=new Map();['svg','.er-inspector','.er-status','.er-zoom','.er-search','input','[data-er="in"]','[data-er="out"]','[data-er="fit"]','[data-er="organize"]'].forEach(key=>{const element=new Element(key==='svg'?'svg':'div',this.ownerDocument);this.selectorMap.set(key,element);this.append(element);});}
    querySelector(selector){return this.selectorMap.get(selector);}
  }
  const doc={createElementNS:(ns,tag)=>new Element(tag,doc),createElement:tag=>new Element(tag,doc),createTextNode:text=>({textContent:text}),defaultView:{ResizeObserver:class{constructor(callback){observer=this;this.callback=callback;}observe(){}disconnect(){this.disconnected=true;}}}};
  const container=new Element('div',doc);
  function all(element){return[element,...(element.children||[]).flatMap(all)];}
  return{container,svg:()=>container.querySelector('svg'),node:name=>all(container).find(el=>el.attrs?.['data-node']===name),observer:()=>observer};
}
test('Destroy after an interrupted node drag flushes visible position and releases capture',async()=>{
  const dom=fixtureDOM(),saves=[],mounted=ER.mount(dom.container,{schema:[table('a')],envId:'captured-env',layout:{},onSave:patch=>saves.push(patch)});
  await new Promise(resolve=>setTimeout(resolve,340));assert.equal(saves.length,1);
  const first=saves[0],svg=dom.svg(),node=dom.node('a');
  svg.emit('pointerdown',{pointerId:17,target:node,clientX:100,clientY:100});svg.emit('pointermove',{pointerId:17,target:svg,clientX:180,clientY:140});
  assert.equal(svg.hasPointerCapture(17),true);mounted.destroy();assert.equal(saves.length,2);
  assert.equal(saves[1].env_id,'captured-env');near(saves[1].positions.a.x,first.positions.a.x+80/first.viewport.scale);near(saves[1].positions.a.y,first.positions.a.y+40/first.viewport.scale);
  assert.equal(svg.hasPointerCapture(17),false);assert.equal(svg.released,17);assert.equal(dom.observer().disconnected,true);
  mounted.destroy();assert.equal(saves.length,2);await new Promise(resolve=>setTimeout(resolve,340));assert.equal(saves.length,2);
});
test('Destroy during a pan saves viewport even when pointerup was never received',()=>{
  const dom=fixtureDOM(),saves=[],layout={positions:{a:{x:20,y:40}},viewport:{x:5,y:15,scale:.5}};
  const mounted=ER.mount(dom.container,{schema:[table('a')],envId:'pan-env',layout,onSave:patch=>saves.push(patch)}),svg=dom.svg();
  svg.emit('pointerdown',{pointerId:3,target:svg,clientX:200,clientY:300});svg.emit('pointermove',{pointerId:3,target:svg,clientX:120,clientY:250});mounted.destroy();
  assert.equal(saves.length,1);assert.deepEqual(saves[0].viewport,{x:-75,y:-35,scale:.5});assert.deepEqual(saves[0].positions.a,{x:20,y:40});assert.equal(svg.hasPointerCapture(3),false);
});


test('A one-pixel drag is also persisted when navigation interrupts the gesture',()=>{
  const dom=fixtureDOM(),saves=[],mounted=ER.mount(dom.container,{schema:[table('a')],envId:'small-drag',layout:{positions:{a:{x:0,y:0}},viewport:{x:0,y:0,scale:1}},onSave:patch=>saves.push(patch)}),svg=dom.svg();
  svg.emit('pointerdown',{pointerId:7,target:dom.node('a'),clientX:10,clientY:10});svg.emit('pointermove',{pointerId:7,target:svg,clientX:11,clientY:10});mounted.destroy();
  assert.equal(saves.length,1);assert.deepEqual(saves[0].positions.a,{x:1,y:0});
});
