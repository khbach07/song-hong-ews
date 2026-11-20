# W2 · Chất lượng dữ liệu và quy tắc làm sạch

**Phụ trách theo phân công gốc** Lệ Xuân. Module `src/ews/clean_rules.py`. Workbook `02_Customer_Profile`.

| Hạng mục | Chính sách mặc định | Bằng chứng |
|---|---|---|
| Thiếu dữ liệu | Giữ NA và tạo cờ cho card utilization, tiền gửi và các trường cần giám sát | `missing_profile.csv` |
| Tuổi | Kẹp 18–75, ghi cờ và giữ giá trị gốc để đối chiếu | `outliers_profile.csv` |
| Thu nhập trên 500 triệu | Áp giả định lỗi đơn vị trong bài tập, chia 100 và lưu cờ | Báo cáo ngoại lai và bảng drift |
| DTI trên 200%, card utilization trên 100% | Gắn cờ, giữ số gốc theo mặc định | Báo cáo ngoại lai |
| Mâu thuẫn chéo | Báo cáo quan hệ tháng làm việc/tuổi, CIC/tuổi và tần suất DPD | R05–R08 |
| Drift thu nhập | Trung vị sau sửa đơn vị và tỷ lệ thiếu theo tháng hồ sơ | `income_drift.csv` |

Ví dụ DTI 230 đi tiếp ở giá trị 230 kèm cờ ngoại lai. Khi hợp đồng dữ liệu thay đổi, xác nhận lại đơn vị với bên cung cấp trước khi áp quy tắc sửa thu nhập. Thu nhập và tuổi phục vụ kiểm soát DQ trong phiên bản này. Bảng drift mang tính mô tả, mức thay đổi trung vị còn phụ thuộc vào cơ cấu hồ sơ và tỷ lệ thiếu.

**Bàn giao cho W4/W5.** W4 dùng allowlist `PROFILE` trong `features.py`. Các biến nhãn vintage, quyết định và biến nhạy cảm nằm ngoài allowlist. Logistic, cây và Random Forest có bước điền trung vị học từ Train trong pipeline mô hình. Gradient Boosting xử lý NA trực tiếp.

**Điều kiện nghiệm thu.** Đối chiếu số thiếu với mẫu số đầu vào, rà hồ sơ trước/sau sửa một quy tắc, xác nhận cờ thiếu được tính trước khi điền dữ liệu. Mở Chất lượng dữ liệu để kiểm demo nguồn, missing và drift.
