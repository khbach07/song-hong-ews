"""W6 – Ngưỡng PD -> Green/Yellow/Orange/Red và reason codes. Xuất outputs/thresholds.csv."""
import pandas as pd
from . import config as C

LEVELS = ["Green", "Yellow", "Orange", "Red"]


def choose_thresholds(scored: pd.DataFrame) -> pd.DataFrame:
    """TODO: chọn ngưỡng dựa trên PD thật của W5 + năng lực xử lý cảnh báo. Cột: level, pd_lower, pd_upper, action."""
    raise NotImplementedError


def assign_level(pd_series: pd.Series, thr: pd.DataFrame) -> pd.Series:
    """TODO: gán cấp theo pd_lower <= PD < pd_upper."""
    raise NotImplementedError


def reason_codes(features: pd.DataFrame) -> pd.DataFrame:
    """TODO: quy tắc lý do cảnh báo (khớp sheet thresholds mục B)."""
    raise NotImplementedError
