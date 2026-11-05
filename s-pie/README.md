# S-PIE trên ns-3.45

## Các file trong thư mục và chức năng

| File | Chức năng | Khi nào cần đọc hoặc sửa |
|---|---|---|
| [`s-pie.cc`](s-pie.cc) | Chương trình mô phỏng chính có hàm `main()`: đọc tham số; tạo topology dumbbell, địa chỉ IP, nguồn ON/OFF và sink; chọn AQM; gắn bộ đo; lập lịch chạy và xuất goodput từng giây. Cũng đăng ký ánh xạ nguồn–đích sang flow ID và nhóm tải cho trace liên kết. | Thay topology, lịch nguồn, kịch bản, tham số chung hoặc bổ sung phép đo. |
| [`spie-queue-disc.h`](spie-queue-disc.h) | Khai báo lớp `ns3::SpieQueueDisc`, các hàm xử lý queue, khóa luồng, bảng Sketch, timer và trạng thái điều khiển PIE. | Xem cấu trúc lớp, kiểu dữ liệu, đơn vị và thêm trạng thái/hàm mới. |
| [`spie-queue-disc.cc`](spie-queue-disc.cc) | Cài đặt thuật toán S-PIE: khai báo attribute; enqueue/dequeue; đọc khóa 5-tuple; băm và truy vấn CMS; tính ngưỡng luồng lớn; cập nhật/reset Sketch; ước lượng trễ và cập nhật xác suất PIE. | Nghiên cứu hoặc sửa cơ chế thuật toán. Các hàm chính: `DoEnqueue`, `DoDequeue`, `CalculateP`, `ReadFlowKey`, `Bucket`, `Estimate`, `AboveThreshold`, `RecordAccepted`, `ResetWindow`. |
| [`run-metrics.h`](run-metrics.h) | Khai báo lớp `RunMetrics`, giao diện gắn trace, đăng ký luồng và các stream xuất CSV. | Xem các phép đo được hỗ trợ; thêm giao diện thu dữ liệu. |
| [`run-metrics.cc`](run-metrics.cc) | Thu trace queue, drop, LastRTT/SRTT, khung truyền trên bottleneck và cấu hình. Phân tích bản sao header PPP/IPv4/TCP để ghi flow/group vào link trace; ghi ánh xạ đã đăng ký vào config. | Sửa định dạng CSV, thêm trường đo hoặc kiểm tra nhận diện luồng. |
| [`run-simulation.sh`](run-simulation.sh) | Điều phối batch: nhận tùy chọn Bash, cấu hình tham số, configure/build một lần, chạy nhiều job có giới hạn song song, chia folder scenario/run/AQM, ghi log và gọi `summarize.py`. | Chọn số run, kịch bản, số tiến trình, thuật toán, thư mục kết quả và bộ tham số thí nghiệm. |
| [`summarize.py`](summarize.py) | Hậu xử lý **một run** từ raw CSV trong khoảng giây nguyên `[start,end)`: goodput tổng/nhóm, Jain, queue trung bình thời gian, LastRTT/SRTT trung bình sự kiện, wire rate và drop theo reason. In bảng metric/value ra stdout. Chỉ dùng thư viện chuẩn Python. | Tạo summary hoặc kiểm tra chỉ số của một khoảng đo; không vẽ hình và không gộp nhiều run. |
| [`test_batch_runner.py`](test_batch_runner.py) | Kiểm thử script Bash bằng wrapper NS-3 giả trong thư mục tạm: số job, folder output, build một lần, giới hạn song song, dry-run, chống ghi đè, job lỗi và tham số dòng lệnh. | Kiểm tra bộ điều phối sau khi sửa script; không phải kiểm thử tính đúng đắn thuật toán S-PIE. |
| [`README.md`](README.md) | Hướng dẫn các file, cách chạy, tham số, định nghĩa dữ liệu và kiểm chứng. | Điểm bắt đầu khi sử dụng hoặc bàn giao mã. |

Các file `.cc`/`.h` được dùng để build chương trình mô phỏng. Shell và Python phục vụ chạy batch, tổng hợp và kiểm thử; không phải một phần của bộ điều khiển AQM.

### Quan hệ giữa các file

```text
run-simulation.sh
  ├─ configure/build chương trình s-pie
  ├─ chạy s-pie.cc cho mỗi scenario/run/AQM
  │    ├─ spie-queue-disc.h/.cc: xử lý S-PIE khi chọn aqm=Spie
  │    ├─ AQM có sẵn trong NS-3 khi chọn Pie, Red, CoDel
  │    └─ run-metrics.h/.cc: ghi raw trace và cấu hình
  └─ summarize.py: đọc raw CSV, ghi summary của mỗi job

test_batch_runner.py → kiểm tra run-simulation.sh bằng NS-3 giả
```

Đọc mã theo thứ tự `s-pie.cc` → `spie-queue-disc.h/.cc` → `run-metrics.h/.cc` để hiểu mô hình, thuật toán và phép đo. Để chạy thí nghiệm, bắt đầu từ `run-simulation.sh`.

### Phân biệt hai loại nhãn luồng

`small`/`large` trong trace là **nhóm nguồn cấu hình của kịch bản 1** (nửa đầu/nửa sau); scenario 2 dùng `equal`. Nhóm này phục vụ phân tích throughput. Quyết định luồng lớn của Sketch được tính động từ tần suất gói trong cửa sổ và không lấy nhãn nhóm cấu hình làm đầu vào.

Phải chép đồng bộ `s-pie.cc`, `run-metrics.cc` và `run-metrics.h` vào cây NS-3 khi cập nhật nhận diện luồng. `RegisterFlow()` cần được gọi trước khi truyền. Mã hiện tại dừng sớm nếu chưa đăng ký luồng nào; các ánh xạ được ghi dưới khóa `flow.<id>.*` trong config.

## Chạy bằng script cấu hình

Chép cả thư mục vào `scratch/s-pie` của NS-3.45. Trong Ubuntu/WSL, từ gốc NS-3 chạy:

```bash
# Xem trợ giúp hoặc kiểm tra các lệnh dự kiến
bash scratch/s-pie/run-simulation.sh --help
bash scratch/s-pie/run-simulation.sh --scenario 1 --runs 3 --dry-run

# 3 run cho kịch bản 1; tối đa 2 job đồng thời
bash scratch/s-pie/run-simulation.sh --scenario 1 --runs 3 --parallel 2
```

Mỗi job là một tổ hợp scenario/run/AQM. Script configure/build một lần rồi dùng `ns3 run --no-build` cho các job. Mặc định trong file là `SCENARIOS=(1 2)`, `RNG_RUNS=(1 2 3)`, bốn AQM và `MAX_PARALLEL=2`; tùy chọn dòng lệnh ghi đè cho lần gọi hiện tại. Nếu đã có kết quả, chọn `--start-run` mới hoặc một `--result-dir` khác.

Output mỗi job nằm trong `result/scenario_<số>_run_<số>/<AQM>/`, gồm raw CSV, summary và log riêng. `OVERWRITE=false` chặn ghi đè CSV cùng tiền tố. `--dry-run` chỉ in lệnh, không build/chạy. Chỉnh các biến đầu file để đổi tham số chi tiết; xem các mục batch bên dưới cho đầy đủ tùy chọn.

Nếu script nằm ngoài cây NS-3, đặt `NS3_ROOT` đúng đường dẫn gốc NS-3 và vẫn chép mã C++ vào `scratch/s-pie`. Các biến ngưỡng để trống giữ `Time::Max()`; các giá trị chưa có tùy chọn C++ được liệt kê trong script.

## Chạy lần đầu

Chép cả thư mục `s-pie` vào `scratch/` của cây nguồn **ns-3.45**. Từ thư mục chứa chương trình `ns3`, chạy:

```bash
./ns3 configure
./ns3 build s-pie
./ns3 run "s-pie --scenario=1 --aqm=Spie --output=s1-spie.csv"
./ns3 run "s-pie --scenario=2 --aqm=Spie --output=s2-spie.csv"
```

Mỗi lần chạy chỉ mô phỏng một cấu hình. Dùng tên CSV riêng vì chương trình mở lại tệp đầu ra từ đầu. Thay `Spie` bằng `Pie`, `Red` hoặc `CoDel` để chạy đối chứng. Để ghép cặp giữa các thuật toán, giữ cùng `--RngRun`, tốc độ, lịch nguồn và seed hash. Đổi `--RngRun=2` cho lần lặp tiếp theo. Nếu muốn đổi cả họ băm giữa các lần lặp, đặt `HashSeed` rõ ràng cho mỗi run.

## Chỉnh số liệu

Các giá trị khởi đầu của **thí nghiệm** nằm ở đầu `main` trong `s-pie.cc`. Có thể ghi đè bằng dòng lệnh. Dùng `./ns3 run "s-pie --PrintHelp"` để xem danh sách. Ví dụ sau thay đồng thời kích thước bảng, thời gian reset và trễ mục tiêu:

```bash
./ns3 run "s-pie --scenario=1 --aqm=Spie --ns3::SpieQueueDisc::SketchWidth=512 --ns3::SpieQueueDisc::SketchWindow=250ms --ns3::SpieQueueDisc::QueueDelayReference=10ms --output=s1-w512.csv"
```

| Đại lượng | Tên tùy chọn | Giá trị khởi đầu |
|---|---|---|
| Cặp nguồn–đích, giới hạn qdisc chiều đi | `flows`, `limit` | 100, 50p |
| Tốc độ và trễ mỗi access link | `accessRate`, `accessDelay` | 100Mbps, 5ms |
| Tốc độ và trễ bottleneck | `coreRate`, `coreDelay` | 50Mbps, 20ms |
| Kịch bản 1, tốc độ ON của hai nửa số nguồn | `smallRate`, `largeRate` | 1Mbps, 50Mbps |
| Kịch bản 2, tốc độ ON chung | `equalRate` | 10Mbps |
| Số byte mỗi lần ứng dụng gửi, thời gian phát (s) | `payload`, `duration` | 1000, 30 |
| Thời gian ON và OFF (s) | `onTime`, `offTime` | Mỗi giá trị là `ns3::ExponentialRandomVariable[Mean=1]` |
| Số hàng, số ô mỗi hàng | `SketchRows`, `SketchWidth` | 4, 1024 |
| Chu kỳ xóa bảng, seed cơ sở | `SketchWindow`, `HashSeed` | 500ms, 1 |
| Hệ số chia trễ mục tiêu | `DelayDivisor` | 3 |
| Bật phân biệt luồng | `SketchEnabled` | true |

Bốn dòng cuối là **attribute**: thêm tiền tố `--ns3::SpieQueueDisc::`. Với các tham số điều khiển chung, đổi ở **cả hai** lớp khi so sánh. Các giá trị khởi đầu là `A=0.125`, `B=1.25`, `QueueDelayReference=5ms`, `Tupdate=30ms`, `DequeueThreshold=10000` byte, `MaxBurstAllowance=100ms` và `UseDequeueRateEstimator=true`. Hệ số EWMA của bộ ước lượng giữ nguyên 0,5 trong mã PIE 3.45. Ví dụ thay MSS qua `--ns3::TcpSocket::SegmentSize=1200`. MSS và `payload` là hai tham số riêng.

## Đọc mã thuật toán

Trong `spie-queue-disc.cc`, bắt đầu ở `DoEnqueue`, sau đó đọc `ReadFlowKey`, `Estimate`, `AboveThreshold`, `RecordAccepted` và `ResetWindow`. Các phần điều khiển xác suất, burst và đo tốc độ dequeue được giữ từ `PieQueueDisc` của tag ns-3.45; vì thế số hạng sai số điều khiển dùng trễ hiện tại theo mã ns-3.45. Tệp `spie-queue-disc.h` khai báo trạng thái và đơn vị của các biến.

1. Nếu qdisc vượt giới hạn khi nhận gói, loại vì đầy.
2. Nếu chưa đủ dữ liệu hoặc trễ dưới `QueueDelayReference / DelayDivisor`, gọi logic PIE. Với bộ ước lượng tốc độ đã bật, dùng trễ mà controller cập nhật theo `Tupdate`.
3. Trong nhánh Sketch, lấy giá trị nhỏ nhất qua các hàng cho từng khóa. So sánh nghiêm ngặt `c_k × Σc_i > Σc_i²`, tương đương công thức tỷ trọng khi cùng chia cho M. Bằng ngưỡng thì nhận. Tên lý do loại là `Sketch large-flow drop`.
4. Chỉ sau khi hàng đợi nội bộ nhận thành công mới tăng các ô và M. Timer xóa đồng thời các ô, tập khóa và M. Khóa gồm hai địa chỉ IPv4, giao thức và hai cổng, giữ hướng truyền. Gói phân mảnh hoặc ngoài IPv4 TCP/UDP quay về PIE.

Chi phí mảng đếm là `8 × SketchRows × SketchWidth` byte. Tập khóa cần thêm bộ nhớ theo số luồng. Tính ngưỡng trực tiếp cần truy vấn từng khóa trong cửa sổ. Kích thước CMS, thời gian reset, phân phối ON/OFF và các override controller là lựa chọn triển khai của nhóm.

## Kiểm tra PIE nền

```bash
./ns3 run "s-pie --aqm=Pie --RngRun=1 --events=pie-events.csv --output=pie.csv"
./ns3 run "s-pie --aqm=Spie --RngRun=1 --ns3::SpieQueueDisc::SketchEnabled=false --events=off-events.csv --output=off.csv"
cmp pie-events.csv off-events.csv
cmp pie.csv off.csv
```

CSV sự kiện lưu thời điểm ns, loại sự kiện, UID và kích thước gói. CSV goodput có một dòng mỗi giây cho mỗi luồng, kể cả luồng không nhận byte. Có thể tính Jain theo từng giây từ cột goodput, với đủ số luồng; nếu cả cửa sổ bằng 0 thì trả NA. Các bộ đếm của qdisc in sau khi mô phỏng kết thúc, bao gồm 5 giây xả hàng đợi. CSV goodput kết thúc tại thời điểm nguồn dừng. Các CSV bổ sung dưới đây dùng chung tiền tố với tệp goodput.

## Tệp kết quả và cách thống kê

Ví dụ chọn `--output=s1-spie.csv`. Thư mục chứa tệp phải tồn tại. Dùng tiền tố riêng cho mỗi run để lưu đủ bộ.

| Tệp | Đơn vị quan sát và cách sử dụng |
|---|---|
| `s1-spie.csv` | Byte payload và Mbps từng luồng, từng giây phát. Cộng theo nhóm để so nhóm nhỏ/lớn ở kịch bản 1. |
| `s1-spie-queue.csv` | Occupancy của qdisc chiều Router1 → Router2 sau mỗi enqueue/dequeue, theo gói và byte. Có trạng thái ban đầu và mốc kết thúc. Lấy tổng `Q × thời gian duy trì Q` chia cho độ dài cửa sổ. |
| `s1-spie-rtt.csv` | ID luồng, thời điểm và giá trị ns của mỗi **thay đổi** LastRTT (mẫu RTT) hoặc RTT (SRTT). Tách hai chuỗi khi thống kê. Luồng không có mẫu trong cửa sổ không có RTT trung bình. |
| `s1-spie-drops.csv` | Mỗi sự kiện loại gói ghi vị trí, lớp, giai đoạn xử lý, lý do gốc, UID và kích thước. Lọc `core-forward,qdisc` để lấy drop của thuật toán. PIE/S-PIE dùng `Forced drop` cho tràn hàng; với RED, forced là quyết định AQM, còn tràn hàng ở cấu hình này mang lý do `Dropped by internal queue`. CoDel tách `Overlimit drop` và `Target exceeded drop`. |
| `s1-spie-link.csv` | Mỗi khung bắt đầu phát trên bottleneck chiều đi: thời gian, phase, wire_bytes, flow, group, IP nguồn/đích, giao thức và cổng. Gồm header, TCP control và tái truyền. Throughput = tổng byte / thời gian / 10^6 (10^6 byte/s), hoặc nhân thêm 8 để ra Mbps. Khung cắt biên được tính trọn tại thời điểm bắt đầu phát. Gói chưa nhận diện có flow=0, group=unknown. |
| `s1-spie-config.csv` | Kịch bản, seed/run, tốc độ, thời gian, phân phối ON/OFF, tham số qdisc/TCP/Sketch và ánh xạ `flow.<id>.*` được đăng ký trong lần chạy. |

Trong các trace có cột `phase`, thời điểm từ 0 đến trước khi nguồn dừng thuộc `traffic`; các sự kiện tại và sau mốc dừng thuộc `drain`. CSV goodput vẫn chỉ chứa các cửa sổ phát. Để tổng hợp bằng Python chuẩn, chạy từ thư mục gốc ns-3:

```bash
python3 scratch/s-pie/summarize.py s1-spie.csv > s1-spie-summary.csv
python3 scratch/s-pie/summarize.py s1-spie.csv --start 5 --end 20
```

Chương trình tính Jain từ tổng byte **từng luồng trong khoảng đã chọn**, gồm cả luồng 0 byte. Để vẽ chuỗi Jain từng giây, chọn lần lượt từng khoảng 1 s. Trung bình RTT trong tệp tổng hợp đặt trọng số bằng nhau cho mỗi sự kiện thay đổi. Dùng dữ liệu thô theo flow nếu cần đặt trọng số bằng nhau cho mỗi luồng. Khi làm thống kê nhiều lần lặp, tính chỉ tiêu cho từng run trước rồi mới tổng hợp giữa các run.

## Kiểm chứng bản bàn giao ban đầu

Các kết quả dưới đây là lịch sử kiểm chứng bản ban đầu, không xác nhận mọi chỉnh sửa trace/batch sau đó đã được build lại trên NS-3. Các sửa đổi thu trace gần đây cần được build trong môi trường mô phỏng thực tế.

Đã build với Clang 20.1.3 trên Windows từ tag ns-3.45. Cả tám tổ hợp của hai kịch bản và bốn thuật toán chạy hết với 100 luồng, 30 s phát và 5 s xả hàng đợi, một run cho mỗi tổ hợp.

Ở kịch bản 1, PIE gốc và S-PIE tắt Sketch cho hai CSV sự kiện giống nhau từng byte (SHA-256 `c97d64515ea1d3d689b7d7161a73ebadc6e2aaade5d84ff368747a7e587bf1e5`). Hai CSV goodput cũng giống nhau từng byte. Trong phép thử riêng với bảng 1 hàng × 1 ô, reset 250 ms, thời gian phát 8 s, tất cả luồng có ước lượng bằng nhau. Qdisc nhận 54.544 gói, nhận vào hàng 52.833 gói và loại 1.711 gói vì đầy; số loại do Sketch bằng 0.

## Batch nhiều run và chạy song song (cập nhật)

`run-simulation.sh` hiện dùng cấu hình batch thay cho `SCENARIO` và `RNG_RUN` đơn lẻ:

```bash
SCENARIOS=(1 2)
RNG_RUNS=(1 2 3)
MAX_PARALLEL=2
ALGORITHMS=(Spie Pie Red CoDel)
RNG_SEED=1
RESULT_DIR="result"
OVERWRITE=false
```

Mặc định: 2 scenario × 3 run × 4 AQM = 24 mô phỏng, tối đa 2 job cùng lúc. Mỗi job là một scenario/run/AQM; thuật toán của cùng run dùng chung seed/run. Giữ HASH_SEED cố định nếu chỉ đánh giá biến thiên traffic/drop. Chọn MAX_PARALLEL theo CPU/RAM/dung lượng ghi trace; đặt 1 để chạy tuần tự. Cần Bash >=4.3 trên Ubuntu/WSL.

Từ gốc NS-3.45, sau khi chép lại thư mục s-pie vào scratch:

```bash
bash scratch/s-pie/run-simulation.sh --dry-run
bash scratch/s-pie/run-simulation.sh
```

Script kiểm tra danh sách và kết quả trùng trước khi configure/build một lần. Mỗi job gọi `ns3 run --no-build` để tránh các tiến trình cùng build cây nguồn. Output:

```text
result/scenario_1_run_1/Spie/s1-Spie-seed1-r1.csv
result/scenario_1_run_1/Spie/s1-Spie-seed1-r1.log
result/scenario_1_run_1/Pie/...
result/scenario_1_run_2/Spie/...
result/scenario_2_run_3/CoDel/...
```

CSV trace và summary nằm cùng thư mục thuật toán. Log chứa lệnh thực tế, stdout/stderr và summary. Job lỗi làm batch trả mã lỗi sau khi chờ các job đã lên lịch; xem log tương ứng, không sử dụng kết quả dở dang. OVERWRITE=false chặn chạy đè bất kỳ CSV cùng tiền tố; tăng run mới hoặc chủ động đặt true khi cần chạy lại. Không chạy hai bản script cùng ghi vào một tập scenario/seed/run. Đổi RESULT_DIR khi khảo sát bộ tham số khác; tên thư mục run không chứa seed nên dùng result root riêng khi đổi seed nếu cần tách biểu đồ theo seed.

Để chạy 10 lần mỗi scenario, đặt `RNG_RUNS=(1 2 3 4 5 6 7 8 9 10)`. Để chỉ chạy scenario 1, đặt `SCENARIOS=(1)`.

Chép result về data/result của dự án rồi vẽ:

```powershell
python plots/plot_results.py --data data/result
```

Mỗi thư mục scenario/run sẽ có thư mục hình tương ứng trong plots/output.

Đã kiểm tra phần điều phối bằng wrapper NS-3 giả qua test_batch_runner.py (không thay thế build/chạy NS-3 thật): dry-run, 24 job/6 folder, giới hạn song song, build một lần, chặn ghi đè và báo job lỗi.

## Điều khiển batch bằng dòng lệnh

Các tùy chọn dòng lệnh ghi đè cấu hình đầu file cho lần gọi hiện tại:

```bash
# 10 run cho mỗi kịch bản, tối đa 4 mô phỏng chạy đồng thời
bash scratch/s-pie/run-simulation.sh --runs 10 --parallel 4

# Kịch bản 1, 5 run bắt đầu từ run 4: run 4,5,6,7,8
bash scratch/s-pie/run-simulation.sh --scenario 1 --runs 5 --start-run 4 --parallel 2

# Chỉ kiểm tra lệnh, không build/chạy
bash scratch/s-pie/run-simulation.sh --scenario 2 --runs 3 --dry-run

# Chọn nơi lưu kết quả
bash scratch/s-pie/run-simulation.sh --runs 2 --result-dir result_new

bash scratch/s-pie/run-simulation.sh --help
```

`--runs N` là số run trên mỗi scenario, mỗi run chạy đủ ALGORITHMS. Nếu chọn cả hai scenario và bốn AQM, --runs 10 tạo 80 job. `--start-run` mặc định 1 khi chỉ định số run; nếu chỉ đặt --start-run thì dùng số phần tử RNG_RUNS đã cấu hình làm số run. Không truyền cả hai tùy chọn thì giữ nguyên danh sách RNG_RUNS trong file. `--scenario` nhận 1, 2 hoặc both; bỏ qua tùy chọn này thì giữ SCENARIOS trong file. Hỗ trợ cả --runs 5 và --runs=5.

Ví dụ --scenario 1 --runs 2 --start-run 4 tạo result/scenario_1_run_4/ và result/scenario_1_run_5/. Giữ cùng seed và tham số giữa các run. Kết quả đã có vẫn được bảo vệ bởi OVERWRITE=false; --start-run giúp tiếp tục các run mới mà không sửa file.
