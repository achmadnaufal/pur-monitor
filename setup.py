#!/usr/bin/env python3.12
"""
setup.py — Creates the PUR Latin America monitoring DuckDB database,
           defines all tables, and seeds realistic sample data.
"""

import duckdb
import random
from datetime import date, timedelta

DB_PATH = "pur_monitor.db"

DDL = """
CREATE OR REPLACE TABLE regions (
    id          INTEGER PRIMARY KEY,
    region_name VARCHAR NOT NULL
);
CREATE OR REPLACE TABLE countries (
    id           INTEGER PRIMARY KEY,
    region_id    INTEGER REFERENCES regions(id),
    country_name VARCHAR NOT NULL,
    country_code CHAR(2) NOT NULL
);
CREATE OR REPLACE TABLE projects (
    id              INTEGER PRIMARY KEY,
    region_id       INTEGER REFERENCES regions(id),
    country_id      INTEGER REFERENCES countries(id),
    project_name    VARCHAR NOT NULL,
    project_country VARCHAR NOT NULL,
    project_year    INTEGER NOT NULL
);
CREATE OR REPLACE TABLE species (
    id           INTEGER PRIMARY KEY,
    species_name VARCHAR NOT NULL
);
CREATE OR REPLACE TABLE ref_erosion (
    id                 INTEGER PRIMARY KEY,
    erosion_level_name VARCHAR NOT NULL
);
CREATE OR REPLACE TABLE ref_soil_texture (
    id                INTEGER PRIMARY KEY,
    soil_texture_name VARCHAR NOT NULL
);
CREATE OR REPLACE TABLE ref_mortality (
    id             INTEGER PRIMARY KEY,
    mortality_name VARCHAR NOT NULL
);
CREATE OR REPLACE TABLE ref_planting_model (
    id                  INTEGER PRIMARY KEY,
    planting_model_name VARCHAR NOT NULL
);
CREATE OR REPLACE TABLE farmers (
    id           INTEGER PRIMARY KEY,
    project_id   INTEGER REFERENCES projects(id),
    farmer_name  VARCHAR NOT NULL,
    gender       VARCHAR CHECK(gender IN ('M','F')) NOT NULL,
    age          INTEGER NOT NULL,
    is_active    BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE OR REPLACE TABLE parcels (
    id                INTEGER PRIMARY KEY,
    farmer_id         INTEGER REFERENCES farmers(id),
    project_id        INTEGER REFERENCES projects(id),
    parcel_name       VARCHAR NOT NULL,
    is_active         BOOLEAN NOT NULL DEFAULT TRUE,
    area_parcel       DOUBLE NOT NULL,
    area_to_plant     DOUBLE NOT NULL,
    species_id        INTEGER REFERENCES species(id),
    number_of_tree    INTEGER NOT NULL,
    erosion_id        INTEGER REFERENCES ref_erosion(id),
    soil_texture_id   INTEGER REFERENCES ref_soil_texture(id),
    mortality_id      INTEGER REFERENCES ref_mortality(id),
    planting_model_id INTEGER REFERENCES ref_planting_model(id)
);
CREATE OR REPLACE TABLE parcel_visits (
    id                 INTEGER PRIMARY KEY,
    parcel_id          INTEGER REFERENCES parcels(id),
    farmer_id          INTEGER REFERENCES farmers(id),
    project_id         INTEGER REFERENCES projects(id),
    visit_date         DATE NOT NULL,
    trees_alive        INTEGER NOT NULL,
    trees_dead         INTEGER NOT NULL,
    mortality_id       INTEGER REFERENCES ref_mortality(id),
    submitted_by       VARCHAR NOT NULL,
    kobo_submission_id VARCHAR NOT NULL
);
CREATE OR REPLACE TABLE project_targets (
    id                   INTEGER PRIMARY KEY,
    project_id           INTEGER REFERENCES projects(id),
    target_year          INTEGER NOT NULL,
    target_trees         INTEGER NOT NULL,
    target_area_hectares DOUBLE NOT NULL,
    target_farmers       INTEGER NOT NULL,
    target_parcels       INTEGER NOT NULL,
    start_date           DATE NOT NULL,
    end_date             DATE NOT NULL
);
"""

def seed(con):
    random.seed(42)

    con.executemany("INSERT INTO regions VALUES (?, ?)", [(1, "Latin America")])

    con.executemany("INSERT INTO countries VALUES (?, ?, ?, ?)", [
        (1, 1, "Peru",     "PE"),
        (2, 1, "Colombia", "CO"),
        (3, 1, "Brazil",   "BR"),
    ])

    con.executemany("INSERT INTO species VALUES (?, ?)", [
        (1, "Cedrus atlantica"), (2, "Swietenia macrophylla"),
        (3, "Cedrela odorata"),  (4, "Tectona grandis"),
        (5, "Acacia mangium"),   (6, "Enterolobium cyclocarpum"),
    ])

    con.executemany("INSERT INTO ref_erosion VALUES (?, ?)", [
        (1, "None"), (2, "Low"), (3, "Moderate"), (4, "High"), (5, "Severe"),
    ])

    con.executemany("INSERT INTO ref_soil_texture VALUES (?, ?)", [
        (1, "Sandy"), (2, "Loamy"), (3, "Clay"), (4, "Sandy Loam"), (5, "Clay Loam"),
    ])

    con.executemany("INSERT INTO ref_mortality VALUES (?, ?)", [
        (1, "Drought"),              (2, "Flooding"),
        (3, "Pest/Disease"),         (4, "Animal Damage"),
        (5, "Competition w/ Weeds"), (6, "Poor Planting Technique"),
        (7, "Unknown"),
    ])

    con.executemany("INSERT INTO ref_planting_model VALUES (?, ?)", [
        (1, "Agroforestry"), (2, "Silvopastoral"), (3, "Windbreak"),
        (4, "Riparian Buffer"), (5, "Enrichment Planting"),
    ])

    con.executemany("INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?)", [
        (1, 1, 1, "Bosques Amazonicos Peru I",      "Peru",     2022),
        (2, 1, 1, "Reforestacion Andina Peru",       "Peru",     2023),
        (3, 1, 2, "Corredor Verde Colombia Norte",   "Colombia", 2022),
        (4, 1, 2, "Agroforestal Amazonia Colombia",  "Colombia", 2023),
        (5, 1, 3, "Refloresta Para Brasil",          "Brazil",   2022),
    ])

    con.executemany("INSERT INTO project_targets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", [
        (1, 1, 2023, 15000, 120.0, 40,  80,  date(2022,3,1),  date(2024,3,1)),
        (2, 2, 2024, 10000,  85.0, 25,  55,  date(2023,1,15), date(2025,1,15)),
        (3, 3, 2023, 18000, 145.0, 50, 100,  date(2022,6,1),  date(2024,6,1)),
        (4, 4, 2024, 12000,  95.0, 30,  65,  date(2023,4,1),  date(2025,4,1)),
        (5, 5, 2023, 20000, 160.0, 55, 110,  date(2022,2,1),  date(2024,2,1)),
    ])

    peru_m    = ["Carlos Quispe","Juan Mamani","Luis Ccoa","Pedro Huanca","Marco Flores",
                 "Alvaro Condori","Roberto Apaza","Diego Cutipa","Raul Tito","Cesar Pumari"]
    peru_f    = ["Maria Quispe","Rosa Mamani","Ana Ccoa","Lucia Huanca","Elena Flores",
                 "Carmen Condori","Silvia Apaza"]
    col_m     = ["Andres Perez","Camilo Garcia","Felipe Rodriguez","Sergio Martinez",
                 "Julian Lopez","Daniel Torres","Sebastian Gomez","Mateo Vargas",
                 "Ricardo Moreno","Santiago Diaz"]
    col_f     = ["Valentina Perez","Isabella Garcia","Sofia Rodriguez","Natalia Martinez",
                 "Paula Lopez","Daniela Torres","Mariana Gomez"]
    bra_m     = ["Joao Silva","Pedro Oliveira","Carlos Santos","Paulo Costa",
                 "Marcos Ferreira","Lucas Alves","Bruno Barbosa","Rafael Lima",
                 "Fernando Souza","Eduardo Ribeiro"]
    bra_f     = ["Maria Silva","Ana Oliveira","Lucia Santos","Fernanda Costa",
                 "Camila Ferreira","Juliana Alves","Beatriz Barbosa","Gabriela Lima"]

    proj_cfg  = {
        1: (peru_m, peru_f, 12),
        2: (peru_m, peru_f,  8),
        3: (col_m,  col_f,  14),
        4: (col_m,  col_f,   9),
        5: (bra_m,  bra_f,  13),
    }

    farmers_rows = []
    fid = 1
    proj_fids = {}
    for pid, (nm, nf, cnt) in proj_cfg.items():
        pool = [(n,'M') for n in nm] + [(n,'F') for n in nf]
        random.shuffle(pool)
        chosen = pool[:cnt]
        ids = []
        for name, gender in chosen:
            age = random.randint(28, 65)
            active = random.random() > 0.08
            farmers_rows.append((fid, pid, name, gender, age, active))
            ids.append(fid)
            fid += 1
        proj_fids[pid] = ids
    con.executemany("INSERT INTO farmers VALUES (?, ?, ?, ?, ?, ?)", farmers_rows)

    parcel_rows = []
    parcel_meta = []
    parc_id = 1
    parcel_counts = {1: 20, 2: 15, 3: 25, 4: 18, 5: 22}
    for pid, cnt in parcel_counts.items():
        fids = proj_fids[pid]
        for i in range(cnt):
            fid_p = random.choice(fids)
            name  = f"Parcela-{pid}-{i+1:03d}"
            active= random.random() > 0.05
            area_p= round(random.uniform(1.5, 8.0), 2)
            area_a= round(area_p * random.uniform(0.5, 0.85), 2)
            sp    = random.randint(1, 6)
            ntree = int(area_a * random.uniform(200, 400))
            er    = random.randint(1, 5)
            st    = random.randint(1, 5)
            mo    = random.randint(1, 7)
            pm    = random.randint(1, 5)
            parcel_rows.append((parc_id, fid_p, pid, name, active, area_p, area_a,
                                sp, ntree, er, st, mo, pm))
            parcel_meta.append((parc_id, fid_p, pid, ntree, area_a))
            parc_id += 1
    con.executemany("INSERT INTO parcels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    parcel_rows)

    visit_rows = []
    vid = 1
    months = [date(2023,m,1) for m in range(7, 13)]
    agents = ["field_agent_01","field_agent_02","field_agent_03","field_agent_04","supervisor_01"]
    for (parc_id_v, fid_v, proj_id_v, ntree_v, _) in parcel_meta:
        alive = ntree_v
        for mo in months:
            vday = mo + timedelta(days=random.randint(0, 25))
            dead = int(alive * random.uniform(0.0, 0.04))
            alive = max(0, alive - dead)
            mc   = random.randint(1, 7)
            sub  = random.choice(agents)
            kobo = f"KBO-{proj_id_v}-{parc_id_v}-{vday.strftime('%Y%m%d')}"
            visit_rows.append((vid, parc_id_v, fid_v, proj_id_v, vday, alive, dead, mc, sub, kobo))
            vid += 1
    con.executemany("INSERT INTO parcel_visits VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", visit_rows)

    print(f"Seeded: {len(farmers_rows)} farmers | {len(parcel_rows)} parcels | {len(visit_rows)} visits")


def main():
    print(f"Setting up PUR Monitor DB -> {DB_PATH}")
    con = duckdb.connect(DB_PATH)
    con.execute(DDL)
    seed(con)
    con.close()
    print(f"Done: {DB_PATH}")


if __name__ == "__main__":
    main()
