# W6 · Ngưỡng, danh sách rà soát và web

**Vai trò theo phân công gốc** Risk Alerts & Dashboard. Module `src/ews/thresholds.py`, `src/ews/scoring.py`, `serve_ews.py` và `web/`. Workbook `05_EWS_Alerts`, `00_Overview`.

Ngưỡng là cận dưới của cấp. Từ validation, giới hạn tỷ trọng tích lũy Yellow trở lên 20%, Orange trở lên 10%, Red 3%. Các khoản cùng điểm được giữ cùng nhóm. Ngưỡng được đóng băng cùng mô hình. Tỷ trọng theo tháng phản ánh phân phối PD của tháng đó.

| Cấp | PD 30+ / 3M tại lần bàn giao | Hành động |
|---|---:|---|
| Green | Từ 0% | Theo dõi định kỳ |
| Yellow | Từ 3,5886% | Rà lịch trả và nhắc trước hạn |
| Orange | Từ 6,4210% | Liên hệ và làm rõ nguyên nhân |
| Red | Từ 23,3430% | Ưu tiên rà soát, chuyển chuyên viên |
| Existing 30+ | DPD hiện tại ≥30, PD để trống | Chuyển luồng quản lý khoản quá hạn |

Các giá trị hiển thị đã làm tròn. Khi chấm, hệ thống dùng ngưỡng đầy đủ trong `thresholds.csv`. Tín hiệu như DPD tăng và cơ cấu là quy tắc mô tả quan sát tại snapshot. Phần giải thích này hỗ trợ chuyên viên tra cứu dữ liệu.

**Luồng web.** `HistoricalScorer` nạp nguồn, làm sạch hồ sơ và tạo lịch sử đặc trưng lúc khởi động. Khi chọn tháng, dịch vụ chỉ dùng thông tin đến tháng đó và gọi mô hình 30+ đã lưu. Cache giữ ba tháng gần đây trong bộ nhớ. Trình duyệt lấy từng trang 20 dòng, mở chi tiết khoản vay và tải CSV cho toàn bộ kết quả khớp bộ lọc. KPI tính trên toàn snapshot tháng. API và hướng dẫn chạy nằm trong [WEB_RUNBOOK](../WEB_RUNBOOK.md).

**Điều kiện nghiệm thu.** Kiểm số lượng từng cảnh báo cộng bằng toàn danh mục. PD chỉ có cho DPD dưới 30. Mở Red và Existing 30+ để kiểm tra hành động hai luồng. So cùng tháng giữa CLI và web. Khi trình bày OOT, gọi đúng đơn vị snapshot dương vì cùng khoản và sự kiện có thể góp vào nhiều tháng.
