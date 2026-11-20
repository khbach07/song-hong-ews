# W1 · Tích hợp dữ liệu và phạm vi

**Phụ trách theo phân công gốc** Thiên An. Module `src/ews/data_check.py`. Tương ứng workbook `00_Instructions`, `01_Raw_Data` và bàn giao workbook.

| Nguồn | Grain | Vai trò |
|---|---|---|
| `song_hong_perf_monthly.csv` | Một dòng mỗi `app_id` | Tháng mở, MOB quan sát, MOB tất toán/cơ cấu, DPD từ 01–24 |
| `song_hong_dev_2023.csv` | Một hồ sơ mỗi `app_id` | Nhận diện cohort Dev và hồ sơ lúc xin vay |
| `song_hong_oot_2024H1.csv` | Một hồ sơ mỗi `app_id` | Nhận diện cohort OOT và hồ sơ lúc xin vay |

`read_source` kiểm tra schema và khóa. `load_data` chuẩn hóa thời gian, kiểm tra DPD nguyên không âm và khoảng MOB, phát hiện trùng giữa hai cohort và ghép one-to-one. Sau left join từ performance, hệ thống chọn Approved có hồ sơ, áp loại trừ nhân viên/gian lận và trạng thái OOT Excluded theo quy tắc dự án. Indeterminate vẫn đi qua W3 để xét đủ dữ kiện ở từng tháng.

**Bàn giao cho W2 và W3.** Hai bảng đã đồng phạm vi, 58.071 khoản trong dữ liệu bàn giao. `source_inventory.csv` đếm ở cấp nguồn, `run_summary.json → scope` ghi độ phủ và loại trừ. `input_sha256` nhận diện ba file tại lần huấn luyện. Mục Chất lượng dữ liệu trên web đọc thông tin từ model-dir.

**Đối chiếu.** Từ 59.000 dòng performance, xác nhận 129 mã thiếu hồ sơ và 800 trường hợp loại trừ trên bộ hiện tại. Số hồ sơ Dev không ghép được không đại diện cho số khoản vay bị bỏ khỏi danh mục, vì điểm xuất phát khi chấm là performance. Khi đổi nguồn, xác nhận tháng mở là MOB 0 và kiểm tra tỷ lệ ngày nộp hồ sơ lệch tháng mở trước khi ghép thời gian.

**Điều kiện nghiệm thu.** Khóa duy nhất ở từng nguồn, Dev và OOT rời nhau, có thể lần lại từng khoản được chấm về cả bảng hồ sơ lẫn performance.
