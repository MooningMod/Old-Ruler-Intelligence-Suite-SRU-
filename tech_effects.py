import copy
from typing import Dict, Tuple, Set, Optional
from unit_parser import Unit

# ===========================================================================================
# GLOBAL EFFECTS MAP (Text Descriptions)
# Effects that modify Nation, Economy, Production, or Social Ratings.
# These do NOT modify individual unit statistics in the comparison table,
# but do affect global efficiency or production.
# ===================================================================================================================
GLOBAL_EFFECT_MAP = {
    # --- Production Costs & Efficiencies (2-23) ---
    2: "Finished Goods Fac. Cost",
    3: "Fac. Construction Mat. Use",
    5: "Research Efficiency",
    6: "Counter Intel Efficiency",
    7: "Intelligence Efficiency",
    8: "Military Efficiency (Global)",
    9: "City Power Generation",
    12: "Chemical Weapon Protection",
    13: "Global Fuel Consumption",
    14: "Motorized Unit Cost",
    15: "Unit Build Speed",
    16: "Facility Build Speed",
    18: "Finished Goods Fac. Efficiency",
    19: "Finished Goods Costs",
    21: "Space Knowledge", # (GR: Space Race)
    22: "Nuclear Plant Maint. Cost",
    23: "GUI Skin",

    # --- Raw Material Usage in Production (24-34) ---
    24: "Factory Agri Use", 25: "Factory Rubber/Water Use",
    26: "Factory Timber Use", 27: "Factory Petrol Use",
    28: "Factory Coal Use", 29: "Factory Ore Use",
    30: "Factory Uranium Use", 31: "Factory Power Use",
    32: "Factory Cons. Goods Use", 33: "Factory Ind. Goods Use",
    34: "Factory Mil. Goods Use",

    # --- Facility Output (35-55) ---
    35: "SynRubber Prod", 36: "Hydroponics Prod", 37: "Composites Prod",
    38: "SynFuel Prod", 39: "Coal Power Prod", 40: "Nuclear Power Prod",
    41: "Petrol Power Prod", 42: "Other Power Prod", 43: "Fusion Power Prod",
    44: "Consumer Goods Prod", 45: "Industrial Goods Prod", 46: "Military Goods Prod",
    47: "Antimatter Prod", 48: "Dark Energy Prod", 55: "Oil Derrick Prod",

    # --- Races / Global Flags (56-59) ---
    56: "Atomic Race",
    57: "Pandemic Race",
    58: "Internet Race",
    59: "Mars Race",

    # --- Population Resource Usage (60-70) ---
    60: "Pop Agri Use", 61: "Pop Rubber/Water Use",
    62: "Pop Timber Use", 63: "Pop Petrol Use",
    64: "Pop Coal Use", 65: "Pop Ore Use",
    66: "Pop Uranium Use", 67: "Pop Power Use",
    68: "Pop Consumer Goods Use", 69: "Pop Ind. Goods Use",
    70: "Pop Mil. Goods Use",

    # --- Resource Output (72-82) ---
    72: "Agri Output", 73: "Rubber/Water Output", 74: "Timber Output",
    75: "Petrol Output", 76: "Coal Output", 77: "Ore Output",
    78: "Uranium Output", 79: "Power Output (All)", 
    80: "Consumer Goods Output", 81: "Industrial Goods Output", 
    82: "Military Goods Output",

    # --- Efficiency of Goods Production (84-94) ---
    84: "Agri Efficiency", 85: "Rubber/Water Efficiency", 
    86: "Timber Efficiency", 87: "Petrol Efficiency", 
    88: "Coal Efficiency", 89: "Ore Efficiency", 
    90: "Uranium Efficiency", 91: "Power Efficiency", 
    92: "Consumer Goods Efficiency", 93: "Industrial Goods Efficiency",
    94: "Military Goods Efficiency",

    # --- Special Levels (96-97) ---
    96: "Garrison/Partisan Level",
    97: "Locomotive Level",

    # --- Social Ratings (100-107) ---
    100: "Health Care Rating", 101: "Education Rating", 
    102: "Infrastructure Rating", 103: "Environment Rating",
    104: "Family Rating", 105: "Law Enforcement Rating",
    106: "Cultural Rating", 107: "Social Services Rating",

    # --- Social Costs (108-115) ---
    108: "Health Care Cost", 109: "Education Cost",
    110: "Infrastructure Cost", 111: "Environment Cost",
    112: "Family Subsidy Cost", 113: "Law Enforcement Cost",
    114: "Cultural Cost", 115: "Social Services Cost",

    # --- Space / Galactic Ruler Specific (128-137) ---being in doubt I put them
    128: "FTL Range", 
    129: "Space Ballistic Defense", 130: "Space Beam Defense",
    131: "Space Ballistic Attack", 132: "Space Beam Attack",
    133: "Space Ballistic Range", 134: "Space Beam Range",
    135: "Space Shield Efficiency",
    136: "FTL Charge Speed", 
    137: "Ore Harvester Capacity",

    # --- Pandemic Mechanics (171-173) ---
    171: "Infection Rate",
    172: "Mortality Rate",
    173: "Trade Infection Risk",
}

# ===========================================================================================
# UNIT STAT MODIFIERS (ID 140-170)
# Modify specific attributes of the Unit object (Unit Upgrade Techs).
# Mapping: (unit_attribute, operation_mode)
# mode "mul": base * (1.0 + value)
# mode "add": base + value
# ===========================================================================================
EFFECT_MAP: Dict[int, Tuple[str, str]] = {       
    # Attack Values
    140: ("soft", "mul"),
    141: ("hard", "mul"),
    142: ("fort", "mul"),
    143: ("air_low", "mul"),
    144: ("air_mid", "mul"),
    145: ("air_high", "mul"),
    146: ("naval_surf", "mul"), 
    147: ("naval_sub", "mul"),
    148: ("close_combat", "mul"),
    
    # Ranges
    150: ("range_ground", "mul"),
    151: ("range_air", "mul"),
    # Nota: In Galactic Ruler, 152 is Ballistic and 153 is Energy
    152: ("range_surf", "mul"),
    153: ("range_sub", "mul"),
    
    # Defense
    # Nota: In Galactic Ruler, 154 is Hull, 155 is Shield
    154: ("def_ground", "mul"),
    155: ("def_air", "mul"),
    156: ("def_indirect", "mul"),
    157: ("def_close", "mul"),
    
    # Specs
    158: ("speed", "mul"),
    159: ("stealth", "mul"),
    160: ("initiative", "mul"),
    161: ("combat_time", "mul"), # Ammo efficiency (1.0 = double shots)
    
    # Logistics
    # 162: "1.0 would reduce range by half (increase fuel consumption by 100%)"
    # Mappiamo su fuel_consumption se l'attributo esiste.
    162: ("fuel_consumption", "mul"), 
    163: ("missile_cap", "add"),
    164: ("efficiency", "mul"), # Unit Quality/Morale base
    165: ("ammo", "add"),       
    166: ("fuel_battalion", "mul"),       # Fuel Capacity techs increase the total tank
    
    # Specific Spotting Unit
    167: ("spot1_range_km", "mul"),     # Spotting 1 Range
    168: ("spot2_range_km", "mul"),       # Spotting 2 Range
    169: ("spot1", "mul"),      # Spotting 1 Strength (spesso mappato stesso attr di range in parser semplici)
    170: ("spot2", "mul"),      # Spotting 2 Strength
}


GLOBAL_UNIT_EFFECT_MAP = {
    116: (["def_ground", "def_close"], "mul"),
    117: (["def_ground", "def_close"], "mul"),
    118: (["soft", "hard", "close_combat"], "mul"),
    119: (["air_low", "air_mid", "air_high"], "mul"),
    120: (["naval_surf"], "mul"),
    121: (["naval_sub"], "mul"),
    122: (["range_ground"], "mul"),
    123: (["accuracy"], "mul"),
    124: (["stealth"], "mul"),
    125: (["spot1_range_km","spot2_range_km"], "mul"),
    126: (["range_ground"], "mul"),
    127: (["def_ground"], "mul"),
}

# =============================================================================
# BOOLEAN FLAGS ( 0 -> 1)
# ID 200+
# =============================================================================
BOOL_EFFECT_MAP: Dict[int, str] = {
    201: "sosus_enabled",
    202: "nuclear_weapons_enabled",
    203: "chemical_weapons_enabled",
    204: "biological_weapons_enabled",
    205: "comsat_enabled",
    206: "recon_sat_enabled",
    207: "mdi_sat_enabled",
    209: "cyberattack_enabled",
    234: "ecm",                  # Electronic Counter Measures
}

def apply_techs_to_unit(
    unit: Optional[Unit],
    tech_ids: Set[int],
    tech_light: Dict[int, dict],
) -> Optional[Unit]:

    if unit is None or not tech_ids or not tech_light:
        return unit

    modified = copy.deepcopy(unit)

    for tid in tech_ids:
        tech_info = tech_light.get(tid)
        if not tech_info:
            continue

        effects = tech_info.get("effects", [])
        for eff in effects:
            eid = eff.get("effect_id")
            val = eff.get("value", 0.0)

            if eid is None: continue

            # Handle Booleans (Enable/Disable flags)
            if eid in BOOL_EFFECT_MAP:
                attr_flag = BOOL_EFFECT_MAP[eid]
                if not hasattr(modified, attr_flag):
                    setattr(modified, attr_flag, 0)
                try:
                    setattr(modified, attr_flag, 1)
                except: pass
                continue
                
            # Handle Global Military Bonuses (116-127)
            if eid in GLOBAL_UNIT_EFFECT_MAP:
                attrs, mode = GLOBAL_UNIT_EFFECT_MAP[eid]
                for attr in attrs:
                    base = getattr(modified, attr, 0.0)
                    if base is None:
                        continue
                    try:
                        if mode == "mul":
                            new_val = base * (1.0 + float(val))
                            setattr(modified, attr, new_val)
                        elif mode == "add":
                            setattr(modified, attr, base + float(val))
                    except:
                        pass
                continue


            # Handle Stats Unit Upgrade (Multiplicative/Additive)
            if eid in EFFECT_MAP:
                attr, mode = EFFECT_MAP[eid]
                
                # Special Case: Global Spotting (125) applies to BOTH ranges if possible
                if eid == 125:
                    # Apply to Visual
                    base1 = getattr(modified, "spot1_range_km", 0)
                    if base1 > 0:
                        setattr(modified, "spot1_range_km", int(base1 * (1.0 + float(val))))
                    
                    # Apply to Radar
                    base2 = getattr(modified, "spot2_range_km", 0)
                    if base2 > 0:
                        setattr(modified, "spot2_range_km", int(base2 * (1.0 + float(val))))
                    continue
                
                # Special Case: Range Modifiers (150-153) apply to RAW, DEF, and missile ranges
                if eid in (150, 151, 152, 153):
                    # Apply to RAW range
                    base = getattr(modified, attr, 0.0)
                    if base is not None and base > 0:
                        try:
                            if mode == "mul":
                                new_val = base * (1.0 + float(val))
                                setattr(modified, attr, int(new_val))
                        except: pass
                    
                    # Apply to corresponding DEF range
                    def_attr = attr + "_def"
                    base_def = getattr(modified, def_attr, 0.0)
                    if base_def is not None and base_def > 0:
                        try:
                            if mode == "mul":
                                new_val_def = base_def * (1.0 + float(val))
                                setattr(modified, def_attr, new_val_def)
                        except: pass
                    
                    # Apply to missile_range_km for missile units
                    missile_base = getattr(modified, "missile_range_km", 0.0)
                    if missile_base > 0:
                        try:
                            if mode == "mul":
                                new_missile_range = missile_base * (1.0 + float(val))
                                setattr(modified, "missile_range_km", new_missile_range)
                        except: pass
                    
                    continue
                
                # Standard Handling for all other attributes
                base = getattr(modified, attr, 0.0)
                if base is None: continue

                try:
                    if mode == "mul":
                        # ex: val=0.1 (10%) -> base * 1.1
                        new_val = base * (1.0 + float(val))
                        # Keep int for ranges/spotting, float for others
                        if "range" in attr or "spot" in attr or "speed" in attr:
                            setattr(modified, attr, int(new_val))
                        else:
                            setattr(modified, attr, new_val)
                            
                    elif mode == "add":
                        setattr(modified, attr, base + float(val))
                except: continue
    return modified