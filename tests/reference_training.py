"""Independent correct submissions, used only by tests and never served by HTTP."""
SOLUTIONS={
'py-normaliser-evenements':'''def normaliser_evenements(lignes):
    output=[]
    known=set()
    for row in lignes:
        value=row.get('id')
        key='' if value is None else str(value).strip()
        if key and key not in known:
            value=row.get('ville')
            output.append({'id':key,'ville':'' if value is None else str(value).strip().title()})
            known.add(key)
    return output
''',
'py-total-categories':'''import math
def total_par_categorie(lignes):
    output={}
    for row in lignes:
        category=row.get('categorie')
        category='' if category is None else str(category).strip().lower()
        raw=row.get('montant')
        if isinstance(raw,bool):continue
        try:value=float(raw)
        except (TypeError,ValueError,OverflowError):continue
        if category and math.isfinite(value):output[category]=output.get(category,0)+value
    return {key:round(value,2) for key,value in output.items()}
''',
'py-bilan-qualite':'''import math
def bilan_qualite(lignes):
    output=dict(total=len(lignes),manquantes=0,doublons=0,negatives=0)
    seen=set()
    for row in lignes:
        key=row.get('id')
        key='' if key is None else str(key).strip()
        if key:
            output['doublons']+=int(key in seen)
            seen.add(key)
        raw=row.get('valeur')
        try:
            if isinstance(raw,bool):raise ValueError()
            value=float(raw)
            if not math.isfinite(value):raise ValueError()
        except (TypeError,ValueError,OverflowError):output['manquantes']+=1
        else:output['negatives']+=int(value<0)
    return output
''',
'py-extraire-journal':'''from datetime import date
import math
import re
def extraire_journal(texte):
    output={'valides':[],'rejetees':0}
    for line in texte.splitlines():
        if not line.strip():continue
        fields=[value.strip() for value in line.split(';')]
        try:
            if len(fields)!=3 or not fields[1] or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',fields[0]):raise ValueError()
            date.fromisoformat(fields[0])
            value=float(fields[2])
            if not math.isfinite(value):raise ValueError()
        except (ValueError,OverflowError):output['rejetees']+=1
        else:output['valides'].append({'date':fields[0],'capteur':fields[1],'valeur':value})
    return output
''',
'sql-filtrer-alertes':"SELECT id,service FROM alerts WHERE severity='critical' AND message IS NOT NULL ORDER BY service,id;",
'sql-joindre-commandes':"SELECT c.id AS customer_id,c.name AS customer_name,COALESCE(SUM(o.total),0) AS total_paid,COUNT(o.id) AS order_count FROM customers c LEFT JOIN orders o ON o.customer_id=c.id AND o.status='paid' GROUP BY c.id,c.name ORDER BY c.id;",
'sql-agreger-ventes':"SELECT category,SUM(amount) AS total_amount,COUNT(*) AS nb_sales FROM sales WHERE category IS NOT NULL GROUP BY category HAVING SUM(amount)>=100 ORDER BY total_amount DESC,category;",
'sql-debug-classement':"SELECT id,team,points,DENSE_RANK() OVER(PARTITION BY team ORDER BY points DESC) AS rank_in_team FROM scores ORDER BY team,rank_in_team,id;",
'schema-atelier':"CREATE TABLE apprenants(id INTEGER PRIMARY KEY,nom TEXT NOT NULL,email TEXT NOT NULL UNIQUE); CREATE TABLE inscriptions(id INTEGER PRIMARY KEY,apprenant_id INTEGER NOT NULL REFERENCES apprenants(id) ON DELETE CASCADE,atelier TEXT NOT NULL,inscrit_le TEXT NOT NULL,UNIQUE(apprenant_id,atelier));",
'schema-stocks':"CREATE TABLE produits(id INTEGER PRIMARY KEY,sku TEXT NOT NULL UNIQUE); CREATE TABLE stocks(produit_id INTEGER NOT NULL REFERENCES produits(id),depot TEXT NOT NULL,quantite INTEGER NOT NULL CHECK(quantite>=0),PRIMARY KEY(produit_id,depot));"
}
