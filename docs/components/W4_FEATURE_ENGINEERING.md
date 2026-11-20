# W4 · Đặc trưng hành vi tại thời điểm đánh giá

**Phụ trách theo phân công gốc** Vân Anh. Module `src/ews/features.py`. Workbook `03_Risk_Indicators`.

| Cửa sổ | Đặc trưng | Ý nghĩa |
|---|---|---|
| t và t−1 | `mob`, `dpd_current`, `dpd_delta_1` | Tuổi khoản, mức trễ và đà thay đổi |
| t−2…t | `dpd_mean_3`, `dpd_max_3`, `late_months_3` | Cường độ và tần suất trễ gần đây |
| t−5…t | `dpd_max_6`, `late_months_6`, `dpd_obs_6` | Lịch sử dài hơn và mức độ đầy đủ |
| Đến t | `restructured` | Cơ cấu đã xảy ra tại hoặc trước tháng chấm |
| Lúc xin vay | `PROFILE` | Quy mô vay, DTI, CIC, sử dụng thẻ, tiền gửi và cờ thiếu |

Với DPD của t−2, t−1, t là 0, 8, 17 thì trung bình là 8,33, max là 17, số tháng trễ là 2 và delta là 9. Nếu tháng t−1 thiếu, trung bình dùng phần quan sát được, delta để NA. Số tháng trễ đếm các giá trị quan sát lớn hơn 0. `dpd_obs_6` giúp phân biệt lịch sử sạch với lịch sử thưa.

**Bàn giao cho W5.** `features.csv.gz` có cùng khóa và độ phủ snapshot với panel. Dùng allowlist `BEHAVIOR` và `PROFILE`. Pipeline và chấm tháng lịch sử cùng tái sử dụng `dpd_features`.

**Điều kiện nghiệm thu.** Chép một khoản vay và sửa DPD sau tháng t. Nhãn W3 có thể thay đổi, đặc trưng và PD tại t phải giữ nguyên. Kiểm thêm `restr_mob=t+1` để xác nhận cờ tại t bằng 0.
