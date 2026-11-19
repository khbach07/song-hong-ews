"""W3 – wide -> long và tạo target. Xuất outputs/panel_target.csv."""
import pandas as pd
from . import config as C


def wide_to_long(perf: pd.DataFrame) -> pd.DataFrame:
    """TODO: mỗi khoản vay nhiều dòng theo (app_id, mob); thêm snap_date = config.snap_date(open_month, mob)."""
    raise NotImplementedError


def make_targets(long_df: pd.DataFrame) -> pd.DataFrame:
    """TODO: Target_30_3M / Target_90_3M từ DPD tháng t+1..t+3; chỉ gán nhãn khi đủ 3 tháng quan sát.
    Xử lý riêng: tất toán, quan sát đã chạm ngưỡng tại t (risk-at-entry), cắt cụt. Không tự gán Good.
    Giữ Indeterminate, loại Excluded, phạm vi MOB 3-21."""
    raise NotImplementedError


def main():
    # TODO: đọc config.PERF -> wide_to_long -> make_targets -> lưu config.PANEL_TARGET (cột config.PANEL_COLS)
    raise NotImplementedError


if __name__ == "__main__":
    main()
