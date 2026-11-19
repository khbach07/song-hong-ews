"""W5 – Ghép dữ liệu, chia Dev/OOT theo thời gian, train LR/DT/RF, xuất coef.csv."""
import pandas as pd
from . import config as C


def load_model_table() -> pd.DataFrame:
    """TODO: ghép PANEL_TARGET + FEATURES theo config.KEY; áp clean_rules; bỏ LEAKAGE_COLS."""
    raise NotImplementedError


def split_dev_oot(df: pd.DataFrame):
    """TODO: chia theo thời gian (Dev để phát triển, OOT để kiểm định)."""
    raise NotImplementedError


def compare_models(dev, oot) -> pd.DataFrame:
    """TODO: LR, DT, RF; báo cáo AUC/KS... trên Dev và OOT."""
    raise NotImplementedError


def export_coef(model, features: list):
    """TODO: lưu config.COEF với cột feature, coef, mean, scale (+ dòng intercept) – khớp sheet coef."""
    raise NotImplementedError


if __name__ == "__main__":
    pass
