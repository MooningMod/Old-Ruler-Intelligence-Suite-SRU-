import csv

def load_tech_file(path):
    """
    Legge DEFAULT.TTRX / DEFAULT.TTR per SRU.
    Estrae:
      - ID tech
      - short_title (dal commento // a fine riga)
      - effetti (Effect 1/2 + EffectValue 1/2)

    Layout header SRU :
    0  ID
    1  Category
    2  SR6 Tech Level
    3  Pic
    4  Prereq 1
    5  Prereq 2
    6  Effect 1
    7  Effect 2
    8  Effect Value 1
    9  Effect Value 2
    10 Time to Res
    11 Cost
    12 Pop Support
    13 World Support
    14 AI Interest
    15 Tradeable?
    16 Set by Default
    17 Unit Requirement
    18 Tech Requirement
    19 Facility Requirement
    20 EraTech
    21 Cabinet AI Interest
    22 WM Offer Interest
    23 // Short Title (commento)
    """

    TECH_DATA_LIGHT = {}
    TECH_DATA_FULL = {}

    try:
        with open(path, "r", encoding="Windows-1252", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"[Parser] Errore apertura file {path}: {e}")
        return {}, {}

    # Trova inizio dati (&&TTR / &&TECHS / prima riga numerica)
    start_index = None
    for i, line in enumerate(lines):
        if line.strip().startswith("&&TTR") or line.strip().startswith("&&TECHS"):
            start_index = i + 1
            break

    if start_index is None:
        for i, line in enumerate(lines):
            if line.strip().startswith("//") or not line.strip():
                continue
            parts = line.split(',')
            if parts and parts[0].strip().isdigit():
                start_index = i
                break

    if start_index is None:
        return {}, {}

    data_lines = lines[start_index:]
    reader = csv.reader(data_lines, delimiter=",")

    for row, raw_line in zip(reader, data_lines):
        if len(row) < 10:
            continue

        # ID Tech
        try:
            tech_id = int(row[0])
            if tech_id == 0:
                continue
        except ValueError:
            continue

        # 1) Short title dal commento // (più robusto)
        short_title = ""
        if "//" in raw_line:
            comment_part = raw_line.split("//", 1)[1].strip()
            if comment_part:
                short_title = comment_part

        # 2) Fallback: ultima colonna
        if not short_title and len(row) > 0:
            last_col = row[-1].strip()
            if "//" in last_col:
                short_title = last_col.split("//", 1)[-1].strip()
            elif not last_col.isdigit() and len(last_col) > 3:
                short_title = last_col

        if not short_title:
            if "//" in raw_line:
                short_title = raw_line.split("//",1)[1].strip()

        # fallback finale
        if not short_title:
            short_title = f"Tech {tech_id}"

        # -------------------------
        # EFFETTI (SRU CORRETTI)
        # -------------------------
        effect_ids = []
        # Effect 1, Effect 2
        for col in (6, 7):
            if col < len(row) and row[col].strip():
                try:
                    eid = int(float(row[col]))
                    if eid != 0:
                        effect_ids.append(eid)
                except Exception:
                    pass

        effect_values = []
        # Effect Value 1, Effect Value 2
        for col in (8, 9):
            if col < len(row) and row[col].strip():
                try:
                    effect_values.append(float(row[col]))
                except Exception:
                    pass

        # Costruiamo lista effetti (id + value)
        effects = [
            {"effect_id": eid, "value": val}
            for eid, val in zip(effect_ids, effect_values)
        ]

        TECH_DATA_LIGHT[tech_id] = {
            "short_title": short_title,
            "effects": effects,
        }
        if not TECH_DATA_LIGHT[tech_id]["effects"]:
            TECH_DATA_LIGHT[tech_id]["effects"] = []

        # Dati completi (per debug / Tech view)
        def get_col(idx):
            return row[idx] if idx < len(row) else ""

        TECH_DATA_FULL[tech_id] = {
            "id": tech_id,
            "short_title": short_title,
            "category": get_col(1),
            "tech_level": get_col(2),
            "prereq_1": get_col(4),
            "prereq_2": get_col(5),
            "time_to_research": get_col(10),
            "cost": get_col(11),
            "effect_ids": effect_ids,
            "effect_values": effect_values,
        }

    print(f"[TechParser] Caricate {len(TECH_DATA_LIGHT)} tech da {path}")
    return TECH_DATA_LIGHT, TECH_DATA_FULL
