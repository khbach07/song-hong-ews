import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ews import config as C

def test_snap_date():
    assert str(C.snap_date("2023-04", 3).date()) == "2023-07-01"

def test_leakage_list():
    assert "perf_class" in C.LEAKAGE_COLS and "gender" in C.LEAKAGE_COLS
