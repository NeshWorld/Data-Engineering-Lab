const test=require('node:test');
const assert=require('node:assert/strict');
const sandbox=require('../web/sandbox.js');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
test('les valeurs numériques et NULL sont typées sans accepter de non-fini',()=>{assert.equal(sandbox.parseCell('12','INTEGER'),12);assert.equal(sandbox.parseCell('2.5','REAL'),2.5);assert.equal(sandbox.parseCell('0012','TEXT'),'0012');assert.equal(sandbox.parseCell('','TEXT',true),null);assert.throws(()=>sandbox.parseCell('Infinity','REAL'),/invalide/);assert.throws(()=>sandbox.parseCell('1.2','INTEGER'),/invalide/);});
test('le DDL cite les identifiants et construit les clés composites',()=>{const sql=sandbox.previewAction({operation:'create_table',table:'commande"archive',columns:[{name:'region',type:'TEXT',primary_key:true,not_null:true},{name:'id',type:'INTEGER',primary_key:true,min:0,references:{table:'parent',column:'id'}}]});assert.match(sql,/"commande""archive"/);assert.match(sql,/PRIMARY KEY \("region", "id"\)/);assert.match(sql,/CHECK \("id" >= 0\)/);assert.match(sql,/REFERENCES "parent" \("id"\)/);});
test('le modèle refuse les colonnes sans nom et types non autorisés',()=>{assert.throws(()=>sandbox.columnSQL({name:'',type:'TEXT'}),/nom/);assert.throws(()=>sandbox.columnSQL({name:'x',type:'TEXT;DROP TABLE x'}),/Type/);assert.throws(()=>sandbox.columnSQL({name:'x',type:'REAL',min:Infinity}),/minimum/);});
test('les aperçus CRUD séparent identifiants, placeholders et valeurs',()=>{const sql=sandbox.previewAction({operation:'update_row',table:'clients',key:{id:7},values:{name:"x'); DROP TABLE clients;--"}});assert.match(sql,/UPDATE "clients" SET "name" = \? WHERE "id" = \?;/);assert.match(sql,/Valeurs liées/);assert.equal(sql.split('\n')[0].includes('DROP'),false);});
test('une clé primaire complète est reconstruite pour une ligne tableau ou objet',()=>{const table={columns:[{name:'value',type:'TEXT'},{name:'a',pk:true,pk_ordinal:1},{name:'b',pk:true,pk_ordinal:2}]};assert.deepEqual(sandbox.rowKey(table,['hello',1,2]),{a:1,b:2});assert.deepEqual(sandbox.rowKey(table,{value:'hello',a:1,b:2}),{a:1,b:2});assert.throws(()=>sandbox.rowKey(table,{a:1}),/incomplète/);assert.throws(()=>sandbox.rowKey({columns:[{name:'x'}]},{x:1}),/clé primaire/);});
test('les opérations destructrices possèdent un aperçu explicite',()=>{assert.equal(sandbox.previewAction({operation:'drop_column',table:'t',column:'x'}),'ALTER TABLE "t" DROP COLUMN "x";');assert.equal(sandbox.previewAction({operation:'drop_table',table:'t'}),'DROP TABLE "t";');assert.match(sandbox.previewAction({operation:'delete_row',table:'t',key:{id:5}}),/DELETE FROM "t" WHERE "id" = \?;/);});
test('destroy ignore une réponse info tardive sans modifier un autre écran',async()=>{let resolve;const request=new Promise(yes=>resolve=yes),container={innerHTML:'',classList:{add(){}},querySelector:()=>null,querySelectorAll:()=>[]};const mounted=sandbox.mount(container,{api:()=>request,getState:()=>({env:'env'}),notify:()=>{throw new Error('notification après destruction');}});const loading=container.innerHTML;mounted.destroy();resolve({environment:{id:'env'},tables:[],is_sandbox:true});await tick();assert.equal(container.innerHTML,loading);});

test('une clé nommée __proto__ reste une vraie propriété sérialisable',()=>{
 const key=sandbox.rowKey({columns:[{name:'__proto__',pk:true,type:'INTEGER'}]},[7]);
 assert.equal(Object.hasOwn(key,'__proto__'),true);assert.equal(key.__proto__,7);assert.equal(JSON.stringify(key),' {"__proto__":7}'.trim());
});
test('les grands entiers imprécis ne peuvent pas modifier une autre ligne',()=>{
 assert.throws(()=>sandbox.parseCell('9007199254740993','INTEGER'),/exactement/);
 assert.throws(()=>sandbox.parseCell('9007199254740993','NUMERIC'),/exactement/);
 assert.throws(()=>sandbox.rowKey({columns:[{name:'id',pk:true,type:'INTEGER'}]},[9007199254740992]),/exactement/);
 assert.equal(sandbox.parseCell('9007199254740991','INTEGER'),9007199254740991);
});
