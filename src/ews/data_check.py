"""W1 – Kiểm tra cấu trúc và khả năng ghép các file dữ liệu."""
import pandas as pd
from . import config as C


def describe_files() -> pd.DataFrame:
    """TODO: số dòng, số cột, cột khóa, cột thời gian của từng file."""
    raise NotImplementedError


def check_joins() -> dict:
    """TODO: giao nhau app_id giữa perf / dev / oot; liệt kê trường hợp thiếu."""
    raise NotImplementedError


def build_raw_snapshot(snap: str) -> pd.DataFrame:
    """TODO: ghép perf + hồ sơ (dev/oot) cho tháng đánh giá `snap` (yyyy-mm) -> dữ liệu dán vào sheet 01_Raw_Data."""
    raise NotImplementedError


if __name__ == "__main__":
    print(describe_files())
