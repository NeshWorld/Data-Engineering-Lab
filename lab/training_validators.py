"""Independent, deterministic training fixtures and host-side assertions.

These validators are local source code, not a security boundary or secret tests.
No expected result is accepted from the submitted Python process.
"""
from collections import defaultdict
from datetime import date
import math
import re
import time
import sqlite3
from .storage import database
from .sql_engine import identifier

VALIDATOR_VERSION = '1'
PYTHON_FUNCTIONS = {
    'py-normaliser-evenements':'normaliser_evenements',
    'py-total-categories':'total_par_categorie',
    'py-bilan-qualite':'bilan_qualite',
    'py-extraire-journal':'extraire_journal',
}
SQL_IDS = ('sql-filtrer-alertes','sql-joindre-commandes','sql-agreger-ventes','sql-debug-classement')
SCHEMA_IDS = ('schema-atelier','schema-stocks')
ENGINES = {**{key:'python' for key in PYTHON_FUNCTIONS},**{key:'sql' for key in SQL_IDS},**{key:'schema' for key in SCHEMA_IDS}}

class ValidationFailure(Exception):
    """A reproducible assertion about the submitted work failed."""

def number(value):
    if isinstance(value,bool) or value is None:
        return None
    try:
        result=float(value)
    except (ValueError,TypeError,OverflowError):
        return None
    return result if math.isfinite(result) else None

def normal_id(value):
    return '' if value is None else str(value).strip()

def oracle(exercise_id, value):
    if exercise_id == 'py-normaliser-evenements':
        seen=set(); output=[]
        for row in value:
            key=normal_id(row.get('id'))
            if key and key not in seen:
                seen.add(key)
                output.append({'id':key,'ville':normal_id(row.get('ville')).title()})
        return output
    if exercise_id == 'py-total-categories':
        totals=defaultdict(float)
        for row in value:
            category=normal_id(row.get('categorie')).lower()
            amount=number(row.get('montant'))
            if category and amount is not None:
                totals[category]+=amount
        return {key:round(amount,2) for key,amount in totals.items()}
    if exercise_id == 'py-bilan-qualite':
        result={'total':len(value),'manquantes':0,'doublons':0,'negatives':0}; seen=set()
        for row in value:
            key=normal_id(row.get('id'))
            if key:
                result['doublons']+=int(key in seen);seen.add(key)
            amount=number(row.get('valeur'))
            result['manquantes']+=int(amount is None)
            result['negatives']+=int(amount is not None and amount<0)
        return result
    if exercise_id == 'py-extraire-journal':
        valid=[];rejected=0
        for line in value.splitlines():
            if not line.strip():
                continue
            fields=[field.strip() for field in line.split(';')]
            good=len(fields)==3
            if good:
                try:
                    good=bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}',fields[0]))
                    if good:date.fromisoformat(fields[0])
                except ValueError:
                    good=False
                amount=number(fields[2])
                good=good and bool(fields[1]) and amount is not None
            if good:
                valid.append({'date':fields[0],'capteur':fields[1],'valeur':amount})
            else:
                rejected+=1
        return {'valides':valid,'rejetees':rejected}
    raise ValueError('Validateur Python inconnu.')

def python_cases(exercise_id):
    inputs={
        'py-normaliser-evenements':[
            [{'id':' A1 ','ville':'  paRIS '},{'id':'A1','ville':'Lyon'},{'id':' ','ville':'Nice'},{'id':2,'ville':' lille '},{'ville':'Brest'}],
            [],
            [{'id':0,'ville':None},{'id':'0','ville':'PERDU'},{'id':'n-7','ville':' saint-malo '},{'id':None,'ville':'X'},{'id':'Z','ville':' ÉVRY '},{'id':'z'}],
        ],
        'py-total-categories':[
            [{'categorie':' Livre ','montant':'12.50'},{'categorie':'livre','montant':-2},{'categorie':'JEU','montant':7.25},{'categorie':'','montant':100},{'categorie':'jeu','montant':'invalide'}],
            [],
            [{'categorie':' Café ','montant':' 2.35 '},{'categorie':'CAFÉ','montant':4.15},{'categorie':None,'montant':9},{'categorie':'autre','montant':0},{'categorie':'autre','montant':None},{'categorie':'x','montant':'NaN'},{'categorie':'x','montant':'Infinity'},{'categorie':'nouveau','montant':'1e1'},{'categorie':'bool','montant':True}],
        ],
        'py-bilan-qualite':[
            [{'id':' a ','valeur':1},{'id':'a','valeur':None},{'id':'b','valeur':'-2.5'},{'id':'','valeur':''},{'id':None,'valeur':'oops'}],
            [],
            [{'id':0,'valeur':0},{'id':'0','valeur':-1},{'id':'0','valeur':'NaN'},{'id':None},{'id':None,'valeur':'2'},{'id':'c','valeur':'Infinity'},{'id':'d','valeur':'  -0.25 '},{'id':'bool','valeur':False}],
        ],
        'py-extraire-journal':[
            '2025-01-02; A ;12.5\nincorrect\n2025-02-30;B;2\n2025-01-03;C;-2\n',
            '\n  \n',
            '2024-02-29;Temp;-0.5\n2025-02-29;Temp;3\n2025-04-07;;1\n2025-04-08;X;NaN\n2025-04-09;Y;1e2\n2025-4-10;Z;3\n2025-04-11;Z;2;extra\n2025-04-12;Étage;0\n',
        ],
    }[exercise_id]
    titles=['Données variées et pièges courants','Entrée vide','Valeurs limites et autre jeu de données']
    return [{'id':f'cas-{index+1}','title':titles[index],'input':value,'expected':oracle(exercise_id,value)} for index,value in enumerate(inputs)]

def compare_values(actual, expected, path='résultat',strict_int=True):
    if isinstance(expected,bool) or isinstance(actual,bool):
        return (True,'Résultat conforme.') if type(actual) is type(expected) and actual==expected else (False,f'Type ou valeur incorrecte à {path}.')
    if isinstance(expected,(int,float)):
        if strict_int and type(expected) is int:
            return (True,'Résultat conforme.') if type(actual) is int and actual==expected else (False,f'Entier incorrect à {path}.')
        try:equal=isinstance(actual,(int,float)) and math.isfinite(actual) and math.isclose(actual,expected,rel_tol=1e-9,abs_tol=1e-8)
        except (OverflowError,ValueError):equal=False
        return (True,'Résultat conforme.') if equal else (False,f'Valeur numérique incorrecte à {path}.')
    if isinstance(expected,dict):
        if not isinstance(actual,dict) or set(actual)!=set(expected):
            return False,f'Clés incorrectes à {path} ; vérifiez le contrat de sortie.'
        for key in expected:
            result=compare_values(actual[key],expected[key],path+'['+repr(key)+']',strict_int)
            if not result[0]:return result
        return True,'Résultat conforme.'
    if isinstance(expected,list):
        if not isinstance(actual,list) or len(actual)!=len(expected):
            return False,f'Nombre de lignes ou type incorrect à {path}.'
        for index,(value,wanted) in enumerate(zip(actual,expected)):
            result=compare_values(value,wanted,path+f'[{index}]',strict_int)
            if not result[0]:return result
        return True,'Résultat conforme.'
    return (True,'Résultat conforme.') if type(actual) is type(expected) and actual==expected else (False,f'Valeur incorrecte à {path}.')

def sql_fixture(path, exercise_id, variant):
    """Create real input tables; compute the oracle without a reference SQL query."""
    titles=['Jeu initial varié','Autres valeurs et cas limites','Nouvelle population']
    with database(path) as db:
        if exercise_id=='sql-filtrer-alertes':
            db.execute('CREATE TABLE alerts(id INTEGER PRIMARY KEY,service TEXT,severity TEXT,message TEXT)')
            rows=[[(7,'etl','critical','retard'),(2,'api','warning','signal'),(9,'api','critical',None),(4,'api','critical',''),(1,'db','critical','arrêt')],
                  [(31,'worker','info','ok'),(11,'etl','warning',None)],
                  [(91,None,'critical','limite'),(88,'zeta','critical','x'),(85,'alpha','Critical','x'),(83,'alpha','critical','x'),(82,'alpha','critical','y')]][variant]
            db.executemany('INSERT INTO alerts VALUES(?,?,?,?)',rows)
            expected=[[row[0],row[1]] for row in sorted((r for r in rows if r[2]=='critical' and r[3] is not None),key=lambda r:(r[1] is not None,r[1] or '',r[0]))]
            columns=['id','service']
        elif exercise_id=='sql-joindre-commandes':
            db.executescript('CREATE TABLE customers(id INTEGER PRIMARY KEY,name TEXT);CREATE TABLE orders(id INTEGER PRIMARY KEY,customer_id INTEGER REFERENCES customers(id),total REAL,status TEXT);')
            customers=[[(1,'Aline'),(2,'Boris'),(3,'Chloé')],[(7,'Dune'),(9,'Echo')],[(15,'Faye'),(21,'Gabin'),(34,'Hugo'),(55,'Iris')]][variant]
            orders=[[(1,1,20,'paid'),(2,1,5,'cancelled'),(3,1,4.5,'paid'),(4,2,10,'pending')],[(1,7,None,'paid'),(2,7,-2.5,'paid'),(3,9,30,'cancelled')],[(1,15,0,'paid'),(2,21,100,'paid'),(3,21,12.5,'paid'),(4,34,77,'pending'),(5,55,-4,'paid')]][variant]
            db.executemany('INSERT INTO customers VALUES(?,?)',customers);db.executemany('INSERT INTO orders VALUES(?,?,?,?)',orders)
            expected=[]
            for cid,name in customers:
                selected=[o for o in orders if o[1]==cid and o[3]=='paid']
                expected.append([cid,name,sum(o[2] for o in selected if o[2] is not None),len(selected)])
            columns=['customer_id','customer_name','total_paid','order_count']
        elif exercise_id=='sql-agreger-ventes':
            db.execute('CREATE TABLE sales(id INTEGER PRIMARY KEY,category TEXT,amount REAL)')
            rows=[[(1,'A',60),(2,'A',40),(3,'B',140),(4,'C',99),(5,None,500),(6,'B',None)],
                  [(1,'X',110),(2,'X',-10),(3,'Y',30),(4,'Y',None),(5,'Z',None),(6,'',120)],
                  [(1,'alpha',75),(2,'alpha',45),(3,'beta',120),(4,'gamma',200),(5,'gamma',-20),(6,None,300)]][variant]
            db.executemany('INSERT INTO sales VALUES(?,?,?)',rows)
            groups=defaultdict(list)
            for _,category,amount in rows:
                if category is not None:groups[category].append(amount)
            expected=[[category,sum(v for v in values if v is not None),len(values)] for category,values in groups.items() if sum(v for v in values if v is not None)>=100]
            expected.sort(key=lambda row:(-row[1],row[0]));columns=['category','total_amount','nb_sales']
        elif exercise_id=='sql-debug-classement':
            db.execute('CREATE TABLE scores(id INTEGER PRIMARY KEY,team TEXT,points INTEGER)')
            rows=[[(1,'a',10),(2,'a',10),(3,'a',5),(4,'b',20),(5,'b',3)],
                  [(12,'orion',None),(11,'orion',7),(15,'orion',7),(13,'orion',1),(19,None,2)],
                  [(31,'z',99),(32,'z',12),(33,'z',12),(35,'m',0),(36,'m',None),(37,'m',0)]][variant]
            db.executemany('INSERT INTO scores VALUES(?,?,?)',rows)
            teams={row[1] for row in rows};ranks={}
            for team in teams:
                values=sorted({row[2] for row in rows if row[1]==team},key=lambda value:(value is None,-value if value is not None else 0))
                ranks[team]={value:index+1 for index,value in enumerate(values)}
            expected=[[rid,team,points,ranks[team][points]] for rid,team,points in rows]
            expected.sort(key=lambda row:(row[1] is not None,row[1] or '',row[3],row[0]));columns=['id','team','points','rank_in_team']
        else:raise ValueError('Validateur SQL inconnu.')
    return {'id':f'cas-{variant+1}','title':titles[variant],'expected':{'columns':columns,'rows':expected}}

def compare_sql(actual, expected):
    if actual.get('truncated'):
        return False,'Le résultat est trop volumineux pour être validé intégralement.'
    if actual.get('columns')!=expected['columns']:
        return False,'Colonnes incorrectes : vérifiez les noms, alias et leur ordre.'
    return compare_values(actual.get('rows'),expected['rows'],'lignes',False)

def _require(condition,message):
    if not condition:raise ValidationFailure(message)

def _reject(db, sql, values, description):
    db.execute('SAVEPOINT negative_probe')
    rejected=False
    try:
        db.execute(sql,values)
    except sqlite3.IntegrityError:
        rejected=True
    finally:
        db.execute('ROLLBACK TO negative_probe');db.execute('RELEASE negative_probe')
    _require(rejected,'La contrainte doit refuser '+description+'.')

def validate_schema(path, exercise_id, variant):
    """Assert declared structure AND actual positive/negative database behavior."""
    with database(path,isolation_level=None) as db:
        started=time.monotonic()
        db.set_progress_handler(lambda:int(time.monotonic()-started>2),1000)
        db.execute('PRAGMA foreign_keys=ON')
        _require(not db.execute("SELECT 1 FROM sqlite_master WHERE type='trigger'").fetchone(),'Utilisez les contraintes SQLite demandées sans trigger.')
        names={name.lower():name for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        specs={'schema-atelier':{'apprenants':{'id':'INTEGER','nom':'TEXT','email':'TEXT'},'inscriptions':{'id':'INTEGER','apprenant_id':'INTEGER','atelier':'TEXT','inscrit_le':'TEXT'}},'schema-stocks':{'produits':{'id':'INTEGER','sku':'TEXT'},'stocks':{'produit_id':'INTEGER','depot':'TEXT','quantite':'INTEGER'}}}[exercise_id]
        infos={}
        for table,columns in specs.items():
            _require(table in names,'Table requise absente : '+table+'.')
            info={row[1].lower():row for row in db.execute('PRAGMA table_info('+identifier(names[table])+')')}
            infos[table]=info
            _require(db.execute('SELECT COUNT(*) FROM '+identifier(names[table])).fetchone()[0]==0,'Le schéma doit être livré sans données permanentes.')
            for name,kind in columns.items():
                _require(name in info,'Colonne requise absente : '+table+'.'+name+'.')
                declared=info[name][2].upper()
                affinity='INTEGER' if 'INT' in declared else 'TEXT' if any(x in declared for x in ('CHAR','CLOB','TEXT')) else declared
                _require(affinity==kind,'Type incorrect pour '+table+'.'+name+'.')
        def primary(table):
            return [name for name,row in sorted(infos[table].items(),key=lambda item:item[1][5]) if row[5]]
        if exercise_id=='schema-atelier':
            _require(primary('apprenants')==['id'] and primary('inscriptions')==['id'],'Les identifiants doivent être des clés primaires simples.')
            fks=db.execute('PRAGMA foreign_key_list('+identifier(names['inscriptions'])+')').fetchall()
            _require(any(r[2].lower()=='apprenants' and r[3].lower()=='apprenant_id' and (r[4] or 'id').lower()=='id' and r[6].upper()=='CASCADE' for r in fks),'Clé étrangère apprenant_id avec ON DELETE CASCADE requise.')
        else:
            _require(primary('produits')==['id'],'produits.id doit être une clé primaire.')
            ordered=[name for name,row in sorted(infos['stocks'].items(),key=lambda item:item[1][5]) if row[5]]
            _require(ordered==['produit_id','depot'],'La clé primaire de stocks doit être composée de produit_id puis depot.')
            fks=db.execute('PRAGMA foreign_key_list('+identifier(names['stocks'])+')').fetchall()
            _require(any(r[2].lower()=='produits' and r[3].lower()=='produit_id' and (r[4] or 'id').lower()=='id' and r[6].upper() in ('NO ACTION','RESTRICT') for r in fks),'La référence vers produits.id doit empêcher la suppression d’un produit stocké.')
        db.execute('SAVEPOINT training_checks')
        try:
            base=(variant+1)*101
            if exercise_id=='schema-atelier':
                db.execute('INSERT INTO apprenants(id,nom,email) VALUES(?,?,?)',(base,'Nom fictif',f'qa{base}@example.test'))
                db.execute('INSERT INTO apprenants(id,nom,email) VALUES(?,?,?)',(base+1,'Autre fictif',f'autre{base}@example.test'))
                db.execute('INSERT INTO inscriptions(id,apprenant_id,atelier,inscrit_le) VALUES(?,?,?,?)',(base,base,'SQL','2025-02-04'))
                db.execute('INSERT INTO inscriptions(id,apprenant_id,atelier,inscrit_le) VALUES(?,?,?,?)',(base+1,base,'Python','2025-02-05'))
                db.execute('INSERT INTO inscriptions(id,apprenant_id,atelier,inscrit_le) VALUES(?,?,?,?)',(base+2,base+1,'SQL','2025-02-06'))
                _reject(db,'INSERT INTO apprenants(id,nom,email) VALUES(?,?,?)',(base+8,None,'null@example.test'),'un nom NULL')
                _reject(db,'INSERT INTO apprenants(id,nom,email) VALUES(?,?,?)',(base+8,'X',None),'un email NULL')
                _reject(db,'INSERT INTO apprenants(id,nom,email) VALUES(?,?,?)',(base+8,'X',f'qa{base}@example.test'),'un email dupliqué')
                _reject(db,'INSERT INTO inscriptions(id,apprenant_id,atelier,inscrit_le) VALUES(?,?,?,?)',(base+8,base+999,'ETL','2025-02-07'),'une référence orpheline')
                _reject(db,'INSERT INTO inscriptions(id,apprenant_id,atelier,inscrit_le) VALUES(?,?,?,?)',(base+8,base,'SQL','2025-02-07'),'la même inscription apprenant/atelier')
                for col in ('apprenant_id','atelier','inscrit_le'):
                    values={'id':base+8,'apprenant_id':base,'atelier':'ETL','inscrit_le':'2025-02-07'};values[col]=None
                    _reject(db,'INSERT INTO inscriptions(id,apprenant_id,atelier,inscrit_le) VALUES(?,?,?,?)',tuple(values.values()),col+' NULL')
                _reject(db,'INSERT INTO apprenants(id,nom,email) VALUES(?,?,?)',(base,'Autre','autre-id@example.test'),'un identifiant apprenant dupliqué')
                _reject(db,'INSERT INTO inscriptions(id,apprenant_id,atelier,inscrit_le) VALUES(?,?,?,?)',(base,base+1,'ETL','2025-03-01'),'un identifiant inscription dupliqué')
                db.execute('UPDATE apprenants SET nom=? WHERE id=?',('Nom modifié',base))
                db.execute('UPDATE inscriptions SET inscrit_le=? WHERE id=?',('2025-03-01',base))
                _require(db.execute('SELECT nom FROM apprenants WHERE id=?',(base,)).fetchone()[0]=='Nom modifié','Une mise à jour valide doit réussir.')
                db.execute('DELETE FROM apprenants WHERE id=?',(base,))
                _require(db.execute('SELECT COUNT(*) FROM inscriptions WHERE apprenant_id=?',(base,)).fetchone()[0]==0,'La suppression d’un apprenant doit supprimer ses inscriptions.')
                _require(db.execute('SELECT COUNT(*) FROM inscriptions').fetchone()[0]>=1,'La cascade ne doit pas supprimer les inscriptions d’un autre apprenant.')
            else:
                db.execute('INSERT INTO produits(id,sku) VALUES(?,?)',(base,f'QA-{base}'))
                db.execute('INSERT INTO produits(id,sku) VALUES(?,?)',(base+1,f'QA-{base+1}'))
                db.execute('INSERT INTO stocks(produit_id,depot,quantite) VALUES(?,?,?)',(base,'Nord',0))
                db.execute('INSERT INTO stocks(produit_id,depot,quantite) VALUES(?,?,?)',(base,'Sud',9))
                db.execute('INSERT INTO stocks(produit_id,depot,quantite) VALUES(?,?,?)',(base+1,'Nord',1000000))
                _reject(db,'INSERT INTO produits(id,sku) VALUES(?,?)',(base+8,None),'un SKU NULL')
                _reject(db,'INSERT INTO produits(id,sku) VALUES(?,?)',(base+8,f'QA-{base}'),'un SKU dupliqué')
                _reject(db,'INSERT INTO stocks(produit_id,depot,quantite) VALUES(?,?,?)',(base,'Nord',5),'la même paire produit/dépôt')
                _reject(db,'INSERT INTO stocks(produit_id,depot,quantite) VALUES(?,?,?)',(base+999,'Autre',1),'un produit inexistant')
                for values,label in [((None,'X',2),'un produit NULL'),((base,None,2),'un dépôt NULL'),((base,'X',None),'une quantité NULL'),((base,'X',-1),'une quantité négative')]:
                    _reject(db,'INSERT INTO stocks(produit_id,depot,quantite) VALUES(?,?,?)',values,label)
                _reject(db,'INSERT INTO produits(id,sku) VALUES(?,?)',(base,'AUTRE-ID'),'un identifiant produit dupliqué')
                db.execute('UPDATE stocks SET quantite=? WHERE produit_id=? AND depot=?',(4,base,'Nord'))
                _require(db.execute('SELECT quantite FROM stocks WHERE produit_id=? AND depot=?',(base,'Nord')).fetchone()[0]==4,'Une mise à jour valide du stock doit réussir.')
                db.execute('UPDATE produits SET sku=? WHERE id=?',('SKU-modifié',base))
                _reject(db,'UPDATE stocks SET quantite=? WHERE produit_id=? AND depot=?',(-3,base,'Nord'),'une mise à jour vers une quantité négative')
                _reject(db,'DELETE FROM produits WHERE id=?',(base,),'la suppression d’un produit stocké')
        finally:
            db.execute('ROLLBACK TO training_checks');db.execute('RELEASE training_checks')
    return 'Structure et contraintes vérifiées sur des opérations réelles.'

