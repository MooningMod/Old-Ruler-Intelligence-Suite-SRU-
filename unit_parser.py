import csv
from dataclasses import dataclass, field
from pathlib import Path

# Global database for ingame ranges (loaded from CSV scanner)
# Structure: {unit_id: {'ground': float, 'air': float, 'surface': float, 'sub': float, 'special_41_B': float}}
RANGE_DATABASE = {}

# SRU Spotting conversion table (based on standard game values)
# Maps SpotType ID -> (range_km, strength_value)
# These values are typical for SRU - adjust if needed based on actual game data
SPOTTING_CONVERSION = {
    0: (0, 0),      # No spotting
    9: (7, 50),     # Visual Basic
    10: (10, 60),   # Visual Enhanced
    11: (12, 70),   # Visual Advanced
    12: (15, 80),   # Visual Superior
    13: (20, 90),   # Radar Basic
    14: (25, 100),  # Radar Enhanced
    15: (30, 110),  # Radar Advanced
    18: (35, 120),  # Radar Superior
    28: (40, 130),  # Radar Elite
    30: (45, 140),  # Advanced Sensors
    34: (50, 150),  # Elite Sensors
    45: (55, 160),  # Superior Detection
    50: (60, 170),  # Next-Gen Sensors
    59: (70, 180),  # Advanced Detection
    79: (80, 190),  # Strategic Detection
    89: (90, 200),  # Ultimate Detection
    96: (100, 210), # Space-grade Detection
    99: (110, 220), # Advanced Space Detection
    106: (120, 230), # Elite Space Detection
    112: (130, 240), # Superior Space Detection
    117: (140, 250), # Ultimate Space Detection
    119: (150, 260), # Next-Gen Space Detection
    134: (160, 270), # Advanced Strategic Detection
    159: (170, 280), # Elite Strategic Detection
    535: (25, 100),  # Naval Radar Basic
    541: (30, 110),  # Naval Radar Enhanced
    543: (35, 120),  # Naval Radar Advanced
    552: (40, 130),  # Naval Radar Superior
    553: (45, 140),  # Naval Radar Elite
    556: (50, 150),  # Naval Advanced Detection
    578: (55, 160),  # Naval Superior Detection
    580: (60, 170),  # Naval Elite Detection
    596: (70, 180),  # Naval Strategic Detection
}

def get_spotting_range(spot_id: int) -> tuple[int, int]:
    """
    Convert SpotType ID to (range_km, strength).
    For SRU without spotting.csv dependency.
    """
    if spot_id in SPOTTING_CONVERSION:
        return SPOTTING_CONVERSION[spot_id]
    
    # Fallback calculation for unknown IDs
    # Rough estimation based on ID value
    if spot_id == 0:
        return (0, 0)
    elif spot_id < 20:
        return (spot_id, spot_id * 5)
    elif spot_id < 100:
        return (spot_id // 2, spot_id * 2)
    elif spot_id < 200:
        return (spot_id // 3, spot_id)
    elif spot_id < 600:
        return (spot_id // 10, spot_id // 2)
    else:
        return (spot_id // 15, spot_id // 3)


def load_range_database(csv_path: str) -> dict:
    """
    Load the unit range database from scanner CSV.
    Returns: {unit_id: {'ground': float, 'air': float, 'surface': float, 'sub': float, 'special_41_B': float}}
    """
    global RANGE_DATABASE
    RANGE_DATABASE.clear()
    
    path = Path(csv_path)
    if not path.exists():
        return RANGE_DATABASE
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    unit_id = int(row['unit_id'])
                    
                    # Parse ranges (can be empty string)
                    ground = float(row['ground']) if row['ground'] else 0.0
                    air = float(row['air']) if row['air'] else 0.0
                    surface = float(row['surface']) if row['surface'] else 0.0
                    sub = float(row['sub']) if row['sub'] else 0.0
                    special_41_B = float(row['special_41_B']) if row.get('special_41_B') else 0.0
                    
                    RANGE_DATABASE[unit_id] = {
                        'ground': ground,
                        'air': air,
                        'surface': surface,
                        'sub': sub,
                        'special_41_B': special_41_B
                    }
                except (ValueError, KeyError):
                    continue
    except Exception:
        pass
    
    return RANGE_DATABASE


def parse_int(value: str) -> int:
    """Parse string to int, returning 0 on error/empty."""
    try:
        value = value.strip()
        if not value:
            return 0
        return int(float(value))
    except Exception:
        return 0


def parse_float(value: str) -> float:
    """Parse string to float, returning 0.0 on error/empty."""
    try:
        value = value.strip()
        if not value:
            return 0.0
        return float(value)
    except Exception:
        return 0.0

@dataclass
class Unit:
    """
    Representation of an SRU unit based on DEFAULT.UNIT.
    """

    # Identity
    id: int = 0
    name: str = ""
    class_num: int = 0
    year: str = "N/A"
    region: str = ""
    model_code: str = ""          # SRU ha solo "ModelCode+EquipName": lo teniamo separato per il futuro
    tech_level: int = 0           # non presente in SRU, ma utile per UI

    # Tech Requirement / upgrade path
    req_tech_id: int = 0          # alias di tech_req_1 per compatibilità
    tech_req_1: int = 0           # TechReq1 (col 23)
    tech_req_2: int = 0           # TechReq2 (col 24)
    upgrade_unit: int = 0         # UGTo (col 15)
    replace_by: int = 0           # ReplaceBy (col 16)
    refit_to: int = 0             # RefitTo (col 17)

    # Strength / Personnel
    strength: int = 1
    crew: int = 0
    personnel: int = 0

    # Economy / Production
    days: int = 0                 # giorni totali per battaglione
    cost: float = 0.0             # costo totale in M
    ig_cost: float = 0.0          # Industrial Goods totali
    ur_cost: float = 0.0          # Uranium Goods totali (da URCost)
    mg_cost: float = 0.0          # placeholder (SRU non lo fornisce esplicito)
    maintenance_mg: float = 0.0   # placeholder
    uranium_req: float = 0.0      # alias di ur_cost per la UI
    weight: int = 0               # peso totale (t)

    # Movement / Supply
    speed: int = 0               # km/h
    move_range: int = 0          # km

    # Fuel System
    fuel: float = 0.0            # t per singolo veicolo (dal file)
    fuel_battalion: float = 0.0  # t per battaglione (calcolato)
    fuel_cap: float = 0.0        # alias per la UI (stessa cosa di fuel_battalion)

    combat_time: int = 0
    supply_t: float = 0.0        # t per battaglione

    # Initiative / Stealth
    initiative: int = 0
    stealth: int = 0

    # Spotting System
    spot1_id: int = 0            # SpotType1 ID
    spot2_id: int = 0            # SpotType2 ID
    spot1_range_km: int = 0      # range convertito
    spot2_range_km: int = 0
    spot1_strength: int = 0      # “forza” sensore (lookup)
    spot2_strength: int = 0

    # Legacy fields (per compat con painters vecchi)
    spot1: int = 0
    spot2: int = 0

    # Capacities
    missile_cap: int = 0
    transport_cap: int = 0
    cargo_cap: int = 0
    carrier_cap: int = 0

    # Missile Details
    missile_size_max: int = 0      # MisislePtsValue
    launch_type: int = 0           # LaunchType (bitmask)
    launch_types_str: str = ""     # es. "Land, Air"

    # Combat Values (Attack)
    soft: float = 0.0
    hard: float = 0.0
    fort: float = 0.0
    air_low: float = 0.0
    air_mid: float = 0.0
    air_high: float = 0.0
    naval_surf: float = 0.0
    naval_sub: float = 0.0
    close_combat: float = 0.0

    # Defense Values
    def_ground: float = 0.0
    def_air: float = 0.0
    def_indirect: float = 0.0
    def_close: float = 0.0

    # Ranges (RAW) from DEFAULT.UNIT (col 50-53)
    range_ground: int = 0
    range_air: int = 0
    range_surf: int = 0
    range_sub: int = 0

    # Ranges (km) - INGAME from scanner database (DEF)
    range_ground_def: float = 0.0
    range_air_def: float = 0.0
    range_surf_def: float = 0.0
    range_sub_def: float = 0.0

    # Ranges (km) usate dalla UI (preferisce DEF, fallback RAW)
    range_ground_km: float = 0.0
    range_air_km: float = 0.0
    range_surface_km: float = 0.0
    range_sub_km: float = 0.0

    # Missile Range (special_41_B) - shown under attack stats in-game
    missile_range_km: float = 0.0

    # Boolean Flags (0/1)
    indirect_fire: int = 0
    ballistic_art: int = 0
    nbc: int = 0
    ecm: int = 0
    no_eff_loss_move: int = 0
    ftl: int = 0               # per SRU sarà sempre 0 (placeholder)
    survey: int = 0            # idem
    river_xing: int = 0
    airdrop: int = 0
    air_tanker: int = 0
    air_refuel: int = 0
    amph: int = 0
    bridge_build: int = 0
    engineering: int = 0
    stand_off: int = 0
    move_fire_penalty: int = 0
    no_land_cap: int = 0
    has_production: int = 0
    supply_move_only: int = 0
    low_visibility: int = 0

    # Techs that upgrade this unit (SRU specific columns alla fine del file)
    tech_ids: list[int] = field(default_factory=list)

    def matches(self, query: str) -> bool:
        """Search by Name or ID."""
        q = query.lower()
        return q in self.name.lower() or q == str(self.id)


def parse_default_unit(file_path: str) -> list[Unit]:
    """
    Parses DEFAULT.UNIT into a list of Unit objects.
    Adapted for SRU format.
    """
    units: list[Unit] = []

    try:
        with open(file_path, "r", encoding="latin-1", errors="replace") as f:
            lines = f.readlines()

        start_index = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("&&UNITS"):
                start_index = i + 1
                break

        csv_reader = csv.reader(lines[start_index:], delimiter=",", quotechar='"')

        for row in csv_reader:
            if not row: continue
            if row[0].strip().startswith("//"): continue
            if len(row) < 80: continue

            try:
                u = Unit()

                # --- 1. Identity ---
                u.id = parse_int(row[0])
                u.name = row[1].strip().strip('"')
                u.class_num = parse_int(row[2])

                year_val = parse_int(row[4])
                u.year = str(1900 + year_val) if year_val > 0 else "N/A"
                u.region = row[12].strip()
                
                # Tech Req
                                # --- 1b. Tech Req / upgrade path ---
                u.tech_req_1 = parse_int(row[23])   # TechReq1
                u.tech_req_2 = parse_int(row[24])   # TechReq2
                u.req_tech_id = u.tech_req_1        # alias per compatibilità

                u.upgrade_unit = parse_int(row[15])  # UGTo
                u.replace_by = parse_int(row[16])    # ReplaceBy
                u.refit_to = parse_int(row[17])      # RefitTo


                # --- 2. Strength & Personnel ---
                u.strength = parse_int(row[13]) or 1      
                u.crew = parse_int(row[14])               
                u.personnel = u.strength * u.crew

                # --- 3. Initiative & Stealth ---
                u.initiative = parse_int(row[9])
                u.stealth = parse_int(row[10])

                # --- 4. Capacities ---
                u.carrier_cap = parse_int(row[11])
                u.missile_cap = parse_int(row[20]) * u.strength
                u.cargo_cap = parse_int(row[30])
                u.transport_cap = parse_int(row[31])

                # --- 5. Spotting System (Direct Conversion) ---
                u.spot1_id = parse_int(row[21])              
                u.spot2_id = parse_int(row[22])
                
                # Compat legacy
                u.spot1 = u.spot1_id
                u.spot2 = u.spot2_id

                # Conversione con lookup: (range_km, strength)
                try:
                    r1, s1 = get_spotting_range(u.spot1_id)
                    r2, s2 = get_spotting_range(u.spot2_id)
                    u.spot1_range_km = r1
                    u.spot2_range_km = r2
                    u.spot1_strength = s1
                    u.spot2_strength = s2
                except Exception:
                    u.spot1_range_km = 0
                    u.spot2_range_km = 0
                    u.spot1_strength = 0
                    u.spot2_strength = 0

                # --- 6. Economy ---
                days_per_unit = parse_float(row[25])      # DaysToBuild
                cost_per_unit = parse_float(row[26])      # Cost
                ig_per_unit = parse_float(row[27])        # IGCost
                ur_per_unit = parse_float(row[28])        # URCost (uranium)
                weight_per_unit = parse_float(row[29])    # Weight

                u.days = int(days_per_unit * u.strength)
                u.cost = cost_per_unit * u.strength
                u.ig_cost = ig_per_unit * u.strength
                u.ur_cost = ur_per_unit * u.strength
                u.uranium_req = u.ur_cost             
                u.weight = int(weight_per_unit * u.strength)


                # --- 7. Movement & Fuel ---
                u.speed = parse_int(row[19])
                u.move_range = parse_int(row[32])
                
                # Fuel calculation
                u.fuel = parse_float(row[34])             # Per vehicle
                u.fuel_battalion = round(u.fuel * u.strength, 1) # Total Battalion
                u.fuel_cap = u.fuel_battalion  # UI  "Fuel Capacity"
                
                u.combat_time = parse_int(row[35])

                supply_cap_per_unit = parse_float(row[36])
                if supply_cap_per_unit:
                    u.supply_t = round(supply_cap_per_unit * u.strength, 2)

                # --- 8. Combat Values (Attack) ---
                u.soft = parse_float(row[37])
                u.hard = parse_float(row[38])
                u.fort = parse_float(row[39])
                u.air_low = parse_float(row[40])
                u.air_mid = parse_float(row[41])
                u.air_high = parse_float(row[42])
                u.naval_surf = parse_float(row[43])
                u.naval_sub = parse_float(row[44])
                u.close_combat = parse_float(row[45])

                # --- 9. Defense ---
                u.def_ground = parse_float(row[46])
                u.def_air = parse_float(row[47])
                u.def_indirect = parse_float(row[48])
                u.def_close = parse_float(row[49])

                # --- 10. Ranges ---
                u.range_ground = parse_int(row[50])
                u.range_air = parse_int(row[51])
                u.range_surf = parse_int(row[52])
                u.range_sub = parse_int(row[53])
                
                # --- 10b. Load DEF Ranges from Database ---
                if u.id in RANGE_DATABASE:
                    db_entry = RANGE_DATABASE[u.id]
                    u.range_ground_def = db_entry.get('ground', 0.0)
                    u.range_air_def = db_entry.get('air', 0.0)
                    u.range_surf_def = db_entry.get('surface', 0.0)
                    u.range_sub_def = db_entry.get('sub', 0.0)
                    u.missile_range_km = db_entry.get('special_41_B', 0.0)
                # --- 10c. Ranges for UI (prefer DEF, fallback RAW) ---
                u.range_ground_km = u.range_ground_def or u.range_ground
                u.range_air_km = u.range_air_def or u.range_air
                u.range_surface_km = u.range_surf_def or u.range_surf
                u.range_sub_km = u.range_sub_def or u.range_sub

                # --- 11. Flags ---
                u.indirect_fire = parse_int(row[56])      # IndirectFlag
                u.ballistic_art = parse_int(row[57])      # BalisticArt
                u.nbc = parse_int(row[58])                # NBCProt

                # 59 TurretRot 
                # 60 LimitedFiringArc 
                # 61 TurretImmed
                # 62 LongDeckCarrier
                # 63 DirectDef

                u.ecm = parse_int(row[64]) if len(row) > 64 else 0          # ECMEquipped
                u.no_eff_loss_move = parse_int(row[65]) if len(row) > 65 else 0  # NoEffLossMove
                u.river_xing = parse_int(row[66]) if len(row) > 66 else 0        # RiverXing
                u.airdrop = parse_int(row[67]) if len(row) > 67 else 0           # Airdrop
                u.air_tanker = parse_int(row[68]) if len(row) > 68 else 0        # AirTanker
                u.air_refuel = parse_int(row[69]) if len(row) > 69 else 0        # AirRefuel

                # 70 ShortDeckTakeOff, 71 LongDeckTakeOff (non usati nella UI ora)
                u.amph = parse_int(row[72]) if len(row) > 72 else 0              # Amphibious

                # 73,74 filler
                u.bridge_build = parse_int(row[75]) if len(row) > 75 else 0      # BridgeBuild
                # 76 UGDemol (non mappato)
                u.engineering = parse_int(row[77]) if len(row) > 77 else 0       # EngineeringUnit
                # 78 DockToUnload (non mappato)
                u.stand_off = parse_int(row[79]) if len(row) > 79 else 0         # StandOffUnit
                u.move_fire_penalty = parse_int(row[80]) if len(row) > 80 else 0 # MoveFirePenalty
                u.no_land_cap = parse_int(row[81]) if len(row) > 81 else 0       # NoLandCap
                u.has_production = parse_int(row[82]) if len(row) > 82 else 0    # HasProduction
                u.supply_move_only = parse_int(row[83]) if len(row) > 83 else 0  # SupplyMoveOnly
                u.low_visibility = parse_int(row[84]) if len(row) > 84 else 0    # LowVisibility

                
                # --- 12. Missiles Details ---
                if len(row) > 110:
                    u.launch_type = parse_int(row[109]) if len(row) > 109 else 0
                    u.missile_size_max = parse_int(row[110])
                    lt = u.launch_type
                    types = []
                    if lt & 1: types.append("Land")
                    if lt & 2: types.append("Air")
                    if lt & 4: types.append("Naval")
                    if lt & 8: types.append("Sub")
                    u.launch_types_str = ", ".join(types) if types else "-"
                else:
                    u.launch_types_str = "-"
                    
                # --- 13. Tech IDs (SRU specific columns) ---
                # SRU stores tech_ids in different columns than SR2030
                # Columns identified by diagnostic: 126, 123, 125, 127, 129, 130, 131, 132
                u.tech_ids = []
                units.append(u)

            except Exception as e:
                # Uncomment to debug specific row errors
                # print(f"Error parsing row {row[0]}: {e}")
                continue

    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return []

    return units
