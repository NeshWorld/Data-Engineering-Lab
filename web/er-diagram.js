(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.LabER = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const HEADER = 38, ROW = 25, GAP = 75;
  const finite = x => typeof x === 'number' && Number.isFinite(x);
  const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
  const own = (obj,key) => obj != null && Object.prototype.hasOwnProperty.call(obj,key);
  // SQLite identifier matching folds ASCII only, not accented Unicode letters.
  const sqliteKey = value => String(value).replace(/[A-Z]/g, letter => letter.toLowerCase());
  function validPoint(p) { return !!p && finite(p.x) && finite(p.y) && Math.abs(p.x) <= 1e7 && Math.abs(p.y) <= 1e7; }
  function validViewport(p) { return validPoint(p) && finite(p.scale) && p.scale >= .1 && p.scale <= 3; }
  function short(value, length) { const chars = Array.from(String(value));return chars.length > length ? chars.slice(0,length-1).join('')+'…' : chars.join(''); }
  function model(schema) {
    const nodes = (Array.isArray(schema) ? schema : []).map(table => {
      const columns = (table.columns || []).map(col => ({ ...col, pk_ordinal: Number(col.pk_ordinal) || (col.pk ? 1 : 0) }));
      const longest = Math.max(String(table.name).length, ...columns.map(c => String(c.name).length + String(c.type || '').length + 8));
      return { ...table, columns, width: clamp(longest * 7.1 + 28, 270, 390), height: HEADER + Math.max(1, columns.length) * ROW + 8 };
    });
    const byName = new Map(nodes.map(n => [n.name, n])), byKey = new Map(nodes.map(n => [sqliteKey(n.name), n])), edges = [];
    nodes.forEach(node => {
      const groups = new Map();
      (node.foreign_keys || []).forEach((fk, index) => {
        const id = fk.id == null ? 'legacy-' + index : String(fk.id);
        if (!groups.has(id)) groups.set(id, []);
        groups.get(id).push({ ...fk, seq: Number(fk.seq) || 0 });
      });
      groups.forEach((rows, id) => {
        rows.sort((a, b) => a.seq - b.seq);
        const parent = byKey.get(sqliteKey(rows[0].table));
        const primary = parent ? parent.columns.filter(c => c.pk_ordinal > 0).sort((a,b) => a.pk_ordinal - b.pk_ordinal) : [];
        const pairs = rows.map((fk,index) => {
          const from = node.columns.find(c => sqliteKey(c.name) === sqliteKey(fk.from));
          const requestedTo = fk.to == null && primary.length === rows.length ? primary[index]?.name ?? null : fk.to;
          const to = requestedTo == null ? null : parent?.columns.find(c => sqliteKey(c.name) === sqliteKey(requestedTo));
          return { from: from?.name ?? fk.from, to: to?.name ?? requestedTo };
        });
        const resolved = !!parent && rows.every(fk => sqliteKey(fk.table) === sqliteKey(parent.name)) && pairs.every(p => node.columns.some(c => c.name === p.from) && parent.columns.some(c => c.name === p.to));
        edges.push({ id: JSON.stringify([node.name, id]), source: node.name, target: parent?.name ?? rows[0].table, fkId: id, pairs, resolved,
          on_update: rows[0].on_update || '', on_delete: rows[0].on_delete || '', match: rows[0].match || '' });
      });
    });
    return { nodes, edges, byName };
  }
  // Dependency ordering stops at cycles. A bounded grid also keeps larger schemas compact.
  function automaticPositions(graph) {
    const ranks = new Map(graph.nodes.map(n => [n.name, 0])), pending = new Set(graph.nodes.map(n => n.name));
    for (let pass = 0; pass < graph.nodes.length; pass++) {
      let changed = false;
      for (const node of graph.nodes) {
        if (!pending.has(node.name)) continue;
        const parents = graph.edges.filter(e => e.resolved && e.source === node.name && e.target !== node.name).map(e => e.target);
        if (parents.some(p => pending.has(p))) continue;
        ranks.set(node.name, parents.length ? Math.max(...parents.map(p => ranks.get(p))) + 1 : 0);
        pending.delete(node.name); changed = true;
      }
      if (!changed) break;
    }
    const ordered = [...graph.nodes].sort((a,b)=>ranks.get(a.name)-ranks.get(b.name));
    const cols = Math.max(1,Math.ceil(Math.sqrt(ordered.length*1.3))), widths=[], heights=[];
    ordered.forEach((n,i)=>{const c=i%cols,r=Math.floor(i/cols);widths[c]=Math.max(widths[c]||0,n.width);heights[r]=Math.max(heights[r]||0,n.height);});
    const xs=[],ys=[];widths.forEach((w,i)=>xs[i]=i?xs[i-1]+widths[i-1]+GAP+30:40);heights.forEach((h,i)=>ys[i]=i?ys[i-1]+heights[i-1]+GAP:40);
    const positions = Object.create(null);
    ordered.forEach((n,i)=>positions[n.name]={x:xs[i%cols],y:ys[Math.floor(i/cols)]});return positions;
  }
  function initialPositions(graph, saved) {
    const positions = automaticPositions(graph), retained = graph.nodes.filter(n => own(saved,n.name) && validPoint(saved[n.name]));
    retained.forEach(n => { positions[n.name] = { x: saved[n.name].x, y: saved[n.name].y }; });
    if (retained.length) {
      let y = Math.max(...retained.map(n => positions[n.name].y + n.height)) + GAP;
      graph.nodes.filter(n => !retained.includes(n)).forEach(n => { positions[n.name] = { x: 40, y }; y += n.height + GAP; });
    }
    return positions;
  }
  function bounds(graph, positions) {
    if (!graph.nodes.length) return { x: 0, y: 0, width: 1, height: 1 };
    const x = Math.min(...graph.nodes.map(n => positions[n.name].x)), y = Math.min(...graph.nodes.map(n => positions[n.name].y));
    return { x, y, width: Math.max(...graph.nodes.map(n => positions[n.name].x + n.width)) - x,
      height: Math.max(...graph.nodes.map(n => positions[n.name].y + n.height)) - y };
  }
  function fitViewport(graph, positions, width, height) {
    const box = bounds(graph, positions), padding = 35;
    const scale = clamp(Math.min(Math.max(1,width-padding*2)/box.width,Math.max(1,height-padding*2)/box.height,1),.1,3);
    return { x: (width-box.width*scale)/2-box.x*scale, y: (height-box.height*scale)/2-box.y*scale, scale };
  }
  function zoomViewport(viewport, factor, point) {
    const scale = clamp(viewport.scale*factor,.1,3),ratio=scale/viewport.scale;
    return { x: clamp(point.x-(point.x-viewport.x)*ratio,-1e7,1e7),y:clamp(point.y-(point.y-viewport.y)*ratio,-1e7,1e7),scale };
  }
  function snapshot(graph,positions,viewport,envId,replace) {
    const patch={env_id:envId,positions:Object.fromEntries(graph.nodes.map(n=>[n.name,{...positions[n.name]}])),viewport:{...viewport}};
    if(replace)patch.replace_positions=true;return patch;
  }
  function columnY(node,names) {
    const indexes=names.map(name=>node.columns.findIndex(c=>c.name===name)).filter(i=>i>=0);
    return indexes.length?HEADER+(indexes.reduce((a,b)=>a+b,0)/indexes.length+.5)*ROW:HEADER/2;
  }
  function edgePath(graph,edge,positions) {
    if(!edge.resolved)return '';
    const a=graph.byName.get(edge.source),b=graph.byName.get(edge.target),ap=positions[a.name],bp=positions[b.name];
    const siblings=graph.edges.filter(e=>e.resolved&&((e.source===edge.source&&e.target===edge.target)||(e.source===edge.target&&e.target===edge.source)));
    const lane=siblings.findIndex(e=>e.id===edge.id),offset=(lane-(siblings.length-1)/2)*20;
    const y1=ap.y+columnY(a,edge.pairs.map(p=>p.from)),y2=bp.y+columnY(b,edge.pairs.map(p=>p.to));
    if(a===b){const x=ap.x+a.width,right=x+55+lane*30;return `M ${x} ${y1} C ${right} ${y1+offset} ${right} ${y2-55-offset} ${x} ${y2}`;}
    const rightwards=bp.x+b.width/2>=ap.x+a.width/2,x1=ap.x+(rightwards?a.width:0),x2=bp.x+(rightwards?0:b.width);
    const bend=Math.max(50,Math.abs(x2-x1)/2)+Math.abs(offset);
    return `M ${x1} ${y1} C ${x1+(rightwards?bend:-bend)} ${y1+offset} ${x2+(rightwards?-bend:bend)} ${y2+offset} ${x2} ${y2}`;
  }
  let mountSerial=0;
  function mount(container,options) {
    const graph=model(options.schema),doc=container.ownerDocument,SVG='http://www.w3.org/2000/svg';
    let positions=initialPositions(graph,options.layout?.positions),viewport=validViewport(options.layout?.viewport)?{...options.layout.viewport}:null;
    let selected=null,pending=false,replace=false,timer=null,disposed=false,gesture=null;
    const envId=options.envId,serial=++mountSerial;container.classList.add('er-root');
    container.innerHTML='<div class="er-toolbar"><div class="er-tools"><button type="button" class="small" data-er="out" aria-label="Réduire le diagramme">−</button><output class="er-zoom" aria-label="Zoom">100 %</output><button type="button" class="small" data-er="in" aria-label="Agrandir le diagramme">+</button><button type="button" class="small" data-er="fit">Tout voir</button><button type="button" class="small" data-er="organize">Organiser</button></div><form class="er-search"><label>Rechercher une table<input type="search" placeholder="Nom de table" aria-label="Rechercher une table du diagramme"></label><button type="submit" class="small">Centrer</button></form></div><div class="er-body"><div class="er-canvas"><svg class="er-svg" role="graphics-document" aria-label="Diagramme des tables et clés étrangères" tabindex="0"></svg><p class="er-help">Déplacez les tables ou le fond. Ctrl + molette pour zoomer. Flèches sur une table pour la déplacer.</p><p class="er-status" aria-live="polite"></p></div><aside class="er-inspector" aria-label="Propriétés du diagramme"></aside></div>';
    const svg=container.querySelector('svg'),inspector=container.querySelector('.er-inspector'),status=container.querySelector('.er-status');
    function s(tag,attrs,text){const element=doc.createElementNS(SVG,tag);Object.entries(attrs||{}).forEach(([k,v])=>element.setAttribute(k,String(v)));if(text!=null)element.textContent=String(text);return element;}
    function h(tag,text,cls){const el=doc.createElement(tag);if(text!=null)el.textContent=String(text);if(cls)el.className=cls;return el;}
    const defs=s('defs'),marker=s('marker',{id:'er-arrow-'+serial,viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:6,markerHeight:6,orient:'auto-start-reverse'});
    marker.append(s('path',{d:'M 0 0 L 10 5 L 0 10 z',class:'er-arrow-head'}));defs.append(marker);svg.append(defs);
    const world=s('g',{class:'er-world'}),edgesLayer=s('g'),nodesLayer=s('g');world.append(edgesLayer,nodesLayer);svg.append(world);
    const nodeEls=new Map(),edgeEls=new Map();
    graph.edges.filter(e=>e.resolved).forEach(edge=>{
      const group=s('g',{'data-edge':edge.id,class:'er-edge',tabindex:0,role:'button','aria-label':`Relation ${edge.source} vers ${edge.target}, ${edge.pairs.length} colonne(s)`});
      const visible=s('path',{class:'er-edge-line','marker-end':'url(#er-arrow-'+serial+')'}),hit=s('path',{class:'er-edge-hit'});
      group.append(visible,hit,s('title',{},edge.pairs.map(p=>`${edge.source}.${p.from} → ${edge.target}.${p.to}`).join('\n')));edgesLayer.append(group);edgeEls.set(edge.id,{group,visible,hit});
    });
    graph.nodes.forEach(node=>{
      const group=s('g',{'data-node':node.name,class:'er-node',tabindex:0,role:'button','aria-label':`Table ${node.name}, ${node.columns.length} colonnes`});
      group.append(s('rect',{class:'er-node-box',width:node.width,height:node.height,rx:7}),s('path',{class:'er-node-header',d:`M 7 0 H ${node.width-7} Q ${node.width} 0 ${node.width} 7 V ${HEADER} H 0 V 7 Q 0 0 7 0`}));
      group.append(s('text',{x:12,y:25,class:'er-title'},short(node.name,Math.floor((node.width-24)/8))),s('title',{},node.name));
      const fkColumns=new Set(graph.edges.filter(e=>e.source===node.name).flatMap(e=>e.pairs.map(p=>p.from)));
      node.columns.forEach((column,index)=>{
        const y=HEADER+index*ROW,key=[column.pk_ordinal?'PK'+column.pk_ordinal:'',fkColumns.has(column.name)?'FK':''].filter(Boolean).join(' ');
        group.append(s('line',{x1:0,x2:node.width,y1:y,y2:y,class:'er-row-line'}),s('text',{x:12,y:y+17,class:'er-key'},key));
        const typeLabel=short(column.type||'—',14),typeWidth=typeLabel.length*6;
        const name=s('text',{x:65,y:y+17,class:'er-column-name'},short(column.name,Math.max(8,Math.floor((node.width-85-typeWidth)/6.8))));name.append(s('title',{},column.name));group.append(name);
        const type=s('text',{x:node.width-10,y:y+17,'text-anchor':'end',class:'er-column-type'},typeLabel);type.append(s('title',{},column.type||'Sans type déclaré'));group.append(type);
      });
      if(!node.columns.length)group.append(s('text',{x:12,y:HEADER+17,class:'er-column-type'},'Aucune colonne'));
      nodesLayer.append(group);nodeEls.set(node.name,group);
    });
    function flush(){if(timer)clearTimeout(timer);timer=null;if(!pending)return;pending=false;const patch=snapshot(graph,positions,viewport,envId,replace);replace=false;
      const failed=()=>{status.textContent='La disposition n’a pas pu être enregistrée.';};try{const result=options.onSave?.(patch);if(result?.catch)result.catch(failed);}catch(err){failed();}}
    function schedule(){pending=true;if(timer)clearTimeout(timer);timer=setTimeout(flush,300);}
    function draw(){world.setAttribute('transform',`translate(${viewport.x} ${viewport.y}) scale(${viewport.scale})`);nodeEls.forEach((el,name)=>el.setAttribute('transform',`translate(${positions[name].x} ${positions[name].y})`));graph.edges.forEach(e=>{const els=edgeEls.get(e.id);if(els){const d=edgePath(graph,e,positions);els.visible.setAttribute('d',d);els.hit.setAttribute('d',d);}});container.querySelector('.er-zoom').textContent=Math.round(viewport.scale*100)+' %';}
    function detail(label,value){const row=h('p',null,'er-detail');row.append(h('strong',label+' '),doc.createTextNode(String(value)));inspector.append(row);}
    function relationButton(edge){const b=h('button',`${edge.source} → ${edge.target}${edge.resolved?'':' (non résolue)'}`,'small er-relation-button');b.type='button';b.addEventListener('click',()=>select('edge',edge.id));inspector.append(b);}
    function inspect(){inspector.replaceChildren();nodeEls.forEach((el,name)=>el.classList.toggle('selected',selected?.kind==='node'&&selected.id===name));edgeEls.forEach((els,id)=>els.group.classList.toggle('selected',selected?.kind==='edge'&&selected.id===id));
      if(selected?.kind==='node'){
        const node=graph.byName.get(selected.id);inspector.append(h('h3',node.name));detail('Objet :',node.type==='view'?'Vue':'Table');detail('Lignes :',node.count??'Inconnu');
        node.columns.forEach(c=>{const item=h('div',null,'er-property');item.append(h('strong',c.name),h('p',`${c.type||'Sans type'} · ${c.notnull?'NOT NULL':'NULL autorisé'}${c.pk_ordinal?' · PK '+c.pk_ordinal:''}${c.hidden?' · '+(c.hidden===1?'masquée':'générée'):''}`));if(c.default!=null)item.append(h('p','Défaut : '+c.default));inspector.append(item);});
        const relations=graph.edges.filter(e=>e.source===node.name||e.target===node.name);if(relations.length){inspector.append(h('h3','Relations'));relations.forEach(relationButton);}
      }else if(selected?.kind==='edge'){
        const edge=graph.edges.find(e=>e.id===selected.id);inspector.append(h('h3','Clé étrangère'));detail('Source :',edge.source);detail('Cible :',edge.target);detail('Identifiant SQLite :',edge.fkId);
        edge.pairs.forEach(p=>inspector.append(h('p',`${p.from} → ${p.to??'Clé primaire non résolue'}`,'er-pair')));
        if(!edge.resolved)inspector.append(h('p','La table ou une colonne cible est absente. Aucun lien graphique n’est inventé.','er-unresolved'));
        detail('ON UPDATE :',edge.on_update||'Non fourni');detail('ON DELETE :',edge.on_delete||'Non fourni');detail('MATCH :',edge.match||'Non fourni');
      }else{
        inspector.append(h('h3','Schéma relationnel'),h('p','Sélectionnez une table ou une relation pour voir ses propriétés.'));detail('Objets :',graph.nodes.length);detail('Clés étrangères :',graph.edges.length);
        const unresolved=graph.edges.filter(e=>!e.resolved);if(unresolved.length){inspector.append(h('p',unresolved.length+' relation(s) non résolue(s).','er-unresolved'));unresolved.forEach(relationButton);}
        inspector.append(h('p','PK : ordre dans la clé primaire. FK : colonne d’une clé étrangère. Les flèches vont de la colonne référente vers la colonne référencée.','er-legend'));
      }}
    function select(kind,id){selected=kind?{kind,id}:null;inspect();}
    function size(){const r=svg.getBoundingClientRect();return{width:r.width||600,height:r.height||420};}
    function fit(){const z=size();viewport=fitViewport(graph,positions,z.width,z.height);draw();schedule();}
    function zoom(factor,point){const z=size();viewport=zoomViewport(viewport,factor,point||{x:z.width/2,y:z.height/2});draw();schedule();}
    function point(event){const r=svg.getBoundingClientRect();return{x:event.clientX-r.left,y:event.clientY-r.top};}
    function down(event){if(event.button!==0)return;const node=event.target.closest('[data-node]'),edge=event.target.closest('[data-edge]');if(edge){select('edge',edge.getAttribute('data-edge'));return;}
      const p=point(event),name=node?.getAttribute('data-node');gesture={pointer:event.pointerId,start:p,name,isNode:!!node,original:node?{...positions[name]}:{x:viewport.x,y:viewport.y},moved:false};if(node)select('node',name);else select(null);svg.setPointerCapture(event.pointerId);event.preventDefault();if(node)node.focus();}
    function move(event){if(!gesture||event.pointerId!==gesture.pointer)return;const p=point(event),dx=p.x-gesture.start.x,dy=p.y-gesture.start.y;gesture.moved=gesture.moved||Math.abs(dx)+Math.abs(dy)>0;if(gesture.moved)pending=true;
      if(gesture.isNode)positions[gesture.name]={x:clamp(gesture.original.x+dx/viewport.scale,-1e7,1e7),y:clamp(gesture.original.y+dy/viewport.scale,-1e7,1e7)};else{viewport.x=clamp(gesture.original.x+dx,-1e7,1e7);viewport.y=clamp(gesture.original.y+dy,-1e7,1e7);}draw();}
    function up(event){if(!gesture||event.pointerId!==gesture.pointer)return;if(gesture.moved)schedule();gesture=null;if(svg.hasPointerCapture(event.pointerId))svg.releasePointerCapture(event.pointerId);}
    function wheel(event){if(!event.ctrlKey&&!event.metaKey)return;event.preventDefault();zoom(Math.exp(-event.deltaY*.002),point(event));}
    function key(event){const node=event.target.closest('[data-node]'),edge=event.target.closest('[data-edge]');if((event.key==='Enter'||event.key===' ')&&(node||edge)){event.preventDefault();select(node?'node':'edge',(node||edge).getAttribute(node?'data-node':'data-edge'));return;}
      if(node&&['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key)){event.preventDefault();const name=node.getAttribute('data-node'),delta=event.shiftKey?50:10,p=positions[name];if(event.key==='ArrowLeft')p.x-=delta;if(event.key==='ArrowRight')p.x+=delta;if(event.key==='ArrowUp')p.y-=delta;if(event.key==='ArrowDown')p.y+=delta;p.x=clamp(p.x,-1e7,1e7);p.y=clamp(p.y,-1e7,1e7);select('node',name);draw();schedule();}if(event.key==='Escape'){select(null);svg.focus();}}
    svg.addEventListener('pointerdown',down);svg.addEventListener('pointermove',move);svg.addEventListener('pointerup',up);svg.addEventListener('pointercancel',up);svg.addEventListener('wheel',wheel,{passive:false});svg.addEventListener('keydown',key);
    container.querySelector('[data-er="in"]').onclick=()=>zoom(1.25);container.querySelector('[data-er="out"]').onclick=()=>zoom(.8);container.querySelector('[data-er="fit"]').onclick=fit;
    container.querySelector('[data-er="organize"]').onclick=()=>{positions=automaticPositions(graph);replace=true;fit();status.textContent='Tables réorganisées. La nouvelle disposition est enregistrée.';};
    container.querySelector('.er-search').onsubmit=event=>{event.preventDefault();const q=container.querySelector('input').value.trim().toLocaleLowerCase();if(!q)return;const node=graph.nodes.find(n=>n.name.toLocaleLowerCase()===q)||graph.nodes.find(n=>n.name.toLocaleLowerCase().includes(q));if(!node){status.textContent='Aucune table correspondante.';return;}
      const z=size(),p=positions[node.name],scale=Math.max(.65,viewport.scale);viewport={x:z.width/2-(p.x+node.width/2)*scale,y:z.height/2-(p.y+node.height/2)*scale,scale};select('node',node.name);draw();schedule();nodeEls.get(node.name).focus({preventScroll:true});status.textContent='Table '+node.name+' centrée.';};
    if(!viewport){const z=size();viewport=fitViewport(graph,positions,z.width,z.height);pending=true;}draw();inspect();if(pending)schedule();
    let previousSize=size();const Observer=doc.defaultView?.ResizeObserver;const observer=Observer?new Observer(()=>{if(disposed)return;const next=size();if(next.width!==previousSize.width||next.height!==previousSize.height){viewport.x+=(next.width-previousSize.width)/2;viewport.y+=(next.height-previousSize.height)/2;previousSize=next;draw();}}):null;observer?.observe(svg);
    return{destroy(){if(disposed)return;if(gesture){if(gesture.moved)pending=true;try{if(svg.hasPointerCapture(gesture.pointer))svg.releasePointerCapture(gesture.pointer);}catch(err){}gesture=null;}flush();disposed=true;observer?.disconnect();svg.removeEventListener('pointerdown',down);svg.removeEventListener('pointermove',move);svg.removeEventListener('pointerup',up);svg.removeEventListener('pointercancel',up);svg.removeEventListener('wheel',wheel);svg.removeEventListener('keydown',key);}};
  }
  return{mount,model,automaticPositions,initialPositions,bounds,fitViewport,zoomViewport,edgePath,validPoint,validViewport,snapshot};
});



