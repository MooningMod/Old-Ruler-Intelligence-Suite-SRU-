import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

# ======================================================
# CONFIGURAZIONE
# ======================================================
BASE_DIR = Path.home() / "Documents" / "SRU_Logger"
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Lista completa e standardizzata di tutte le colonne possibili
# UPDATED: Added Social Spending columns
ALL_POSSIBLE_COLUMNS = [
    "GameName", "Nation", "GameDate", "Population", "Domestic Approval", "Military Approval", "Literacy", 
    "World Market Opinion", "Credit Rating", "Treaty Integrity", "Subsidy Rate", "Tourism", "Treasury", "Bond Debt", 
    "GDP/c", "Inflation", "Unemployment", "Research Efficiency", "Active Personnel", "Reserve Personnel",
    "Emigration", "Immigration", "Births", "Deaths",
    # Social Spending (restored)
    "Health Care", "Education", "Infrastructure", "Environment",
    "Family Subsidy", "Law Enforcement", "Culture Subsidy", "Social Assistance",
    # Resources
    "Agriculture", "Rubber", "Timber", "Petroleum",
    "Coal", "Metal Ore", "Uranium", "Electric Power", "Consumer Goods", "Industry Goods", "Military Goods",
    "Agriculture Production Cost", "Rubber Production Cost", "Timber Production Cost", "Petroleum Production Cost",
    "Coal Production Cost", "Metal Ore Production Cost", "Uranium Production Cost", "Electric Power Production Cost",
    "Consumer Goods Production Cost", "Industry Goods Production Cost", "Military Goods Production Cost",
    "Agriculture Market Price", "Rubber Market Price", "Timber Market Price", "Petroleum Market Price",
    "Coal Market Price", "Metal Ore Market Price", "Uranium Market Price", "Electric Power Market Price",
    "Consumer Goods Market Price", "Industry Goods Market Price", "Military Goods Market Price",
    "Agriculture Trades", "Rubber Trades", "Timber Trades", "Petroleum Trades", "Coal Trades", "Metal Ore Trades",
    "Uranium Trades", "Electric Power Trades", "Consumer Goods Trades", "Industry Goods Trades", "Military Goods Trades",
]

# ======================================================
# FUNZIONI PRINCIPALI
# ======================================================

def _sanitize_filename(text: str) -> str:
    """Sanifica testo per nome file."""
    return "".join(c for c in text if c.isalnum() or c in (' ', '-', '_')).strip()


def get_log_file_path(game_name: str, nation: str, use_timestamp: bool = False) -> Path:
    """
    Genera percorso file di log.
    
    Args:
        game_name: Nome partita
        nation: Nome nazione
        use_timestamp: Se True aggiunge timestamp
    
    Returns:
        Path del file di log
    """
    safe_game = _sanitize_filename(game_name)
    safe_nation = _sanitize_filename(nation)
    
    # Se entrambi i campi sono vuoti, crea un nome di fallback con timestamp
    if not safe_game and not safe_nation:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return LOGS_DIR / f"SRU_Log_{timestamp}.csv"
    
    # Unisce le parti non vuote per formare il nome del file
    # Ordine: Nation_GameName per coerenza
    parts = [p for p in [safe_nation, safe_game] if p]
    base = "_".join(parts)
    
    if use_timestamp:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{base}_{timestamp}.csv"
    else:
        filename = f"{base}.csv"
    
    return LOGS_DIR / filename


def log_to_csv(file_path: Path, data_dict: dict, game_date: str) -> bool:
    """
    Scrive una riga di dati nel file CSV specificato.
    
    Args:
        file_path: Percorso del file CSV
        data_dict: Dizionario con i dati da scrivere
        game_date: Data di gioco nel formato YYYY-MM-DD
    
    Returns:
        True se scrittura riuscita, False altrimenti
    """
    if not data_dict:
        return False

    file_path = Path(file_path)
    file_exists = file_path.exists() and file_path.stat().st_size > 0

    # Prepara la riga di dati assicurando la coerenza con le colonne standard
    row_data = {key: data_dict.get(key) for key in ALL_POSSIBLE_COLUMNS}
    
    # Mappatura dei nomi interni ai nomi delle colonne
    row_data['GameName'] = data_dict.get('game_name', data_dict.get('GameName'))
    row_data['Nation'] = data_dict.get('nation', data_dict.get('Nation'))
    row_data["GameDate"] = game_date

    try:
        with open(file_path, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=ALL_POSSIBLE_COLUMNS, extrasaction='ignore')
            
            # Scrivi l'intestazione solo se il file è nuovo o vuoto
            if not file_exists:
                writer.writeheader()
                
            writer.writerow(row_data)
        return True
    except Exception as e:
        logging.error(f"Error writing to {file_path}: {e}")
        return False


def get_existing_logs() -> list:
    """
    Restituisce lista dei log esistenti con informazioni dettagliate.
    
    Returns:
        Lista di dizionari con info sui log
    """
    if not LOGS_DIR.exists():
        return []
    
    logs = []
    try:
        # Ordina i file per data di modifica, dal più recente al più vecchio
        csv_files = sorted(LOGS_DIR.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
        
        for file_path in csv_files:
            try:
                stats = file_path.stat()
                modified = datetime.fromtimestamp(stats.st_mtime)
                
                # Conta le righe (escludendo l'header)
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    line_count = max(0, sum(1 for _ in f) - 1)
                
                base_name = file_path.stem
                display = f"{base_name} | {line_count} entries" if line_count > 0 else base_name
                
                logs.append({
                    "name": base_name,
                    "display_name": display,
                    "filename": file_path.name,
                    "path": str(file_path),
                    "file_path": str(file_path),
                    "filepath": str(file_path),  # Per retrocompatibilità
                    "line_count": line_count,
                    "modified_date": modified.strftime("%Y-%m-%d %H:%M:%S"),
                    "file_size_kb": round(stats.st_size / 1024, 2)
                })
            except Exception as e:
                logging.error(f"Error reading {file_path}: {e}")
                continue
                
    except Exception as e:
        logging.error(f"Error listing logs: {e}")
    
    return logs


def get_last_date_from_log(file_path: Path) -> Optional[str]:
    """
    Legge l'ultima data registrata in un file di log.
    
    Args:
        file_path: Percorso del file di log
    
    Returns:
        Ultima data nel formato YYYY-MM-DD o None se non trovata
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            lines = [line.strip() for line in f if line.strip()]
        
        if len(lines) < 2:  # Deve avere almeno header + 1 riga dati
            return None
        
        header = lines[0].split(",")
        last_line = lines[-1].split(",")
        
        if "GameDate" not in header:
            return None
        
        date_idx = header.index("GameDate")
        if date_idx >= len(last_line):
            return None
        
        last_date = last_line[date_idx].strip()
        
        # Valida formato data
        try:
            datetime.strptime(last_date, "%Y-%m-%d")
            return last_date
        except ValueError:
            return None
            
    except Exception as e:
        logging.error(f"Error reading last date from {file_path}: {e}")
        return None


def create_backup(file_path: Path) -> bool:
    """
    Crea un backup del file di log con timestamp.
    
    Args:
        file_path: Percorso del file da backuppare
    
    Returns:
        True se backup creato con successo, False altrimenti
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return False
    
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{file_path.stem}_backup_{timestamp}{file_path.suffix}"
        backup_path = file_path.parent / backup_name
        
        import shutil
        shutil.copy2(file_path, backup_path)
        logging.info(f"Backup created: {backup_path}")
        return True
    except Exception as e:
        logging.error(f"Error creating backup: {e}")
        return False


def validate_log_file(file_path: Path) -> dict:
    """
    Valida l'integrità di un file di log.
    
    Args:
        file_path: Percorso del file da validare
    
    Returns:
        Dizionario con risultati della validazione
    """
    file_path = Path(file_path)
    result = {"valid": False, "errors": [], "warnings": [], "stats": {}}
    
    if not file_path.exists():
        result["errors"].append("File does not exist")
        return result
    
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
        
        if not lines:
            result["errors"].append("File is empty")
            return result
        
        # Valida header
        header = lines[0].strip().split(",")
        required_cols = ["GameDate", "GameName", "Nation"]
        missing = [col for col in required_cols if col not in header]
        
        if missing:
            result["errors"].append(f"Missing required columns: {', '.join(missing)}")
            return result
        
        result["stats"] = {
            "total_lines": len(lines),
            "data_rows": len(lines) - 1,
            "columns": len(header)
        }
        
        # Controlla date duplicate
        date_idx = header.index("GameDate")
        dates = []
        for i, line in enumerate(lines[1:], start=2):
            parts = line.strip().split(",")
            if len(parts) > date_idx:
                date = parts[date_idx]
                if date in dates:
                    result["warnings"].append(f"Line {i}: duplicate date {date}")
                dates.append(date)
        
        result["valid"] = True
        
    except Exception as e:
        result["errors"].append(f"Error reading file: {e}")
    
    return result


def cleanup_old_backups(max_backups: int = 5):
    """
    Rimuove i backup vecchi mantenendo solo gli ultimi N per ogni file.
    
    Args:
        max_backups: Numero massimo di backup da mantenere per file
    """
    try:
        from collections import defaultdict
        backup_files = list(LOGS_DIR.glob("*_backup_*.csv"))
        backups_by_base = defaultdict(list)
        
        # Raggruppa i backup per file base
        for backup in backup_files:
            base_name = backup.stem.split("_backup_")[0]
            backups_by_base[base_name].append(backup)
        
        # Per ogni gruppo, mantieni solo gli ultimi N
        for base_name, backups in backups_by_base.items():
            backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            for old_backup in backups[max_backups:]:
                try:
                    old_backup.unlink()
                    logging.info(f"Removed old backup: {old_backup.name}")
                except Exception as e:
                    logging.error(f"Error removing {old_backup}: {e}")
                    
    except Exception as e:
        logging.error(f"Error during cleanup: {e}")


def get_log_statistics() -> dict:
    """
    Restituisce statistiche aggregate su tutti i log.
    
    Returns:
        Dizionario con statistiche globali
    """
    logs = get_existing_logs()
    
    if not logs:
        return {
            "total_logs": 0,
            "total_entries": 0,
            "total_size_kb": 0
        }
    
    return {
        "total_logs": len(logs),
        "total_entries": sum(log["line_count"] for log in logs),
        "total_size_kb": round(sum(log["file_size_kb"] for log in logs), 2),
        "newest_log": logs[0]["display_name"],
        "oldest_log": logs[-1]["display_name"]
    }


def merge_logs(log_paths: list, output_path: Path, remove_duplicates: bool = True) -> bool:
    """
    Unisce più file di log in uno solo.
    
    Args:
        log_paths: Lista di percorsi dei log da unire
        output_path: Percorso del file di output
        remove_duplicates: Se True, rimuove entry duplicate basate su GameDate
    
    Returns:
        True se unione riuscita, False altrimenti
    """
    try:
        all_rows = []
        seen_dates = set()
        
        for log_path in log_paths:
            log_path = Path(log_path)
            if not log_path.exists():
                continue
                
            with open(log_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if remove_duplicates:
                        date = row.get("GameDate")
                        if date in seen_dates:
                            continue
                        seen_dates.add(date)
                    all_rows.append(row)
        
        # Ordina per data
        all_rows.sort(key=lambda x: x.get("GameDate", ""))
        
        # Scrivi il file unito
        output_path = Path(output_path)
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=ALL_POSSIBLE_COLUMNS, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(all_rows)
        
        logging.info(f"Merged {len(log_paths)} logs into {output_path}")
        return True
        
    except Exception as e:
        logging.error(f"Error merging logs: {e}")
        return False


def export_log_to_json(file_path: Path, output_path: Optional[Path] = None) -> bool:
    """
    Esporta un file di log in formato JSON.
    
    Args:
        file_path: Percorso del file CSV da esportare
        output_path: Percorso del file JSON di output (opzionale)
    
    Returns:
        True se esportazione riuscita, False altrimenti
    """
    try:
        import json
        
        file_path = Path(file_path)
        if not file_path.exists():
            return False
        
        if output_path is None:
            output_path = file_path.with_suffix('.json')
        else:
            output_path = Path(output_path)
        
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            data = list(reader)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Exported {file_path} to {output_path}")
        return True
        
    except Exception as e:
        logging.error(f"Error exporting to JSON: {e}")
        return False


# ======================================================
# TEST
# ======================================================

if __name__ == "__main__":
    print("SRU Data Logger - Testing")
    print("=" * 50)
    
    print("\n📁 Existing logs:")
    for log in get_existing_logs():
        print(f"  • {log['display_name']}")
        print(f"    Size: {log['file_size_kb']} KB | Modified: {log['modified_date']}")
    
    print("\n📊 Statistics:")
    stats = get_log_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n✅ Tests completed")
