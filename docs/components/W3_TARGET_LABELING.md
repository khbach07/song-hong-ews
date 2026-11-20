# W3 · Snapshot, target và cửa sổ theo dõi

**Phụ trách theo phân công gốc** Quanh. Module `src/ews/build_panel.py`. Workbook `13_Labels`.

`wide_to_long` tạo dãy liên tục theo MOB quan sát, giữ ô DPD thiếu trong dãy để phép shift phản ánh đúng tháng lịch. `snap_date` đại diện tháng `open_month + MOB`. Chọn snapshot từ MOB 3, DPD tháng t có dữ liệu và khoản còn mở sau tháng t.

| Trường hợp với ngưỡng K = 30 hoặc 90 | Nhãn |
|---|---|
| DPD tại t ≥ K | NA, đã ở ngưỡng |
| DPD tại t < K và thấy một tháng trong t+1…t+3 đạt K | 1, sự kiện quan sát |
| DPD tại t < K, đủ ba tháng và cả ba dưới K | 0, đủ theo dõi và không có sự kiện |
| Chưa thấy sự kiện và thiếu ít nhất một tháng tương lai hoặc tất toán sớm | NA, chưa đủ kết luận |

Với tháng mở 01/2024, MOB 3 là 04/2024. Nếu DPD tháng 4 bằng 8 và DPD tháng 5–7 lần lượt 10, 31, 0 thì `Target_30_3M=1` và `Target_90_3M=0`. Nếu tháng 7 thiếu, nhãn 30+ vẫn là 1, nhãn 90+ chưa xác định và `full_followup=False`. W5 chỉ đánh giá trên cửa sổ đủ ba tháng để hạn chế chọn mẫu bất đối xứng giữa dương và âm.

**Bàn giao.** `panel_target.csv.gz` giữ khóa `app_id,mob,snap_date`, cohort, nhãn, trạng thái, `full_followup` và `label_end`. W5 dùng `label_end` để tránh nhìn trước khi chia tập. Tháng DPD tại tất toán chỉ có thể góp vào cửa sổ kết quả nếu quan sát được.

**Điều kiện nghiệm thu.** Dựng các ví dụ đủ kỳ, thiếu tháng, tất toán, đã ở ngưỡng và chạm đúng 30/90. Nêu giới hạn rằng việc yêu cầu đủ theo dõi có thể loại những khoản tất toán sớm với hồ sơ khác nhóm còn theo dõi.
