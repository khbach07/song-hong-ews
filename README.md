# Sông Hồng · Behavioral Early Warning System

Đồ án quản trị rủi ro tín dụng. Mỗi tháng, hệ thống xếp hạng các khoản vay hiện hữu theo xác suất có ít nhất một snapshot **DPD ≥ 30** trong ba tháng kế tiếp. Mục tiêu 90+ được huấn luyện và kiểm định riêng. DPD là số ngày quá hạn. MOB là số tháng trên sổ.

## Web demo chạy trên máy cá nhân

Dùng web để đổi tháng đánh giá, lọc khoản vay, xem PD và hành động, tải CSV và trình bày kết quả kiểm định. Web ước lượng rủi ro từ snapshot lịch sử bằng mô hình 30+ đã lưu.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe serve_ews.py
```

Chờ server khởi động rồi mở [Sông Hồng EWS](http://127.0.0.1:8765). Xem [hướng dẫn vận hành và API](docs/WEB_RUNBOOK.md). Trên macOS/Linux, thay đường dẫn Python bằng `.venv/bin/python`.

## Huấn luyện lại và xuất báo cáo

Giải nén ZIP, mở thư mục `song-hong-ews` trong VS Code và cài môi trường như trên. Dùng Python 3.12. Bộ bàn giao có sẵn ba CSV ở `data/raw` và báo cáo kiểm tra được ở `outputs`. Có thể mở `outputs/dashboard.html` hoặc `outputs/EWS_Excel.xlsx` trước khi chạy server.

```powershell
.\.venv\Scripts\python.exe run_ews.py --out outputs/rebuilt
.\.venv\Scripts\python.exe tools/verify_outputs.py --out outputs/rebuilt
.\.venv\Scripts\python.exe -m pytest -q
```

Chọn một đường dẫn `--out` chưa tồn tại cho mỗi lần chạy. `--raw` nhận thư mục chứa đủ ba CSV. `--month YYYY-MM` chọn tháng xuất báo cáo khi huấn luyện. Dùng `--model-dir outputs/rebuilt` ở web để xem bộ kết quả mới.

### Chấm lại một tháng bằng mô hình đã huấn luyện

```powershell
.\.venv\Scripts\python.exe score_ews.py --month 2024-09 --out outputs/sep_2024
.\.venv\Scripts\python.exe tools/verify_outputs.py --out outputs/sep_2024
```

CSV, HTML và Excel được dựng trong cùng lệnh. Excel gồm KPI toàn danh mục, tối đa 80 khoản mỗi cấp để học và đối chiếu, DPD đã che sau MOB hiện tại, ngưỡng, báo cáo chất lượng, bảng nhãn và kiểm định. CSV và HTML chứa toàn bộ snapshot tháng. Dùng ngưỡng đầy đủ trong `thresholds.csv` để đối chiếu cấp cảnh báo.

Web và CLI kiểm tra manifest của bộ mô hình và SHA-256 các nguồn trước khi chấm. Khi CSV thay đổi, huấn luyện một lượt mới và trỏ web/CLI vào thư mục mới. Artifact joblib cần cùng phiên bản scikit-learn và đến từ nguồn nhóm tin cậy.

## Bản đồ học theo sáu phần

| Phần | Đọc và thực hành | Đầu ra cần đối chiếu |
|---|---|---|
| W1 · [Nguồn và phạm vi](docs/components/W1_DATA_INTEGRATION.md) | `data_check.py`, kiểm tra ba nguồn theo `app_id` | `source_inventory.csv`, mục `scope` trong `run_summary.json` |
| W2 · [Chất lượng](docs/components/W2_DATA_QUALITY.md) | `clean_rules.py`, đọc thêm hướng dẫn W2 gốc | `missing_profile.csv`, `outliers_profile.csv`, `income_drift.csv` |
| W3 · [Outcome](docs/components/W3_TARGET_LABELING.md) | `build_panel.py`, tự dựng khoản vay sáu tháng rồi sửa một DPD tương lai | `panel_target.csv.gz` |
| W4 · [Chỉ báo](docs/components/W4_FEATURE_ENGINEERING.md) | `features.py`, kiểm tra cửa sổ 3 và 6 tháng | `features.csv.gz` |
| W5 · [Mô hình](docs/components/W5_MODEL_VALIDATION.md) | `train_model.py`, so sánh baseline DPD với LR, DT, RF và Gradient Boosting | `comparison_*.csv`, `model_*.joblib`, `oot_predictions_*.csv.gz`, `coef.csv` của benchmark Logistic |
| W6 · [Cảnh báo](docs/components/W6_ALERT_OPERATIONS.md) | `thresholds.py`, `report.py`, tra một khoản Red rồi kiểm tra PD và hành động | `thresholds.csv`, `scored.csv`, `dashboard.html`, `EWS_Excel.xlsx` |

`run_ews.py` gọi `src/ews/pipeline.py` để ghép tất cả các phần bằng khóa `(app_id, mob, snap_date)`. `data/raw` chứa nguồn. `outputs` chứa kết quả chạy thật. Xem [kiến trúc và hướng dẫn demo](docs/ARCHITECTURE_AND_DEMO.md). Đọc `docs/METHODOLOGY.md` để hiểu quy tắc và `docs/RESULTS.md` để diễn giải số liệu. `docs/EWS_Excel_Template.xlsx` là workbook khung ban đầu của nhóm.

## Demo trước lớp

Mở dashboard và chọn Red. Tra một mã khoản vay, đọc DPD, PD và hành động. Đối chiếu với một khoản thuộc Existing 30+. Sau đó mở kiểm định theo tháng, so AP 30+ với baseline DPD và nêu khoảng cách giữa PD bình quân với tỷ lệ thực tế. Bước cuối mở một dòng trong `panel_target.csv.gz` và lần lại 3 DPD tương lai trong CSV nguồn.

Đối chiếu các kết quả đã xuất bằng `python tools/verify_outputs.py`. Lệnh kiểm tra tổng số snapshot, cấp cảnh báo, chỉ số OOT và đối chiếu các báo cáo đã xuất.
