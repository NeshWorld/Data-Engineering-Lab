"""Deterministic fictitious SQLite datasets and CSV/JSON source exports.

Size denotes principal rows (orders, shipments, events or raw orders).
Related dimensions and detail rows scale with it. Anomalies are opt-in,
reported explicitly, and never injected into an empty environment.
"""
from __future__ import annotations

import csv
from contextlib import closing
from datetime import datetime, timedelta
import json
import math
import os
from pathlib import Path
import random
import sqlite3
import tempfile
from .storage import publish_files

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GENERATOR_VERSION = "1.1"
KINDS = ("commerce", "logistics", "events", "imperfect")
BASE_DATE = datetime(2025, 1, 1, 8)


def _date(days: int = 0, minutes: int = 0) -> str:
    return (BASE_DATE + timedelta(days=days, minutes=minutes)).isoformat(timespec="seconds")


def _commerce(db, rng, size, dirty):
    db.executescript("""
        CREATE TABLE stores (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, city TEXT NOT NULL
        );
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT,
            country TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE products (
            id INTEGER PRIMARY KEY, sku TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            category TEXT NOT NULL, unit_price REAL NOT NULL
        );
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(id),
            ordered_at TEXT NOT NULL, status TEXT NOT NULL, currency TEXT NOT NULL,
            total_amount REAL NOT NULL,
            store_id INTEGER NOT NULL REFERENCES stores(id)
        );
        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(id),
            product_id INTEGER NOT NULL REFERENCES products(id), quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL, line_total REAL NOT NULL
        );
        CREATE TABLE stocks (
            store_id INTEGER NOT NULL REFERENCES stores(id),
            product_id INTEGER NOT NULL REFERENCES products(id), quantity INTEGER NOT NULL,
            PRIMARY KEY(store_id, product_id)
        );
        CREATE INDEX idx_orders_store ON orders(store_id);
        CREATE INDEX idx_orders_customer ON orders(customer_id);
        CREATE INDEX idx_order_items_order ON order_items(order_id);
        CREATE INDEX idx_order_items_product ON order_items(product_id);
    """)
    ncustomers, nproducts = math.ceil(size / 5), math.ceil(size / 10)
    for i in range(1, ncustomers + 1):
        db.execute("INSERT INTO customers VALUES (?,?,?,?,?)", (
            i, f"Client fictif {i:05d}", f"client{i}@example.test",
            rng.choice(("FR", "BE", "DE", "ES", "IT")), _date(-rng.randint(1, 365))))
    nstores = min(8, max(2, math.ceil(size / 200))) if size else 0
    cities = ("Lyon", "Lille", "Nantes", "Paris", "Bordeaux", "Rennes", "Dijon", "Tours")
    for i in range(1, nstores + 1):
        db.execute("INSERT INTO stores VALUES (?,?,?)", (i, f"Magasin fictif {i:02d}", cities[i-1]))
    prices = {}
    for i in range(1, nproducts + 1):
        prices[i] = rng.randint(500, 25000) / 100
        db.execute("INSERT INTO products VALUES (?,?,?,?,?)", (
            i, f"LAB-{i:05d}", f"Produit fictif {i:05d}",
            rng.choice(("informatique", "maison", "sport", "bureau")), prices[i]))
    for store in range(1, nstores + 1):
        for product in prices:
            db.execute("INSERT INTO stocks VALUES (?,?,?)", (store, product, rng.randint(0, 300)))
    item_id = 0
    for i in range(1, size + 1):
        items = []
        for _ in range(rng.randint(1, 4)):
            item_id += 1
            product, quantity = rng.randint(1, nproducts), rng.randint(1, 5)
            items.append((item_id, i, product, quantity, prices[product], round(quantity * prices[product], 2)))
        db.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?)", (
            i, rng.randint(1, ncustomers), _date(rng.randint(0, 180), rng.randint(0, 719)),
            rng.choice(("paid", "shipped", "delivered", "cancelled")), "EUR",
            round(sum(item[-1] for item in items), 2), (i-1) % nstores + 1))
        db.executemany("INSERT INTO order_items VALUES (?,?,?,?,?,?)", items)
    descriptions = []
    if dirty and size:
        db.execute("UPDATE customers SET email=NULL WHERE id=1")
        db.execute("UPDATE orders SET total_amount=-42.5, customer_id=? WHERE id=1", (ncustomers + 1000,))
        db.execute("UPDATE order_items SET quantity=0 WHERE id=1")
        descriptions = ["customers.id=1 : email manquant.",
                        "orders.id=1 : montant négatif et client inexistant (clé étrangère rompue).",
                        "order_items.id=1 : quantité nulle et total incohérent."]
    return "orders", descriptions


def _logistics(db, rng, size, dirty):
    db.executescript("""
        CREATE TABLE warehouses (
            id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE,
            city TEXT NOT NULL, capacity INTEGER NOT NULL
        );
        CREATE TABLE shipments (
            id INTEGER PRIMARY KEY, warehouse_id INTEGER NOT NULL REFERENCES warehouses(id),
            tracking_number TEXT NOT NULL UNIQUE, destination_country TEXT NOT NULL,
            weight_kg REAL NOT NULL, shipped_at TEXT NOT NULL, delivered_at TEXT,
            status TEXT NOT NULL, shipping_cost REAL NOT NULL
        );
        CREATE TABLE tracking_events (
            id INTEGER PRIMARY KEY, shipment_id INTEGER NOT NULL REFERENCES shipments(id),
            event_time TEXT NOT NULL, event_type TEXT NOT NULL, location TEXT NOT NULL
        );
        CREATE INDEX idx_shipments_warehouse ON shipments(warehouse_id);
        CREATE INDEX idx_tracking_shipment ON tracking_events(shipment_id);
    """)
    nwarehouses = math.ceil(size / 20)
    cities = ("Lyon", "Lille", "Nantes", "Paris", "Bordeaux")
    for i in range(1, nwarehouses + 1):
        db.execute("INSERT INTO warehouses VALUES (?,?,?,?)", (
            i, f"WH-{i:03d}", cities[(i - 1) % len(cities)], rng.randint(1000, 10000)))
    event_id = 0
    for i in range(1, size + 1):
        warehouse, day, transit_days = rng.randint(1, nwarehouses), rng.randint(0, 180), rng.randint(1, 8)
        status = rng.choice(("delivered", "delivered", "in_transit", "exception"))
        weight = rng.randint(10, 3000) / 100
        db.execute("INSERT INTO shipments VALUES (?,?,?,?,?,?,?,?,?)", (
            i, warehouse, f"LAB-TRACK-{i:07d}", rng.choice(("FR", "BE", "DE", "ES")),
            weight, _date(day), _date(day + transit_days) if status == "delivered" else None,
            status, round(4.5 + weight * 0.8 + transit_days * 0.3, 2)))
        states = [("picked_up", _date(day), cities[(warehouse - 1) % len(cities)]),
                  ("in_transit", _date(day, 360), "Centre de tri fictif")]
        if status == "delivered":
            states.append(("delivered", _date(day + transit_days), "Destination fictive"))
        elif status == "exception":
            states.append(("exception", _date(day + 1), "Centre de tri fictif"))
        for state, timestamp, location in states:
            event_id += 1
            db.execute("INSERT INTO tracking_events VALUES (?,?,?,?,?)", (event_id, i, timestamp, state, location))
    descriptions = []
    if dirty and size:
        db.execute("UPDATE shipments SET weight_kg=-1, status='delivered', delivered_at=? WHERE id=1", (_date(-1),))
        db.execute("UPDATE tracking_events SET event_time='date-invalide' WHERE id=1")
        descriptions = ["shipments.id=1 : poids négatif et livraison antérieure à l'expédition.",
                        "tracking_events.id=1 : date non interprétable."]
    return "shipments", descriptions


def _events(db, rng, size, dirty):
    db.executescript("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY, email TEXT, country TEXT NOT NULL, registered_at TEXT NOT NULL
        );
        CREATE TABLE sessions (
            id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
            started_at TEXT NOT NULL, device TEXT NOT NULL, acquisition_channel TEXT NOT NULL
        );
        CREATE TABLE events (
            id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL REFERENCES sessions(id),
            event_key TEXT NOT NULL, occurred_at TEXT NOT NULL, event_type TEXT NOT NULL,
            page_url TEXT NOT NULL, duration_ms INTEGER, properties_json TEXT NOT NULL
        );
        CREATE INDEX idx_sessions_user ON sessions(user_id);
        CREATE INDEX idx_events_session ON events(session_id);
        CREATE INDEX idx_events_time ON events(occurred_at);
    """)
    nusers, nsessions = math.ceil(size / 10), math.ceil(size / 3)
    for i in range(1, nusers + 1):
        db.execute("INSERT INTO users VALUES (?,?,?,?)", (
            i, f"user{i}@example.test", rng.choice(("FR", "BE", "US", "GB")), _date(-rng.randint(1, 300))))
    starts, offsets = {}, {}
    for i in range(1, nsessions + 1):
        day, minute = rng.randint(0, 180), rng.randint(0, 660)
        starts[i], offsets[i] = (day, minute), 0
        db.execute("INSERT INTO sessions VALUES (?,?,?,?,?)", (
            i, rng.randint(1, nusers), _date(day, minute), rng.choice(("desktop", "mobile", "tablet")),
            rng.choice(("organic", "direct", "email", "ads"))))
    for i in range(1, size + 1):
        session = (i - 1) % nsessions + 1
        day, minute = starts[session]
        offset = offsets[session]
        offsets[session] += rng.randint(1, 10)
        event_type = "page_view" if offset == 0 else rng.choice(("click", "scroll", "add_to_cart", "purchase"))
        properties = json.dumps({"synthetic": True, "variant": rng.choice(("A", "B"))}, sort_keys=True)
        db.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?)", (
            i, session, f"event-{i:08d}", _date(day, minute + offset), event_type,
            rng.choice(("/", "/catalogue", "/produits/1", "/panier")), rng.randint(50, 15000), properties))
    descriptions = []
    if dirty and size:
        db.execute("UPDATE events SET duration_ms=-100, properties_json='{broken' WHERE id=1")
        descriptions = ["events.id=1 : durée négative et propriétés JSON malformées."]
        if size > 1:
            db.execute("UPDATE events SET event_key='event-00000001', occurred_at=? WHERE id=2", (_date(-1),))
            descriptions.append("events.id=2 : clé événement dupliquée et date antérieure à la session.")
    return "events", descriptions


def _imperfect(db, rng, size, dirty):
    db.executescript("""
        CREATE TABLE raw_customers (
            id INTEGER PRIMARY KEY, external_id TEXT, full_name TEXT,
            email TEXT, country TEXT, signup_date TEXT
        );
        CREATE TABLE raw_orders (
            id INTEGER PRIMARY KEY, customer_id INTEGER REFERENCES raw_customers(id),
            order_ref TEXT, order_date TEXT, amount_text TEXT, currency TEXT, status TEXT
        );
        CREATE INDEX idx_raw_orders_customer ON raw_orders(customer_id);
    """)
    ncustomers = math.ceil(size / 3)
    for i in range(1, ncustomers + 1):
        db.execute("INSERT INTO raw_customers VALUES (?,?,?,?,?,?)", (
            i, f"CUST-{i:05d}", f"Client brut {i:05d}", f"raw{i}@example.test", "FR", _date(-rng.randint(1, 365))))
    for i in range(1, size + 1):
        db.execute("INSERT INTO raw_orders VALUES (?,?,?,?,?,?,?)", (
            i, rng.randint(1, ncustomers), f"ORDER-{i:06d}", _date(rng.randint(0, 180)),
            f"{rng.randint(500, 50000) / 100:.2f}", "EUR", rng.choice(("paid", "shipped", "cancelled"))))
    descriptions = []
    if dirty and size:
        db.execute("UPDATE raw_customers SET email='adresse-invalide', full_name='  Client brut 00001  ', country='fr ' WHERE id=1")
        db.execute("UPDATE raw_orders SET amount_text='inconnu', order_date='31/02/2025', currency=NULL, customer_id=? WHERE id=1", (ncustomers + 1000,))
        descriptions = ["raw_customers.id=1 : email invalide, espaces superflus et pays non normalisé.",
                        "raw_orders.id=1 : montant non numérique, date impossible, devise manquante et client inexistant."]
        if size > 1:
            db.execute("UPDATE raw_orders SET order_ref='ORDER-000001', amount_text='1 234,50', status='PAYÉ' WHERE id=2")
            descriptions.append("raw_orders.id=2 : référence dupliquée, montant au format local et statut non normalisé.")
        if ncustomers > 1:
            db.execute("UPDATE raw_customers SET external_id='CUST-00001', email=NULL WHERE id=2")
            descriptions.append("raw_customers.id=2 : identifiant externe dupliqué et email manquant.")
        if size > 2:
            db.execute("UPDATE raw_orders SET amount_text='9999999999.00', order_date=? WHERE id=3", (_date(-800),))
            descriptions.append("raw_orders.id=3 : montant aberrant et date antérieure à l'inscription du client.")
        if ncustomers > 2:
            db.execute("UPDATE raw_customers SET full_name='DonnÃ©e fictive' WHERE id=3")
            descriptions.append("raw_customers.id=3 : texte avec encodage mal interprété (mojibake).")
        if size > 3:
            db.execute("UPDATE raw_orders SET order_ref=NULL, status=NULL WHERE id=4")
            descriptions.append("raw_orders.id=4 : enregistrement incomplet, référence et statut absents.")
    return "raw_orders", descriptions


GENERATORS = {"commerce": _commerce, "logistics": _logistics, "events": _events, "imperfect": _imperfect}


def generate(path: Path, kind: str, seed: int, size: int, anomalies: bool = False) -> dict:
    """Generate a fresh database at the engine-selected project path.

    Existing files are replaced only after all generation and serialization
    succeed. The caller must close all connections to the selected database.
    Temporary generation files stay alongside it and are removed on failure.
    """
    if kind not in GENERATORS:
        raise ValueError(f"Environnement inconnu : {kind!r}.")
    if type(seed) is not int or not 0 <= seed <= 2147483647:
        raise ValueError("La graine doit être un entier entre 0 et 2147483647.")
    if type(size) is not int or not 0 <= size <= 10000:
        raise ValueError("La taille doit être un entier entre 0 et 10000.")
    if type(anomalies) is not bool:
        raise ValueError("Le paramètre anomalies doit être un booléen.")
    path = Path(path).resolve()
    if not path.is_relative_to(PROJECT_ROOT):
        raise ValueError("La base doit être située dans le répertoire Data Engineering Lab.")
    if path.name in ("source.csv", "source.json"):
        raise ValueError("Le nom de la base est réservé aux fichiers source.")
    if path.exists() and not path.is_file():
        raise ValueError("Le chemin de la base désigne un répertoire.")
    for name in ("source.csv", "source.json"):
        target = path.parent / name
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise ValueError("Un fichier source cible n'est pas un fichier ordinaire.")
    if any(Path(str(path) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")):
        raise ValueError("Fermez les connexions SQLite actives avant la régénération.")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = []
    try:
        for _ in range(3):
            handle = tempfile.NamedTemporaryFile(prefix=".dataset-", dir=path.parent, delete=False)
            temporary.append(Path(handle.name))
            handle.close()
        with closing(sqlite3.connect(temporary[0])) as db:
            db.execute("PRAGMA foreign_keys=ON" if not anomalies else "PRAGMA foreign_keys=OFF")
            principal, descriptions = GENERATORS[kind](db, random.Random(seed), size, anomalies)
            tables = {}
            for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
                tables[name] = db.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            if not anomalies and db.execute("PRAGMA foreign_key_check").fetchall():
                raise RuntimeError("Le générateur a produit une relation invalide.")
            cursor = db.execute(f'SELECT * FROM "{principal}" ORDER BY id')
            columns = [description[0] for description in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor]
            db.commit()
        with temporary[1].open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
        temporary[2].write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        publish_files([(temporary[0],path),(temporary[1],path.parent/'source.csv'),(temporary[2],path.parent/'source.json')])
        return {"tables": tables, "anomalies": descriptions}
    finally:
        for temporary_path in temporary:
            temporary_path.unlink(missing_ok=True)
