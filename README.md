# Song Hong – Behavioral Early Warning System (EWS)

Dự báo khả năng khoản vay hiện hữu phát sinh quá hạn (DPD ≥ 30, so sánh với ≥ 90) trong 3 tháng tới và hiển thị cảnh báo Green/Yellow/Orange/Red trên Excel.

## Cấu trúc
| Đường dẫn | Nội dung | Phụ trách |
|---|---|---|
| `src/ews/config.py` | Quy ước chung: khóa, tên cột, đường dẫn, biến bị loại | Cả nhóm (đổi phải báo nhóm) |
| `src/ews/data_check.py` | Kiểm tra cấu trúc & ghép dữ liệu | W1 |
| `src/ews/clean_rules.py` | Quy tắc làm sạch, loại biến chống leakage (đã có code) | W2 |
| `src/ews/dq_report.py` | Xuất báo cáo Data Quality Excel + hồ sơ sạch | W2 |
| `docs/W2_HUONG_DAN.md` | Hướng dẫn chi tiết phần W2 | W2 |
| `src/ews/build_panel.py` | wide → long, tạo Target_30_3M / Target_90_3M | W3 |
| `src/ews/features.py` | Chỉ báo rủi ro tại tháng t | W4 |
| `src/ews/train_model.py` | Ghép dữ liệu, chia Dev/OOT, train LR/DT/RF, xuất coef | W5 |
| `src/ews/thresholds.py` | Ngưỡng PD, cấp cảnh báo, reason codes | W6 |
| `tools/make_dummy_data.py` | Sinh dữ liệu giả cùng cấu trúc để làm song song | Ai cũng dùng |
| `docs/EWS_Excel_Template.xlsx` | Workbook khung (sheet 00–07 + sheet phụ) | W1 ghép cuối |
| `docs/GIT_HUONG_DAN.md` | Hướng dẫn Git nhanh | |
| `outputs/` | 4 file trao đổi: panel_target, features, coef, thresholds | |

## Cài đặt
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export PYTHONPATH=src   # Windows PowerShell: $env:PYTHONPATH="src"
```
Giải nén các CSV vào `data/raw/` (bị `.gitignore`, **không đẩy dữ liệu lên GitHub**).

## Quy tắc làm việc
- Mỗi người chỉ sửa file của mình; sửa `config.py` hoặc tên cột file trao đổi phải báo cả nhóm.
- Làm trên nhánh riêng (`w2-clean-rules`, `w3-target`, …) rồi Pull Request vào `main`.
- Tên cột file trao đổi: xem sheet `Interface_Files` trong Excel khung (đang là ĐỀ XUẤT, cần chốt).
- Feature tại tháng t chỉ dùng DPD ≤ t; DPD tương lai chỉ dùng cho target/backtesting.
- Chưa có kết quả của bạn khác? Chạy `python tools/make_dummy_data.py` để có dữ liệu giả cùng cấu trúc.
