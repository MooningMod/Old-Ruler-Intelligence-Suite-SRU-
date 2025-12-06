import sys
import argparse
from PyQt5.QtWidgets import QApplication
from overlay_ins_menu import OverlayINS

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--default-unit", default=None, help="Path to DEFAULT.UNIT")
    parser.add_argument("--default-ttrx", default=None, help="Path to DEFAULT.TTRX")
    parser.add_argument("--range-database", default=None, help="Path to unit_rangestats_database.csv")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    # Pass three paths to overlay (spotting uses static map from spotting_map.py)
    overlay = OverlayINS(
        default_unit_path=args.default_unit,
        default_ttrx_path=args.default_ttrx,
        range_database_path=args.range_database
    )
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
