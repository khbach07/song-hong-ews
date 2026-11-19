"""W4 – Chỉ báo rủi ro tại tháng t. Chỉ dùng DPD <= t. Xuất outputs/features.csv."""
import pandas as pd
from . import config as C


def dpd_features(long_df: pd.DataFrame) -> pd.DataFrame:
    """TODO: dpd_t, dpd_avg_3m, dpd_max_3m, dpd_trend_3m, n_months_dpd_6m, months_since_last_dpd, restr_flag_t, ...
    Tên và công thức theo sheet Feature_Dict. Không dùng DPD sau t."""
    raise NotImplementedError


def main():
    # TODO: tạo features cho mọi (app_id, mob) -> lưu config.FEATURES
    raise NotImplementedError


if __name__ == "__main__":
    main()
