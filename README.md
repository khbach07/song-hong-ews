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

## Pipeline, Excel và dashboard offline

1. Giải nén ZIP. Mở thư mục `song-hong-ews` trong VS Code.
2. Xem ngay `outputs/dashboard.html` bằng trình duyệt hoặc `outputs/EWS_Excel.xlsx` bằng Excel. Mở `docs/RESULTS.md` để đọc kết quả kiểm định.
3. Để huấn luyện lại từ ba CSV đã có sẵn trong `data/raw`, dùng Python 3.12 khuyến nghị.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run_ews.py --out outputs/rebuilt
.\.venv\Scripts\python.exe -m pytest -q
```

Trên macOS/Linux, dùng `.venv/bin/python` thay cho `.\.venv\Scripts\python.exe`. Pipeline có thể cần khoảng vài phút tùy máy. `--out` giúp giữ nguyên kết quả bàn giao. Dùng `--raw` để chỉ định thư mục chứa ba CSV có đúng tên nguồn.

### Chấm lại một tháng với mô hình đã đóng băng

```powershell
.\.venv\Scripts\python.exe score_ews.py --month 2024-09 --out outputs/sep_2024
```

Thêm `--model-dir outputs/rebuilt` nếu muốn dùng artifact vừa huấn luyện. Mở `outputs/sep_2024/dashboard.html` hoặc `scored.csv`. File joblib dùng phiên bản scikit-learn ghi trong requirements. Chỉ tải artifact do nhóm tự tạo hoặc nhận từ nguồn tin cậy.

### Làm mới workbook

Excel kèm theo là bản báo cáo của lượt bàn giao. Pipeline Python tái tạo toàn bộ dữ liệu báo cáo và dashboard HTML. Nếu có môi trường Node cung cấp `@oai/artifact-tool`, tạo workbook mới như sau.

```powershell
.\.venv\Scripts\python.exe tools/prepare_workbook.py --snapshot-dir outputs/sep_2024 --model-dir outputs --output outputs/sep_2024/workbook_input.json
node tools/build_workbook.mjs outputs/sep_2024/workbook_input.json outputs/sep_2024
```

Bảng Excel `05_EWS_Alerts` hiển thị tối đa 80 khoản mỗi cấp, có công thức phân loại lại khi sửa ngưỡng trong `04_Model_Scoring`. KPI toàn danh mục và hành động gốc dùng ngưỡng Python của lượt chạy. HTML và CSV có toàn bộ khoản vay của tháng.

## Bản đồ học theo sáu phần

| Phần | Đọc và thực hành | Đầu ra cần đối chiếu |
|---|---|---|
| W1 · [Nguồn và phạm vi](docs/components/W1_DATA_INTEGRATION.md) | `data_check.py`, kiểm tra ba nguồn theo `app_id` | `source_inventory.csv`, mục `scope` trong `run_summary.json` |
| W2 · [Chất lượng](docs/components/W2_DATA_QUALITY.md) | `clean_rules.py`, đọc thêm hướng dẫn W2 gốc | `missing_profile.csv`, `outliers_profile.csv`, `income_drift.csv` |
| W3 · [Outcome](docs/components/W3_TARGET_LABELING.md) | `build_panel.py`, tự dựng khoản vay sáu tháng rồi sửa một DPD tương lai | `panel_target.csv.gz` |
| W4 · [Chỉ báo](docs/components/W4_FEATURE_ENGINEERING.md) | `features.py`, kiểm tra cửa sổ 3 và 6 tháng | `features.csv.gz` |
| W5 · [Mô hình](docs/components/W5_MODEL_VALIDATION.md) | `train_model.py`, so sánh baseline DPD với LR, DT, RF và Gradient Boosting | `comparison_*.csv`, `model_*.joblib`, `oot_predictions_*.csv.gz`, `coef.csv` của benchmark Logistic |
| W6 · [Cảnh báo](docs/components/W6_ALERT_OPERATIONS.md) | `thresholds.py`, `report.py`, tra một khoản Red rồi kiểm tra PD và hành động | `thresholds.csv`, `scored.csv`, `dashboard.html`, `EWS_Excel.xlsx` |

`run_ews.py` gọi `src/ews/pipeline.py` để ghép tất cả các phần bằng khóa `(app_id, mob, snap_date)`. `data/raw` chứa nguồn. `outputs` chứa kết quả chạy thật. Đọc `docs/METHODOLOGY.md` để hiểu quy tắc và `docs/RESULTS.md` để diễn giải số liệu. `docs/EWS_Excel_Template.xlsx` là workbook khung ban đầu của nhóm.

## Demo trước lớp

Mở dashboard và chọn Red. Tra một mã khoản vay, đọc DPD, PD và hành động. Đối chiếu với một khoản thuộc Existing 30+. Sau đó mở kiểm định theo tháng, so AP 30+ với baseline DPD và nêu khoảng cách giữa PD bình quân với tỷ lệ thực tế. Bước cuối mở một dòng trong `panel_target.csv.gz` và lần lại 3 DPD tương lai trong CSV nguồn.

Đối chiếu các kết quả đã xuất bằng `python tools/verify_outputs.py`. Lệnh kiểm tra tổng số snapshot, cấp cảnh báo, chỉ số OOT và đối chiếu Excel nếu có trong thư mục kết quả.
