import pymem
import pymem.process
import struct
import logging
from typing import List, Tuple, Dict, Optional

"""
Supreme Ruler Ultimate - Memory Reader v2.2 (PERSISTENT)
- Persistent connection to avoid handle open/close overhead
- Much faster, prevents skipping days when the game runs at high speed
- Based on QRti trainer offsets
- Includes Social Spending variables
"""

PROCESS_NAME = "SupremeRulerUltimate.exe"

# ------------------------------------------------
# POINTER SETUP (SRU)
# ------------------------------------------------
# RVA from module base (assumed 0x400000)
MAIN_PTR_RVA   = 0x0104D130
MARKET_PTR_RVA = 0x01105DEC

# ------------------------------------------------
# VARIABLE LISTS
# Names MUST match data_logger.ALL_POSSIBLE_COLUMNS
# ------------------------------------------------

VARIABLES: List[Tuple[str, int, str]] = [
    # --- Domestic / World Market ---
    ("Domestic Approval",        0x7ABC, "float"),
    ("Military Approval",        0x7AC0, "float"),
    ("World Market Opinion",     0x7AB0, "float"),
    ("Treaty Integrity",         0x7AB4, "float"),
    ("Subsidy Rate",             0x7AC8, "float"),
    ("Credit Rating",            0x7AD0, "float"),
    ("Tourism",                  0x7AD4, "float"),
    ("Literacy",                 0x7AD8, "float"),

    # --- Population / Army ---
    ("Population",               0x7AF0, "float"),
    ("Active Personnel",         0x7B08, "float"),
    ("Reserve Personnel",        0x7B0C, "float"),
    ("Unemployment",             0x7B10, "float"),
    ("Immigration",              0x7B14, "float"),
    ("Emigration",               0x7B18, "float"),
    ("Births",                   0x7B1C, "float"),
    ("Deaths",                   0x7B20, "float"),

    # --- Macro / Finance ---
    ("Treasury",                 0x7B30, "float"),
    ("Bond Debt",                0x7B3C, "float"),
    ("GDP/c",                    0x7BE0, "float"),
    ("Inflation",                0x7BF0, "float"),
    ("Research Efficiency",      0x7C74, "float"),

    # --- Social Spending (restored from old version) ---
    ("Health Care",              0x8774, "float"),
    ("Education",                0x8778, "float"),
    ("Infrastructure",           0x877C, "float"),
    ("Environment",              0x8780, "float"),
    ("Family Subsidy",           0x8784, "float"),
    ("Law Enforcement",          0x8788, "float"),
    ("Culture Subsidy",          0x878C, "float"),
    ("Social Assistance",        0x8790, "float"),

    # --- Resources: STOCKS ---
    ("Agriculture",              0x7D18, "float"),
    ("Rubber",                   0x7DF0, "float"),
    ("Timber",                   0x7EC8, "float"),
    ("Petroleum",                0x7FA0, "float"),
    ("Coal",                     0x8078, "float"),
    ("Metal Ore",                0x8150, "float"),
    ("Uranium",                  0x8228, "float"),
    ("Electric Power",           0x8300, "float"),
    ("Consumer Goods",           0x83D8, "float"),
    ("Industry Goods",           0x84B0, "float"),
    ("Military Goods",           0x8588, "float"),

    # --- Resources: PRODUCTION COSTS ---
    ("Agriculture Production Cost",    0x7D50, "float"),
    ("Rubber Production Cost",         0x7E28, "float"),
    ("Timber Production Cost",         0x7ECC, "float"),
    ("Petroleum Production Cost",      0x7FD8, "float"),
    ("Coal Production Cost",           0x807C, "float"),
    ("Metal Ore Production Cost",      0x8154, "float"),
    ("Uranium Production Cost",        0x822C, "float"),
    ("Electric Power Production Cost", 0x8338, "float"),
    ("Consumer Goods Production Cost", 0x8410, "float"),
    ("Industry Goods Production Cost", 0x84E8, "float"),
    ("Military Goods Production Cost", 0x85C0, "float"),

    # --- Resources: TRADES ---
    ("Agriculture Trades",       0x7D54, "float"),
    ("Rubber Trades",            0x7E2C, "float"),
    ("Timber Trades",            0x7F04, "float"),
    ("Petroleum Trades",         0x7FDC, "float"),
    ("Coal Trades",              0x80B4, "float"),
    ("Metal Ore Trades",         0x818C, "float"),
    ("Uranium Trades",           0x8260, "float"),
    ("Electric Power Trades",    0x833C, "float"),
    ("Consumer Goods Trades",    0x8414, "float"),
    ("Industry Goods Trades",    0x84EC, "float"),
    ("Military Goods Trades",    0x85C4, "float"),
]

# Resource market prices - from second pointer
MARKET_PRICES: List[Tuple[str, int, str]] = [
    ("Agriculture Market Price",      0x06C, "float"),
    ("Rubber Market Price",           0x0F0, "float"),
    ("Timber Market Price",           0x178, "float"),
    ("Petroleum Market Price",        0x1F8, "float"),
    ("Coal Market Price",             0x27C, "float"),
    ("Metal Ore Market Price",        0x300, "float"),
    ("Uranium Market Price",          0x384, "float"),
    ("Electric Power Market Price",   0x408, "float"),
    ("Consumer Goods Market Price",   0x48C, "float"),
    ("Industry Goods Market Price",   0x510, "float"),
    ("Military Goods Market Price",   0x594, "float"),
]


class MemoryReader:
    """
    Persistent memory manager for Supreme Ruler Ultimate.
    Keeps the process handle open to maximize read speed and minimize CPU overhead.
    """

    def __init__(self, process_name: str = PROCESS_NAME):
        self.process_name = process_name
        self.pm: Optional[pymem.Pymem] = None
        self.base_address: Optional[int] = None
        self.main_base_ptr: Optional[int] = None
        self.market_base_ptr: Optional[int] = None

    def attach(self) -> bool:
        """Attempts to attach to the process and resolve base pointers."""
        try:
            self.pm = pymem.Pymem(self.process_name)
            mod = pymem.process.module_from_name(self.pm.process_handle, self.process_name)
            self.base_address = mod.lpBaseOfDll
            
            # Pre-resolve the pointers. We only do this once (or on retry).
            self._refresh_pointers()
            
            return True
        except Exception as e:
            logging.debug(f"Failed to attach: {e}")
            self.pm = None
            return False

    def _refresh_pointers(self):
        """Resolves the main and market base pointers."""
        if not self.pm or not self.base_address:
            return

        try:
            main_ptr_addr = self.base_address + MAIN_PTR_RVA
            market_ptr_addr = self.base_address + MARKET_PTR_RVA

            self.main_base_ptr = self.pm.read_uint(main_ptr_addr)
            self.market_base_ptr = self.pm.read_uint(market_ptr_addr)

            # Set to None if pointer is null
            if self.main_base_ptr == 0:
                self.main_base_ptr = None
            if self.market_base_ptr == 0:
                self.market_base_ptr = None
                
        except Exception as e:
            logging.debug(f"Failed to refresh pointers: {e}")
            self.main_base_ptr = None
            self.market_base_ptr = None

    def read_primitive(self, addr: int, t: str) -> Optional[float]:
        """Low-level read wrapper."""
        try:
            if t == "float":
                return self.pm.read_float(addr)
            else:  # double
                return struct.unpack("d", self.pm.read_bytes(addr, 8))[0]
        except:
            return None

    def is_active(self) -> bool:
        """Check if reader is connected to process."""
        return self.pm is not None

    def read_snapshot(self) -> Optional[Dict[str, Optional[float]]]:
        """
        Reads all variables using the open connection.
        This is the hot path - keep it fast.
        """
        if not self.pm:
            if not self.attach():
                return None

        # If we lost the pointer (e.g. main menu reload), try to find it again
        if not self.main_base_ptr:
            self._refresh_pointers()
            if not self.main_base_ptr:
                return None

        results = {}
        
        try:
            # 1. Main variables
            for name, offset, type_ in VARIABLES:
                val = self.read_primitive(self.main_base_ptr + offset, type_)
                results[name] = val

            # 2. Market prices (these live at a different pointer)
            if self.market_base_ptr:
                try:
                    for name, offset, type_ in MARKET_PRICES:
                        val = self.read_primitive(self.market_base_ptr + offset, type_)
                        results[name] = val
                except:
                    pass  # Market prices are optional/less critical

            # Sanity check: if Treasury is None, the read likely failed entirely
            if results.get("Treasury") is None:
                return None
                
            return results

        except Exception as e:
            logging.debug(f"Read error: {e}")
            # Something broke (process closed?), kill the handle so we reconnect next time
            self.pm = None
            return None

    def close(self):
        """Explicitly close the connection if needed."""
        if self.pm:
            try:
                self.pm.close_process()
            except:
                pass
            self.pm = None


# Legacy wrapper for compatibility
def read_all_variables(process_name: str = PROCESS_NAME, game_version: str = "SRU") -> Optional[Dict[str, float]]:
    """
    Legacy API - creates a one-time reader.
    For better performance, use MemoryReader class directly and keep it alive.
    """
    reader = MemoryReader(process_name)
    return reader.read_snapshot()
