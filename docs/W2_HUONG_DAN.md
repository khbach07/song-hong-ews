# Hướng dẫn phần W2 – Data Quality Controller

## 1. Phần việc của W2 là gì?

Theo bản phân công, W2 là người "kiểm tra chất lượng nguyên liệu" trước khi các bạn khác dùng dữ liệu:

1. Đếm giá trị **thiếu** (và hiểu vì sao thiếu – không tự thay bằng 0).
2. Tìm giá trị **bất thường** (tuổi vô lý, income > 500, DTI > 200, card utilization > 100).
3. Kiểm tra **drift** thu nhập theo thời gian (đứt gãy từ 07/2023).
4. Chốt **quy tắc làm sạch + danh sách biến phải loại** (chống data leakage) và viết thành code để cả nhóm dùng chung.

Sản phẩm bàn giao: báo cáo Data Quality + danh sách quy tắc, `clean_rules.py`, sheet `02_Customer_Profile` và `DQ_Report` trên workbook/Google Sheets chung của nhóm.

## 2. Mình đã làm những gì (file nào làm gì)

| File                                  | Làm gì                                                                                                                                                                                                                                                                                             |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/ews/clean_rules.py`              | **Code chính của W2.** Đọc hồ sơ, đếm thiếu / ngoại lai / drift, làm sạch, gắn cờ, loại biến leakage. W4/W5 chỉ gọi hàm trong file này.                                                                                                                                                            |
| `src/ews/dq_report.py`                | Tạo file Excel báo cáo `W2_Customer_Profile_DQ.xlsx` **theo đúng kiểu mẫu của cô** (`Q02_Data_description.xlsx`: Q2b, Q2c): các bảng tổng hợp là công thức Excel (COUNTIFS, PERCENTILE, MEDIAN…) chạy trên dữ liệu thật. Đồng thời xuất `data/interim/customer_profile_clean.csv` (hồ sơ đã sạch). |
| `outputs/W2_Customer_Profile_DQ.xlsx` | Báo cáo Excel phụ trợ. Sheet: Q2b_Missing_outliers, Q2c_Missing_bad_rate, Outlier_Rules, Drift_Income, Quy_tac_xu_ly, Data_Profile (dữ liệu), README.                                                                                                                                              |
| Workbook / Google Sheets chung        | Sheet `02_Customer_Profile` đã áp đúng các quy tắc W2 bằng công thức động nối từ `01_Raw_Data`; `DQ_Report` đã điền đầy đủ kết quả và quy tắc chốt.                                                                                                                                                |

## 3. Cách chạy (làm lần lượt)

```bash
# 1) Cài đặt, bỏ 3 file CSV vào data/raw/ (perf_monthly, dev_2023, oot_2024H1)
pip install -r requirements.txt
# 2) Chạy từ thư mục gốc repo
PYTHONPATH=src python -m ews.dq_report        # Windows PowerShell:  $env:PYTHONPATH="src"; python -m ews.dq_report
```

Kết quả: `outputs/W2_Customer_Profile_DQ.xlsx` và `data/interim/customer_profile_clean.csv`.
Mở file Excel: Excel sẽ tự tính công thức khi mở (có thể mất vài giây vì có ~59 nghìn dòng).

Dùng trong code của bạn khác:

```python
from ews import clean_rules as cr
prof = cr.load_clean_profile()   # hồ sơ sạch + cờ f_*
X    = cr.model_ready(prof)      # đã bỏ biến leakage -> ghép với features.csv theo app_id
```

## 4. Giải thích từng bước & kết quả trên dữ liệu thật của nhóm

**Tập dữ liệu**: 58.871 khoản vay có lịch sử trả nợ = 47.000 khoản trong `dev_2023` (Approved, có trong perf_monthly) + 11.871 khoản trong `oot_2024H1`. Không dùng hồ sơ bị từ chối (không có lịch sử trả nợ) và loại 129 khoản `SH24` cơ cấu không có hồ sơ trong `oot_2024H1`. Mỗi `app_id` đúng 1 dòng.

### 4.1 Giá trị thiếu (Q2b)

| Biến               | Thiếu  | Tỷ lệ | Nghĩa của "thiếu"          |
| ------------------ | ------ | ----- | -------------------------- |
| income_mil         | 2.677  | 4,5%  | Khách không khai           |
| work_months        | 6.320  | 10,7% | Không khai                 |
| card_util_pct      | 17.677 | 30,0% | Không có thẻ               |
| deposit_avg_3m_mil | 22.466 | 38,2% | Chưa có tài khoản tiền gửi |

Các biến còn lại (và mọi biến phân loại) không thiếu. **Quyết định:** giữ trống và gắn cờ `f_*_missing`; không điền 0 vì "không có thẻ" khác "dùng thẻ 0%".

**Q2c – thiếu có mang thông tin rủi ro không?** So bad rate (target gốc 90+/12 tháng, chỉ để phân tích) của nhóm thiếu với cả danh mục (5,04%):
income thiếu 8,7%, work_months thiếu 8,8% → **rủi ro hơn hẳn** (> 1,5 lần); card_util thiếu 3,4%, deposit thiếu 5,4% → gần/ dưới trung bình nhưng nhóm lớn và có nghĩa nghiệp vụ. Kết luận giống nhận xét trong mẫu của cô (cô tính trên mẫu Good+Bad của dev nên số lệch rất nhẹ: 8,5%/8,6%/3,4%/5,4%).

### 4.2 Giá trị bất thường (Outlier_Rules)

| Quy tắc                                                                                  | Số vi phạm    | Xử lý                                                             |
| ---------------------------------------------------------------------------------------- | ------------- | ----------------------------------------------------------------- |
| R01 tuổi < 18 hoặc > 75                                                                  | 61 + 61 = 122 | kẹp về nhóm biên gần nhất [18, 75] + cờ `f_age_invalid`           |
| R02 income > 500                                                                         | 76            | chặn trên (cap) ở 500 + cờ `f_income_outlier`                     |
| R03 DTI > 200                                                                            | 18            | giữ nguyên giá trị thực tế + cờ `f_dti_outlier` (`cap_dti=False`) |
| R04 card_util > 100                                                                      | 1.734         | giữ giá trị + cờ `f_card_over100`                                 |
| R05–R08 (work_months/cic_hist vs tuổi; dpd_cnt_6m ≤ dpd_cnt_12m; dpd_cnt_12m ≤ cic_hist) | 0             | không vi phạm                                                     |

**Lý do chốt quy tắc xử lý ngoại lai:**

- **Tuổi ngoài [18, 75]:** Kẹp về nhóm tuổi hợp lệ gần nhất (`< 18` đưa về `18`, `> 75` đưa về `75`) thay vì xóa thành trống để giữ trọn số lượng quan sát khi ghép mô hình, đồng thời bật cờ `f_age_invalid = 1`.
- **Thu nhập > 500 triệu:** Chặn trên (cap) ở mức `500` triệu và bật cờ `f_income_outlier = 1` để giảm tác động của các giá trị cực đoan mà vẫn giữ được tín hiệu khách hàng có thu nhập cao.
- **DTI > 200%:** Giữ nguyên giá trị thực tế (`cap_dti=False`) và bật cờ `f_dti_outlier = 1` vì khách hàng có tỷ lệ nghĩa vụ nợ cao bất thường có thể phát sinh thực tế và mang tín hiệu rủi ro quan trọng.

Lưu ý: số trong `data_dictionary.csv` (122 tuổi, 76 thu nhập, 29 DTI, 2.139 card_util) được đếm trên các phạm vi khác nhau nên không khớp hoàn toàn. Hãy dùng số đếm trực tiếp trên tập EWS (như bảng trên) và nói rõ phạm vi khi báo cáo.

### 4.3 Drift thu nhập (Drift_Income)

Trung vị thu nhập theo tháng nộp hồ sơ: **12 triệu (01–06/2023) → 15 triệu (từ 07/2023)**, tỷ số 1,25, đúng như ghi chú dữ liệu (biểu mẫu LOS mới). Biểu đồ trong sheet cho thấy bước nhảy rõ ràng.
**Quyết định:** chỉ gắn `income_period` (`pre_0723` / `post_0723`), **không tự hiệu chỉnh** (mặc định `adjust_income_drift=False`). Lý do: hệ quả của drift lên mô hình là chuyện nhóm cần quyết (nhân 1,25 cho giai đoạn trước, hoặc dùng income dạng tương đối / bỏ income). Nếu nhóm đồng ý hiệu chỉnh, gọi `clean_profile(df, adjust_income_drift=True)`.

### 4.4 Loại biến chống leakage

`drop_leakage()` bỏ 8 biến: `perf_class, target, max_dpd_12m, exclusion_reason, indeterminate_reason, decision, curr_max_cic_group, gender` (`perf_class` và `target` chỉ dùng phân tích Q2c). `restr_mob` chỉ dùng dạng cờ `restr_flag_t = (restr_mob ≤ t)` – do W4 tạo ở `features.py`.
Lưu ý: W3 vẫn cần `perf_class` / `exclusion_reason` để xác định phạm vi (loại Excluded, giữ Indeterminate) – đó là dùng để **lọc quan sát**, không đưa vào input mô hình.

### 4.5 Điền thiếu khi huấn luyện (tùy chọn cho W5)

`fit_medians(train)` + `impute_median(df, medians)`: trung vị tính **chỉ trên Dev** rồi áp cho OOT, để không rò rỉ thông tin từ OOT. Cờ `f_*_missing` vẫn giữ để mô hình biết giá trị này vốn bị thiếu.

## 5. Đưa kết quả vào Workbook / Google Sheets của nhóm

- Sheet `02_Customer_Profile`: đã có công thức làm sạch (kẹp tuổi `[18, 75]`, chặn trên thu nhập `500`, giữ nguyên `DTI`) + đủ 8 cờ `f_*`, tự động cập nhật khi `01_Raw_Data` thay đổi tháng snapshot.
- Sheet `DQ_Report`: đã điền đầy đủ kết quả Mục A (Missing), Mục B (Outlier), Mục C (Drift 18 tháng) và Mục D (Chính sách chống leakage) khớp với `THRESH` trong `clean_rules.py`.
- Sheet `Feature_Dict`: đã xác nhận **"Đồng ý"** cho các biến hồ sơ tĩnh để W4 sử dụng.

## 6. Việc cần báo nhóm / dễ bị hỏi khi bảo vệ

1. Vì sao không điền 0 cho giá trị thiếu? (thiếu có nghĩa nghiệp vụ; Q2c cho thấy nhóm thiếu income/work_months rủi ro hơn.)
2. Income > 500, tuổi ngoài [18, 75] và DTI > 200 xử lý ra sao và vì sao? (Income chặn trên 500 và tuổi kẹp về biên gần nhất `[18, 75]` để giảm nhiễu ngoại lai mà không mất dòng; DTI > 200 giữ nguyên vì có thể xảy ra thực tế – tất cả đều gắn cờ `f_*`.)
3. Drift 07/2023 ảnh hưởng gì? (thu nhập tăng ~25% do đổi biểu mẫu, không phải khách giàu lên – nên cẩn thận khi dùng income làm feature và khi chia Dev/OOT theo thời gian.)
4. Vì sao loại `gender`, `curr_max_cic_group`...? (leakage/nhạy cảm theo quy ước nhóm.)
5. 129 khoản SH24 trong perf_monthly không có hồ sơ (đều là khoản đã cơ cấu `Indeterminate`, không nằm trong OOT) – `load_profile()` đã loại khỏi tập hồ sơ sạch (còn 58.871 dòng).

## 7. Checklist W2

- [x] Chạy `python -m ews.dq_report` kiểm thử toàn bộ dữ liệu thật
- [x] Chốt các quy tắc trong `THRESH` và `clean_profile` (`clean_rules.py`)
- [x] Đồng bộ mô tả quy tắc mới trong `dq_report.py` và `W2_HUONG_DAN.md`
- [x] Hoàn thiện `DQ_Report`, `02_Customer_Profile` và xác nhận biến ở `Feature_Dict`
- [x] Báo W4/W5 cách gọi `load_clean_profile()` / `model_ready()`
