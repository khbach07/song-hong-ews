"""W2 – Quy tắc làm sạch dữ liệu hồ sơ & loại biến chống leakage.

Các thành viên khác (W4, W5) chỉ cần gọi:
    from ews import clean_rules as cr
    prof  = cr.load_clean_profile()        # hồ sơ đã làm sạch + cờ chất lượng
    X     = cr.model_ready(prof)           # bỏ biến leakage, sẵn sàng ghép với features

Mọi ngưỡng nằm trong THRESH ở đầu file: muốn đổi quy tắc chỉ sửa ở đây (và báo nhóm).
"""
import numpy as np
import pandas as pd
from . import config as C

# --------------------------------------------------------------------------- ngưỡng & quy tắc
THRESH = dict(
    AGE_MIN=18, AGE_MAX=75,          # tuổi ngoài khoảng này = lỗi nhập liệu (data_dictionary)
    INCOME_MAX=500,                  # thu nhập > 500 (triệu) = lỗi đơn vị (data_dictionary)
    INCOME_UNIT_DIV=100,             # cách sửa: chia 100 (xem docs/W2_HUONG_DAN.md, mục 3.2)
    DTI_MAX=200,                     # DTI > 200% = cực đoan -> chặn trên (cap) ở 200
    CARD_UTIL_MAX=100,               # > 100% = vượt hạn mức, có thể có thật -> chỉ gắn cờ, giữ giá trị
    DRIFT_BREAK="2023-07-01",        # biểu mẫu LOS mới -> thu nhập khai báo tăng ~25%
    DRIFT_FACTOR=1.25,               # dùng nếu chọn hiệu chỉnh drift (mặc định KHÔNG hiệu chỉnh)
)

NUM_COLS = ["loan_amount_mil", "age", "income_mil", "work_months", "dti_pct", "cic_hist_months", "num_lenders",
            "card_util_pct", "inq_6m", "dpd_cnt_6m", "dpd_cnt_12m", "deposit_avg_3m_mil"]
CAT_COLS = ["channel", "customer_type", "province", "region", "occupation", "home_status"]
# Cột chỉ để PHÂN TÍCH chất lượng dữ liệu (ví dụ bad rate của nhóm thiếu), KHÔNG làm input mô hình
ANALYSIS_ONLY = ["perf_class", "target"]
FLAGS = ["f_age_invalid", "f_income_missing", "f_income_outlier", "f_dti_outlier", "f_card_missing",
         "f_card_over100", "f_deposit_missing", "f_work_missing"]


# --------------------------------------------------------------------------- đọc dữ liệu
def load_profile() -> pd.DataFrame:
    """Hồ sơ của các khoản vay có lịch sử trả nợ (có trong perf_monthly): dev_2023 (Approved) + oot_2024H1.
    Mỗi dòng 1 khoản vay (app_id duy nhất). Thêm profile_source, app_ym (yyyymm số nguyên)."""
    perf_ids = pd.read_csv(C.PERF, usecols=["app_id"]).app_id
    dev = pd.read_csv(C.DEV)
    dev = dev[dev.app_id.isin(perf_ids)].copy(); dev["profile_source"] = "dev_2023"
    oot = pd.read_csv(C.OOT); oot["profile_source"] = "oot_2024H1"
    keep = ["app_id", "profile_source", "app_date"] + CAT_COLS + NUM_COLS + ANALYSIS_ONLY + C.LEAKAGE_COLS
    keep = list(dict.fromkeys(keep))
    df = pd.concat([dev.reindex(columns=keep), oot.reindex(columns=keep)], ignore_index=True)
    df["app_date"] = pd.to_datetime(df["app_date"])
    df["app_ym"] = df.app_date.dt.year * 100 + df.app_date.dt.month
    return df


# --------------------------------------------------------------------------- báo cáo chất lượng
def missing_report(df: pd.DataFrame, cols=None) -> pd.DataFrame:
    """Số lượng & tỷ lệ thiếu từng cột (-> DQ_Report mục A)."""
    cols = cols or (NUM_COLS + CAT_COLS)
    r = pd.DataFrame({"n_total": len(df), "n_missing": df[cols].isna().sum()})
    r["pct_missing"] = r.n_missing / r.n_total
    return r.reset_index(names="variable")


def outlier_report(df: pd.DataFrame) -> pd.DataFrame:
    """Đếm vi phạm từng quy tắc bất thường (-> DQ_Report mục B). Đếm trên dữ liệu GỐC."""
    t, ok = THRESH, df.age.between(THRESH["AGE_MIN"], THRESH["AGE_MAX"])
    rules = [
        ("R01a", "age", f"age < {t['AGE_MIN']}", (df.age < t["AGE_MIN"])),
        ("R01b", "age", f"age > {t['AGE_MAX']}", (df.age > t["AGE_MAX"])),
        ("R02", "income_mil", f"income_mil > {t['INCOME_MAX']}", (df.income_mil > t["INCOME_MAX"])),
        ("R03", "dti_pct", f"dti_pct > {t['DTI_MAX']}", (df.dti_pct > t["DTI_MAX"])),
        ("R04", "card_util_pct", f"card_util_pct > {t['CARD_UTIL_MAX']}", (df.card_util_pct > t["CARD_UTIL_MAX"])),
        ("R05", "work_months", "work_months > (age-18)*12", ok & (df.work_months > (df.age - 18) * 12)),
        ("R06", "cic_hist_months", "cic_hist_months > (age-18)*12", ok & (df.cic_hist_months > (df.age - 18) * 12)),
        ("R07", "dpd_cnt_6m", "dpd_cnt_6m > dpd_cnt_12m", (df.dpd_cnt_6m > df.dpd_cnt_12m)),
        ("R08", "dpd_cnt_12m", "dpd_cnt_12m > cic_hist_months", (df.dpd_cnt_12m > df.cic_hist_months)),
    ]
    return pd.DataFrame([(a, b, c, int(m.sum()), m.sum() / len(df)) for a, b, c, m in rules],
                        columns=["rule_id", "variable", "condition", "n_violations", "pct"])


def drift_report(df: pd.DataFrame) -> pd.DataFrame:
    """Số hồ sơ, tỷ lệ thiếu & trung vị thu nhập theo tháng nộp hồ sơ (-> DQ_Report mục C).
    Dùng income_mil đã sửa lỗi đơn vị để trung vị không bị kéo bởi lỗi."""
    inc = _fix_income(df.income_mil)
    g = df.assign(_inc=inc).groupby("app_ym")
    return pd.DataFrame({"n": g.size(), "pct_missing_income": g.income_mil.apply(lambda s: s.isna().mean()),
                         "median_income": g._inc.median()}).reset_index()


def missing_vs_badrate(df: pd.DataFrame, cols=("income_mil", "work_months", "card_util_pct", "deposit_avg_3m_mil")):
    """Bad rate (target gốc 90+/12 tháng) của nhóm thiếu so với nhóm có dữ liệu, trên mẫu Good+Bad.
    CHỈ ĐỂ PHÂN TÍCH: xem thiếu có mang thông tin rủi ro không (quy ước: > 1,5 × bad rate danh mục)."""
    gb = df[df.target.notna()]   # Good + Bad
    base = gb.target.mean(); rows = []
    for c in cols:
        m = gb[c].isna()
        rows.append((c, int(m.sum()), gb.target[m].mean(), gb.target[~m].mean(), base))
    r = pd.DataFrame(rows, columns=["variable", "n_missing", "bad_rate_missing", "bad_rate_present", "bad_rate_portfolio"])
    r["comment"] = np.where(r.bad_rate_missing > 1.5 * base, "Thiếu rủi ro hơn hẳn: giữ thành nhóm riêng",
                    np.where(r.bad_rate_missing < base / 1.5, "Thiếu an toàn hơn: giữ thành nhóm riêng",
                             "Gần mức trung bình: giữ nhóm riêng (có ý nghĩa nghiệp vụ)"))
    return r


# --------------------------------------------------------------------------- làm sạch
def _fix_income(s: pd.Series) -> pd.Series:
    t = THRESH
    return s.where(~(s > t["INCOME_MAX"]), s / t["INCOME_UNIT_DIV"])


def clean_profile(df: pd.DataFrame, fix_income_unit=True, cap_dti=True, adjust_income_drift=False) -> pd.DataFrame:
    """Áp quy tắc xử lý đã chốt. Giữ bản gốc ở cột *_raw; thêm cờ f_* (1 = có vấn đề).

    - Thiếu: GIỮ NaN + cờ (không tự thay bằng 0). Thiếu có ý nghĩa nghiệp vụ (không có thẻ, không có TK tiền gửi...).
    - age ngoài [18, 75]: đặt NaN + cờ f_age_invalid.
    - income > 500: lỗi đơn vị -> chia 100 (fix_income_unit) + cờ f_income_outlier.
    - dti > 200: chặn trên ở 200 (cap_dti) + cờ f_dti_outlier.
    - card_util > 100: giữ nguyên (vượt hạn mức có thể có thật) + cờ f_card_over100.
    - adjust_income_drift: nhân thu nhập trước 07/2023 với 1.25 cho cùng mặt bằng (mặc định tắt – cần nhóm đồng ý).
    """
    t, d = THRESH, df.copy()
    for c in ("age", "income_mil", "dti_pct"):
        d[c + "_raw"] = d[c]
    d["f_age_invalid"] = (~d.age.between(t["AGE_MIN"], t["AGE_MAX"]) & d.age.notna()).astype(int)
    d["f_income_missing"] = d.income_mil.isna().astype(int)
    d["f_income_outlier"] = (d.income_mil > t["INCOME_MAX"]).astype(int)
    d["f_dti_outlier"] = (d.dti_pct > t["DTI_MAX"]).astype(int)
    d["f_card_missing"] = d.card_util_pct.isna().astype(int)
    d["f_card_over100"] = (d.card_util_pct > t["CARD_UTIL_MAX"]).astype(int)
    d["f_deposit_missing"] = d.deposit_avg_3m_mil.isna().astype(int)
    d["f_work_missing"] = d.work_months.isna().astype(int)
    d.loc[d.f_age_invalid == 1, "age"] = np.nan
    if fix_income_unit:
        d["income_mil"] = _fix_income(d.income_mil)
    if cap_dti:
        d["dti_pct"] = d.dti_pct.clip(upper=t["DTI_MAX"])
    d["income_period"] = np.where(d.app_date >= pd.Timestamp(t["DRIFT_BREAK"]), "post_0723", "pre_0723")
    if adjust_income_drift:
        d.loc[d.income_period == "pre_0723", "income_mil"] *= t["DRIFT_FACTOR"]
    d["dq_flag_count"] = d[FLAGS].sum(axis=1)
    return d


def load_clean_profile(**kw) -> pd.DataFrame:
    return clean_profile(load_profile(), **kw)


# --------------------------------------------------------------------------- chống leakage
def drop_leakage(df: pd.DataFrame) -> pd.DataFrame:
    """Bỏ các cột trong config.LEAKAGE_COLS + cột chỉ để phân tích (perf_class, target)."""
    drop = [c for c in C.LEAKAGE_COLS + ANALYSIS_ONLY if c in df.columns]
    return df.drop(columns=drop)


def model_ready(df: pd.DataFrame) -> pd.DataFrame:
    """Bảng hồ sơ sẵn sàng ghép với features: bỏ leakage, bỏ cột *_raw, giữ khóa app_id + cờ chất lượng."""
    d = drop_leakage(df)
    return d.drop(columns=[c for c in d.columns if c.endswith("_raw")])


# --------------------------------------------------------------------------- xử lý thiếu khi huấn luyện (tùy chọn)
def fit_medians(train: pd.DataFrame) -> dict:
    """Trung vị tính CHỈ trên tập Dev (train) để không rò rỉ thông tin từ OOT."""
    return {c: float(train[c].median()) for c in NUM_COLS if c in train.columns}


def impute_median(df: pd.DataFrame, medians: dict) -> pd.DataFrame:
    """Điền trung vị (đã fit trên Dev). Các cờ f_*_missing giữ lại thông tin 'thiếu' cho mô hình."""
    d = df.copy()
    for c, m in medians.items():
        if c in d.columns:
            d[c] = d[c].fillna(m)
    return d
