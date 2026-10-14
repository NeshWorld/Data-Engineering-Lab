const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync(require('node:path').join(__dirname,'../web/app.js'),'utf8');
const saveSource=source.slice(source.indexOf('async function saveArtifact(kind)'),source.indexOf('async function executeSQL()'));
const queueSource=source.slice(source.indexOf('function savePreferences(patch)'),source.indexOf('let initialized='));
function deferred(){let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return{promise,resolve,reject};}
function fixture(){
 const request=deferred(),sessions=new Map([['draft',{history:'A'}]]),messages=[];
 const state={env:'env',page:'python',names:{python:'A'},drafts:{python:'CODE_A'},artifact:{}};
 const c={state,documentRevision:{python:0},pythonSessions:sessions,requireEnvironment:()=>true,pipelineDefinition:()=>{},api:async(path,payload)=>{c.payload=payload;return request.promise;},refreshState:async()=>{},render:()=>{c.renders++;},notify:m=>messages.push(m),renders:0};
 vm.createContext(c);vm.runInContext(saveSource,c);return{c,request,sessions,messages};
}
test('a save completing after another document opens preserves the active document',async()=>{
 const{c,request,sessions}=fixture();const running=c.saveArtifact('python');
 assert.equal(c.payload.code,'CODE_A');c.documentRevision.python++;c.state.artifact.python='B';c.state.drafts.python='CODE_B';c.state.names.python='B';
 request.resolve({id:'A',name:'A'});await running;
 assert.equal(c.state.artifact.python,'B');assert.equal(c.state.drafts.python,'CODE_B');assert.equal(c.state.names.python,'B');assert.equal(c.renders,0);assert.equal(sessions.has('A'),false);
});
test('first save migrates undo session and keeps edits typed while waiting',async()=>{
 const{c,request,sessions}=fixture(),session=sessions.get('draft');const running=c.saveArtifact('python');c.state.drafts.python='CODE_A_NEW';request.resolve({id:'A',name:'A'});await running;
 assert.equal(c.state.artifact.python,'A');assert.equal(c.state.drafts.python,'CODE_A_NEW');assert.equal(sessions.get('A'),session);assert.equal(sessions.has('draft'),false);assert.equal(c.renders,1);
});
test('save while navigating to another workshop does not rebuild that workshop',async()=>{
 const{c,request}=fixture();const running=c.saveArtifact('python');c.state.page='sql';request.resolve({id:'A',name:'A'});await running;assert.equal(c.renders,0);assert.equal(c.state.artifact.python,'A');
});
function queueFixture(){const calls=[],pending=[],errors=[];const c={state:{preferences:{theme:'emerald',diagrams:{}}},preferenceQueue:Promise.resolve(),api:(path,patch)=>{calls.push(patch);const d=deferred();pending.push(d);return d.promise;},notify:m=>errors.push(m)};vm.createContext(c);vm.runInContext(queueSource,c);return{c,calls,pending,errors};}
test('theme and layout writes remain FIFO with immediate local layout for navigation',async()=>{
 const{c,calls,pending}=queueFixture();const a=c.savePreferences({theme:'arctic'}),b=c.savePreferences({diagram:{env_id:'env',positions:{orders:{x:10,y:20}}}}),d=c.savePreferences({theme:'copper'});
 assert.equal(c.state.preferences.theme,'copper');assert.equal(c.state.preferences.diagrams.env.positions.orders.x,10);
 await Promise.resolve();assert.equal(calls.length,1);pending[0].resolve({});await a;await Promise.resolve();assert.equal(calls.length,2);pending[1].resolve({});await b;await Promise.resolve();assert.equal(calls.length,3);pending[2].resolve({});await d;
 assert.deepEqual(calls.map(p=>p.theme||'layout'),['arctic','layout','copper']);
});
test('failed preference write is visible and does not block later saves',async()=>{
 const{c,calls,pending,errors}=queueFixture();const a=c.savePreferences({theme:'arctic'});const rejected=assert.rejects(a,/offline/);const b=c.savePreferences({theme:'copper'});await Promise.resolve();pending[0].reject(new Error('offline'));await rejected;await new Promise(resolve=>setImmediate(resolve));assert.equal(calls.length,2);pending[1].resolve({});await b;assert.equal(errors.length,1);assert.match(errors[0],/non enregistrée/);
});
test('initial hash navigation cannot render preferences before initial loading finishes',()=>{
 const renderSource=source.slice(source.indexOf('function render() {'),source.indexOf('function homeView()'));
 const c={initialized:false};vm.createContext(c);vm.runInContext(renderSource,c);assert.doesNotThrow(()=>c.render());
});
