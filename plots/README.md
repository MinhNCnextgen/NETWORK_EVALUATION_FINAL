# Vẽ biểu đồ S-PIE

Chạy từ thư mục dự án (Python 3.10+):

```powershell
python -m pip install -r plots/requirements.txt
python plots/plot_results.py --data data/result
```

Mặc định chỉ xuất PNG vào `plots/output/`. Script không hỗ trợ xuất PDF nữa. Có thể chọn SVG bằng `--formats svg` hoặc PNG và SVG bằng `--formats png svg`; tăng độ phân giải bằng `--dpi 300`.

## Thư mục đầu vào và đầu ra

Tự nhận diện tên `sim_<số>_run_<số>` hoặc `scenario_<số>_run_<số>`:

```text
data/result/scenario_1_run_1/Spie/...csv
→ plots/output/scenario_1_run_1/
data/result/sim_1_run_2/Spie/...csv
→ plots/output/sim_1_run_2/
```

Mỗi thư mục được xử lý độc lập. Scenario/seed/run được đọc từ config; tên thư mục chỉ dùng tổ chức output. CSV không thuộc các thư mục theo mẫu được xử lý như một bộ; nếu có cả hai loại sẽ xuất vào `ungrouped/`.

```powershell
python plots/plot_results.py --data data/result/scenario_1_run_1
python plots/plot_results.py --scenario 1 --seed 1 --run 1
python plots/plot_results.py --data data/result --combine --output plots/combined
```

`--combine` chủ động gộp các run tương thích, phục vụ boxplot; từ chối trùng scenario/AQM/seed/run và cấu hình không tương thích. Mỗi bộ cần config, goodput, queue, rtt, drops, link CSV cùng tiền tố. Các hình thiếu dữ liệu được bỏ qua và ghi trong manifest.

## Tên biểu đồ

Tên có dạng `scenario_<kịch bản>_<chỉ số>_<cách tổng hợp>.png`.

| Phần tên | Nội dung | Đối chiếu paper |
|---|---|---|
| `queue_packets_1s` | Queue trung bình thời gian từng giây | Hình 4 |
| `rtt_samples` | LastRTT của các luồng | Hình 5 |
| `group_throughput_window/cumulative` | Throughput liên kết nhóm nhỏ/lớn | Hình 6 |
| `throughput_bars_window/cumulative` | Cột throughput theo thời gian, scenario 2 | Hình 7 |
| `throughput_across_runs` | Throughput qua các run, scenario 2 | Hình 8 |
| `jain_window/cumulative` | Công bằng Jain | Hình 9 |
| `overflow_drops`, `active_drops` | Drop đầy và chủ động | Hình 10 ở scenario 2 |
| `total_throughput_window/cumulative` | Throughput tổng liên kết | Bổ sung |
| `group_goodput_window/cumulative` | Goodput nhóm tại ứng dụng | Bổ sung |
| `goodput_1s`, `link_throughput_mbps_1s` | Goodput và throughput liên kết từng giây | Bổ sung |
| `queue_bytes_1s`, `srtt_1s`, `jain_1s` | Queue byte, SRTT, Jain từng giây | Bổ sung |

`window` mặc định là từng cửa sổ 5s; `cumulative` là lũy kế [0,t). Đổi độ dài bằng `--period`. Bảng `summary.csv`, `per_second.csv`, `periods.csv` và `manifest.json` được xuất cùng hình. Tệp trùng tên bị ghi đè; manifest liệt kê kết quả của lượt chạy hiện tại.

## Quy ước đo

- Throughput = tổng wire_bytes / thời gian / 10^6, đơn vị 10^6 byte/s như trục paper. Cột Mbps bằng giá trị này nhân 8. Đo tại đầu phát bottleneck chiều đi, gồm header, TCP control và tái truyền. Paper chưa xác định rõ lớp đo tại đầu nhận, nên chưa khẳng định hai phép đo đồng nhất.
- Nhóm small/large lấy từ cấu hình nguồn scenario 1; equal ở scenario 2. Khác phân loại động của Sketch. C++ ghi flow, group và địa chỉ/cổng vào link.csv; gói không nhận diện là unknown. Python chỉ vẽ throughput nhóm khi tất cả run có schema mới. Tổng small+large+equal+unknown bằng throughput tổng. Unknown không tự phân bổ vào hai nhóm.
- Để bổ sung nhóm vào CSV cũ, cần build và chạy lại C++ đã cập nhật trong s-pie. Không thể suy ra flow từ trace chỉ chứa thời gian và số byte. Ánh xạ hiện tại dựa trên nguồn/đích/cổng TCP đích, phù hợp một ứng dụng trên mỗi cặp trong topology hiện tại.
- Goodput là payload nhận tại ứng dụng, giữ riêng. Queue tính tích phân occupancy theo thời gian, khác EWMA chưa được mô tả đầy đủ trong paper.
- RTT là scatter các sự kiện thay đổi LastRTT của tất cả flow, chọn cặp seed/run nhỏ nhất khi nhiều run; không nối mẫu khác flow. SRTT là chỉ số riêng.
- Jain tính từ byte từng flow trong cùng khoảng, gồm flow 0 byte. Cả khoảng không nhận byte trả NA. Không lấy trung bình Jain từng giây để thay Jain toàn khoảng.
- Drop phân loại theo thuật toán/reason, giữ unknown và drop ngoài queue riêng. Đo trong thời gian phát, loại drain.
- Đường tổng hợp là trung bình giữa run; vùng màu min–max, không phải CI. Boxplot chỉ có khi nhiều run; một run vẽ điểm. Không coi cửa sổ thời gian là các run độc lập.

Kết quả phiên bản cũ được giữ trong `plots/archive_output_before_png/` và `plots/archive_output_throughput_before_png/`. Kết quả dùng hiện tại nằm ở `plots/output/`.

Kiểm thử:

```powershell
python -m unittest discover -s plots -p test_plot_results.py
```

## Khôi phục nhãn luồng từ trace bị unknown

Python tự khôi phục flow/group cho các dòng flow=0, group=unknown nếu đầy đủ src_ip, dst_ip, protocol và dst_port khớp chính xác topology hiện tại của s-pie.cc: core 10.0.0.0/30, mỗi flow có hai subnet /30 kế tiếp, TCP đích port 5000. Với flow i (đánh số từ 1): IP nguồn = 10.0.0.0 + 8*i - 3, IP đích = 10.0.0.0 + 8*i + 2. Không áp dụng suy luận này cho topology có quy hoạch địa chỉ khác. Endpoint không khớp được giữ unknown; nhãn đã ghi mâu thuẫn với ánh xạ sẽ báo lỗi.

Khôi phục diễn ra trong bộ nhớ; CSV gốc không bị thay đổi. `flow_recovery.csv` và trường flow_recovery trong manifest ghi số khung/byte được khôi phục theo từng run. Đây là gán lại nhãn theo địa chỉ, không thay đổi byte, thời gian hoặc các kết quả mô phỏng. Tổng throughput các nhóm phải bằng throughput tổng khi cộng cả unknown.

Để mô phỏng mới có thông tin đăng ký kiểm chứng được, run-metrics.cc ghi các khóa flow.<id>.source/destination/destinationPort/group vào config và dừng sớm nếu chưa đăng ký luồng nào. Cần chép đồng bộ s-pie.cc, run-metrics.cc và run-metrics.h vào cây ns-3. C++ cập nhật chưa được build trong phiên sửa này.

Bộ tổng hợp Python xử lý lần lượt từng run và giải phóng raw trace sau khi lấy số liệu, chỉ giữ RTT của run đại diện để vẽ. Cách này giảm RAM khi gộp nhiều run.
