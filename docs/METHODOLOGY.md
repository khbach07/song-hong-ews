# Phương pháp và quy ước dữ liệu

## Bốn câu trả lời cho giảng viên

| Câu hỏi | Thiết kế |
|---|---|
| Dự báo gì? | Xác suất một khoản vay còn mở, đang dưới ngưỡng, chạm DPD 30+ trong t+1 đến t+3. Tạo một mô hình 90+ riêng với điều kiện DPD hiện tại dưới 90. |
| Dùng thông tin gì? | Lịch sử trả nợ trong performance và hồ sơ đã biết tại lúc xin vay từ Dev/OOT. Các mô hình dùng dữ liệu đến snapshot t. |
| Đặc trưng gì? | DPD hiện tại, trung bình/cao nhất 3 tháng, số tháng quá hạn, biến thiên DPD, mức cao nhất và tần suất trong 6 tháng, tuổi khoản vay, trạng thái cơ cấu và một nhóm thông tin tài chính/CIC tĩnh. |
| Quy trình ra sao? | Kiểm tra nguồn → xác định phạm vi → dựng snapshot → tính features và nhãn → kiểm định thời gian → chọn ngưỡng trên validation → chấm điểm → theo dõi cảnh báo và đối chiếu thực tế. |

## Snapshot, sự kiện và tất toán

- Khóa dự báo là `(app_id, mob)`. `snap_date` là ngày đầu tháng đại diện cho tháng đánh giá, tính từ `open_month + mob`. Giả định `open_month` là MOB 0 theo bản phân công gốc. Ngày trong cột này là nhãn lịch của tháng, thời điểm thông tin DPD được giả định là sau khi snapshot tháng hoàn tất.
- Snapshot bắt đầu MOB 3. DPD tại tháng đánh giá phải có số liệu. Khoản vay tất toán tại hoặc trước MOB của snapshot được ngừng chấm điểm. DPD ở chính tháng tất toán được giữ khi xác định kết quả tương lai nếu nguồn có ghi nhận.
- Với từng ngưỡng, nhãn bằng 1 khi phát hiện ít nhất một tháng tương lai chạm ngưỡng. Nhãn bằng 0 khi cả ba tháng đều có DPD và đều dưới ngưỡng. Nhãn trống nếu khoản vay đã ở trên ngưỡng tại t hoặc chưa quan sát đủ để kết luận.
- Một sự kiện được thấy trước khi cửa sổ trưởng thành vẫn lưu nhãn 1 để truy vết. Huấn luyện và backtesting yêu cầu `full_followup = True` cho cả dương lẫn âm. Vì vậy chỉ số báo cáo áp dụng cho các cửa sổ đủ quan sát. Khoản tất toán sớm có thể tạo thiên lệch chọn mẫu do cơ chế cạnh tranh với quá hạn.
- Một khoản từng 30+ rồi hồi phục về dưới 30 có thể quay lại tập EWS. Các khoản đang từ 30 DPD xuất hiện trong luồng Existing 30+ và để trống PD 30+.
- Chỉ đưa vào phạm vi khoản Approved có hồ sơ đối ứng. Loại 800 hồ sơ nhân viên/gian lận được đánh dấu trong Dev và giữ Indeterminate theo điều kiện tại từng snapshot. Các trường phân loại vintage để phân tích nguồn, nằm ngoài danh sách đặc trưng.

## Biến đầu vào

| Biến | Cách đọc |
|---|---|
| `mob` | Tuổi khoản vay theo tháng tại snapshot |
| `dpd_current` | DPD ở tháng t |
| `dpd_mean_3`, `dpd_max_3` | Trung bình và lớn nhất trong t−2 đến t, dùng các giá trị đã quan sát |
| `late_months_3` | Số giá trị DPD lớn hơn 0 trong t−2 đến t |
| `dpd_delta_1` | DPD tại t trừ DPD tại t−1, để trống khi thiếu một đầu |
| `dpd_max_6`, `late_months_6`, `dpd_obs_6` | Mức cao nhất, số tháng quá hạn và số tháng thật sự có DPD trong t−5 đến t |
| `restructured` | 1 nếu thời điểm cơ cấu đã đến vào hoặc trước t, 0 nếu chưa ghi nhận |
| `loan_amount_mil`, `dti_pct` | Quy mô vay và nghĩa vụ nợ/thu nhập lúc xin vay, DTI được chặn trên ở 200 theo quy tắc W2 |
| `cic_hist_months`, `num_lenders`, `inq_6m`, `dpd_cnt_12m` | Độ dài lịch sử, số tổ chức có dư nợ, số lần tra cứu và số lần trễ theo CIC lúc xin vay |
| `card_util_pct`, `deposit_avg_3m_mil` | Mức sử dụng thẻ và số dư tiền gửi tại lúc xin vay. Giữ giá trị vượt 100% và tín hiệu thiếu riêng. |

Mô hình dùng danh sách cho phép trong `features.py`. `target` gốc, `perf_class`, `max_dpd_12m`, `decision`, `gender`, DPD sau t và MOB cơ cấu tương lai chỉ có thể xuất hiện trong dữ liệu nguồn hoặc bước phân tích phù hợp. Thu nhập được phân tích drift ở W2 và đứng ngoài đặc trưng bản này. Trung vị và chuẩn hóa của các mô hình dùng tiền xử lý được fit riêng trên Train. Gradient Boosting xử lý giá trị thiếu trực tiếp.

## Kiểm định, chọn mô hình và ngưỡng

- Giữ cohort nguồn OOT 2024H1 để kiểm định cuối. Dev có cohort mở trước 09/2023 dành cho train và cohort còn lại dành cho validation. Chỉ lấy Train có cửa sổ kết quả kết thúc trước snapshot sớm nhất của validation. Validation có cửa sổ kết thúc trước snapshot OOT đầu tiên. Một `app_id` chỉ thuộc một tập.
- Chọn theo **Average Precision** trên validation, dùng Brier để phá hòa. AP thích hợp khi sự kiện hiếm vì phản ánh chất lượng xếp hạng theo precision và recall. ROC-AUC là chỉ số phân biệt bổ sung. Brier và bảng calibration cho biết chất lượng của PD tuyệt đối. Brier thấp hơn là tốt hơn khi so trên cùng mẫu.
- Baseline xếp hạng theo DPD hiện tại. Logistic có hai phiên bản để kiểm tra giá trị tăng thêm của hồ sơ. Decision Tree là mốc dễ diễn giải, Random Forest và Gradient Boosting cho phép học tương tác phi tuyến. `coef.csv` là hệ số trên thang đầu vào gốc của Logistic có hồ sơ. Tính logit bằng hệ số chặn cộng tổng hệ số nhân đặc trưng sau điền trung vị, rồi lấy sigmoid. Mô hình Gradient Boosting được chấm trong Python.
- Cấp Red, Orange trở lên và Yellow trở lên có giới hạn mục tiêu tương ứng 3%, 10% và 20% trên danh mục validation. Các tỷ trọng này là giả định phân bổ nguồn lực cho đồ án. Điểm bằng nhau xử lý cùng nhóm. Ngưỡng được đóng băng trước OOT, do đó tỷ trọng thực tế có thể biến động.
- Reason code ghi nhận tín hiệu quan sát được như DPD tăng, trễ nhiều tháng hoặc đã cơ cấu. Với khoản chưa có tín hiệu hiển thị, hệ thống ghi theo dõi theo điểm mô hình. Đây là quy tắc đọc hồ sơ phục vụ vận hành.
- Các tỷ lệ tính trên snapshot khoản vay–tháng. Một khoản có thể xuất hiện nhiều lần và một sự kiện có thể thuộc nhiều cửa sổ dự báo. Khi nói “bắt được sự kiện”, đơn vị là **snapshot dương**.

## Hợp đồng bàn giao

| File | Khóa và vai trò |
|---|---|
| `panel_target.csv.gz` | `app_id, mob, snap_date`, cohort, 2 nhãn, trạng thái, mốc trưởng thành và cờ đủ quan sát |
| `features.csv.gz` | Cùng khóa, giá trị hành vi và hồ sơ đã xử lý để huấn luyện |
| `scored.csv` | Danh mục tháng, điểm xác suất, mức cảnh báo, tín hiệu và hành động |
| `oot_predictions_*.csv.gz` | Mã, thời điểm, nhãn, điểm xác suất để tính lại kết quả OOT |
| `run_summary.json` | Thông tin split, kết quả OOT, độ phủ, số lượng cảnh báo và SHA-256 nguồn |

## Giới hạn khi diễn giải

Validation hiện chỉ gồm một tháng có nhãn trưởng thành trước OOT. Dữ liệu DPD có tối đa 24 MOB và kết thúc theo tháng. Bộ dữ liệu không có số dư khoản vay theo thời gian, dòng tiền hoặc lịch thực hiện thu hồi nợ. PD chưa được hiệu chỉnh độc lập trên một cohort mới. Đồ án hỗ trợ ưu tiên rà soát và đánh giá phương pháp theo dữ liệu được giao.
