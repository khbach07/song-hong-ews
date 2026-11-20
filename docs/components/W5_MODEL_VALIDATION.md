# W5 · Mô hình, kiểm định và bằng chứng

**Phụ trách theo phân công gốc** Được. Module `src/ews/train_model.py`. Workbook `04_Model_Scoring` và đầu ra kiểm định.

1. Ghép W3–W4 theo khóa snapshot. Chọn nhãn quan sát đầy đủ. Tách riêng 30+ và 90+ vì hai mục tiêu có điều kiện đầu vào khác nhau.
2. Chia Dev theo tháng mở. Chỉ giữ Train có `label_end` trước lúc bắt đầu Validation, và Validation có nhãn trưởng thành trước OOT. OOT tách theo cohort nguồn. Cùng một khoản không đi qua nhiều tập.
3. So sánh DPD hiện tại, Logistic chỉ hành vi, Logistic có hồ sơ, Decision Tree, Random Forest và HistGradientBoosting. Xếp ứng viên theo AP Validation, dùng Brier khi AP hòa. DPD hiện tại là benchmark.
4. Giữ champion đã fit trên Train. Chấm Validation để xác lập ngưỡng W6 và đánh giá OOT riêng với artifact đã lưu.

| Chỉ số | Cách dùng khi bảo vệ |
|---|---|
| AP | Đọc sức xếp hạng khi dương hiếm. So cùng mục tiêu và cùng tập. |
| ROC-AUC | Đọc khả năng phân biệt dương/âm khi xét toàn thang điểm. |
| Brier | Trung bình bình phương sai số giữa xác suất và nhãn 0/1. |
| PD bình quân so với tỷ lệ quan sát | Kiểm tra chênh lệch ở cấp danh mục và theo tháng/nhóm điểm. |

**Bằng chứng.** OOT 30+ đạt AP 0,4352 so với 0,3417 của DPD hiện tại. PD bình quân 2,58% và tỷ lệ thực tế 1,29%, cho thấy lệch hiệu chỉnh trên mẫu này. Validation chỉ có 12/2023. Diễn giải kết quả cho danh mục, thời kỳ và định nghĩa nhãn của bài tập. Xem thêm [RESULTS](../RESULTS.md) cho 90+.

**Bàn giao cho W6.** `model_30.joblib` và `model_90.joblib` lưu estimator, danh sách features và mục tiêu. `comparison_*.csv` so ứng viên trên Validation. `oot_predictions_*.csv.gz` để tính lại metrics. `coef.csv` mô tả Logistic benchmark. Trang Kiểm định mô hình trình bày luồng 30+ đã dùng để cảnh báo.

**Điều kiện nghiệm thu.** Kiểm tra cohort rời nhau, cửa sổ nhãn trưởng thành, đúng thứ tự features và kết quả OOT có thể tái tạo. Với dữ liệu mở rộng, dành một giai đoạn riêng để hiệu chỉnh và một giai đoạn sau đó để kiểm tra lại.
