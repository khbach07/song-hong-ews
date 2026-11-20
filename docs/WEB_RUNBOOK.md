# Vận hành web demo

## Khởi động

Từ thư mục dự án, chạy `python serve_ews.py` trong môi trường đã cài `requirements.txt`. Chờ log hiển thị địa chỉ rồi mở <http://127.0.0.1:8765>. Mặc định web mở tháng bàn giao ghi trong run_summary.json. Nhấn Ctrl+C để dừng. Web phục vụ trên loopback và dùng artifact local đáng tin cậy.

| Nhu cầu | Lệnh |
|---|---|
| Đổi cổng | `python serve_ews.py --port 8766` |
| Dùng một lần huấn luyện mới | `python serve_ews.py --model-dir outputs/rebuilt` |
| Dùng thư mục nguồn khác | `python serve_ews.py --raw data/raw_new --model-dir outputs/rebuilt` |
| Xuất snapshot và HTML độc lập | `python score_ews.py --month 2024-09 --out outputs/sep_2024` |

Thư mục model là bộ kết quả do `run_ews.py` tạo. Khi khởi động, web kiểm tra `manifest.json` và fingerprint của ba CSV, sau đó nạp mô hình 30+ và cache tối đa ba tháng. Dashboard kiểm định và chất lượng phản ánh lượt huấn luyện hiện trong thanh điều hướng. Nếu đổi dữ liệu, chạy lại pipeline với `--raw` và `--out` mới rồi khởi động web bằng đúng cặp thư mục.


## API và luồng xử lý

| GET | Hành vi |
|---|---|
| `/api/meta` | Tháng hợp lệ, kết quả mô hình, ngưỡng và báo cáo |
| `/api/snapshot?month=2025-06&level=Red&page=1` | KPI toàn tháng và tối đa 20 bản ghi lọc |
| `/api/export?month=2025-06&level=Red` | CSV toàn bộ kết quả lọc |

`level`, `cohort` và `q` là bộ lọc tùy chọn. `q` tìm chuỗi con của mã khoản vay. Tháng ngoài phạm vi và bộ lọc sai trả HTTP 400. Web là ứng dụng demo đọc nguồn và artifact, tải trang qua Python. Dashboard HTML cũ mở trực tiếp để dự phòng thuyết trình.

## Kịch bản demo 4 phút

1. Mở 06/2025. Đối chiếu 36.811 khoản hoạt động, 599 Red và 1.578 Existing 30+ với báo cáo bàn giao.
2. Chọn Red, mở một khoản, đọc DPD hiện tại, PD ba tháng, tín hiệu và hành động. Xuất CSV. Sau đó chuyển Existing 30+ và quan sát cột PD hiển thị dấu gạch.
3. Đổi về 09/2024 để minh họa chấm lại từ dữ liệu đã có tại tháng lịch sử. Lượng cảnh báo thay đổi trong khi ngưỡng vẫn cố định.
4. Mở Kiểm định mô hình. So AP với DPD baseline và dùng biểu đồ để giải thích vì sao cần thận trọng với PD tuyệt đối. Kết thúc bằng nguồn, missing và drift ở màn hình Chất lượng dữ liệu.

## Xử lý lỗi thường gặp

| Triệu chứng | Kiểm tra |
|---|---|
| Cổng đang dùng | Dùng `--port 8766` và mở đúng URL hiện trong log |
| Lỗi nạp model | Kiểm tra thư mục model và phiên bản scikit-learn 1.8.0 |
| Thiếu CSV | Kiểm tra tên đủ ba file nguồn hoặc chạy lại pipeline ra thư mục model |
| Không có khoản khớp | Xóa mã tra, đặt cohort và mức cảnh báo về Tất cả rồi áp dụng |
| Mất kết nối | Xác nhận tiến trình Python vẫn đang chạy |

Phạm vi hiện tại là demo tại máy cá nhân, dữ liệu theo tháng lịch sử, báo cáo OOT và xuất danh sách rà soát. Khi chuyển thành công cụ ngân hàng dùng chung, cần xác định quyền truy cập, cơ chế audit và chính sách phê duyệt mô hình theo quy trình của đơn vị.
