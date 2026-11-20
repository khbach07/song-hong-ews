# Kết quả kiểm định EWS Sông Hồng

## Phạm vi dữ liệu

Nguồn performance có **59.000** khoản duy nhất. Dev có **66.000** hồ sơ, trong đó **47.000** hồ sơ ghép được với performance. Cả **11.871/11.871** hồ sơ OOT ghép được. Sau khi loại 129 khoản performance thiếu hồ sơ đối ứng và 800 hồ sơ nhân viên/gian lận, còn **58.071** khoản đủ điều kiện xét snapshot.

## Chia tập thời gian · 30+

| Tập | Tháng snapshot | Snapshot | Khoản vay duy nhất | Nhãn dương | Tháng kết thúc nhãn muộn nhất |
|---|---|---:|---:|---:|---|
| Train | 2023-04-01 → 2023-08-01 | 53,540 | 18,166 | 2,164 | 2023-11-01 |
| Validation | 2023-12-01 → 2023-12-01 | 3,895 | 3,895 | 180 | 2024-03-01 |
| OOT | 2024-04-01 → 2025-03-01 | 109,062 | 11,814 | 1,405 | 2025-06-01 |

Validation chỉ có tháng 12/2023 sau khi áp điều kiện trưởng thành nhãn. Mốc OOT là 04/2024. Hai tháng 04 và 05/2025 ban đầu có một số kết quả dương ghi nhận sớm. Chúng vẫn lưu trong panel nhưng không góp vào mẫu kiểm định đủ ba tháng.

## Kết quả OOT

| Mục tiêu | Mô hình | Snapshot | Dương | AP | AP baseline DPD | ROC-AUC | Brier | PD bình quân | Tỷ lệ thực tế |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 30+ | Gradient Boosting | 109,062 | 1,405 | 0.4352 | 0.3417 | 0.8275 | 0.00898 | 2.58% | 1.29% |
| 90+ | Gradient Boosting | 110,343 | 1,709 | 0.9707 | 0.9564 | 0.9942 | 0.00519 | 0.76% | 1.55% |

Với 30+, mô hình cải thiện AP ngoài thời gian từ **0.3417 lên 0.4352**. PD bình quân là **2.58%**, trong khi tỷ lệ quan sát chỉ **1.29%**. Kết quả hỗ trợ xếp thứ tự rà soát. Khi diễn giải PD tuyệt đối, cần theo dõi và kiểm định hiệu chỉnh trên một cohort mới.

Với 90+, DPD hiện tại đã là baseline rất mạnh. Khi chỉ xét khoản đang dưới 30 DPD, tập OOT có **109,062** snapshot và **520** nhãn dương. AP khi đó là **0.8861**. Hai mô hình dùng tập đủ điều kiện khác nhau, nên bảng này không dùng để chọn 30+ hay 90+ theo độ lớn AP.

## Hiệu quả ngưỡng · 30+

Ngưỡng PD đóng băng từ validation: Green ≥ 0.0000% · Yellow ≥ 3.5886% · Orange ≥ 6.4210% · Red ≥ 23.3430%.

| Cấp | Snapshot | Dương | Tỷ trọng | Tỷ lệ dương trong cấp | Tỷ lệ bắt snapshot dương |
|---|---:|---:|---:|---:|---:|
| Green | 93,777 | 501 | 85.99% | 0.53% | 35.66% |
| Yellow | 9,836 | 153 | 9.02% | 1.56% | 10.89% |
| Orange | 4,792 | 232 | 4.39% | 4.84% | 16.51% |
| Red | 657 | 519 | 0.60% | 79.00% | 36.94% |

**Orange hoặc Red** chiếm **5.00%** snapshot OOT và bắt **53.45%** snapshot dương. OOT cho thấy năng lực xử lý thực tế và tỷ lệ bắt có thể khác validation. Theo dõi đồng thời khối lượng cảnh báo, số sự kiện bắt được và mức độ khớp PD theo tháng.

## Snapshot bàn giao

Tháng **2025-06** có **36,811** khoản đủ điều kiện hiển thị. Các cấp ghi nhận: Green 29,157 · Yellow 3,069 · Orange 2,408 · Existing 30+ 1,578 · Red 599. Danh mục này sử dụng lịch sử đã có đến snapshot và gồm cả hai cohort khi còn hoạt động. Bảng phân bổ cảnh báo của snapshot và bảng backtest ở trên có phạm vi khác nhau.
