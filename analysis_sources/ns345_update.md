# Cập nhật thiết kế thí nghiệm cho NS-3.45

Ngày 02/11/2026. Người dùng đã chốt dùng NS-3.45. Tài liệu này thay thế những nhận định về phiên bản/API trong ghi chú trước. Không sửa DOCX; chưa cài đặt, build hoặc chạy NS-3.

## Căn cứ đã xác minh

Đọc tài liệu chính thức version3.45 về TCP, QueueDisc và cài đặt; tải và kiểm tra trực tiếp 12 file từ mirror chính thức nsnam/ns-3-dev-git, tag ns-3.45. Các bản nguồn nằm trong thư mục `ns-3.45` cạnh tài liệu này. Tên file giữ đường dẫn nguồn bằng cách thay / bằng __. Manifest SHA256 ghi riêng để kiểm tra bản lưu.

Nguồn chính:

- https://github.com/nsnam/ns-3-dev-git/tree/ns-3.45
- https://raw.githubusercontent.com/nsnam/ns-3-dev-git/ns-3.45/src/traffic-control/model/pie-queue-disc.cc
- https://raw.githubusercontent.com/nsnam/ns-3-dev-git/ns-3.45/src/traffic-control/model/pie-queue-disc.h
- https://raw.githubusercontent.com/nsnam/ns-3-dev-git/ns-3.45/src/traffic-control/model/red-queue-disc.cc
- https://raw.githubusercontent.com/nsnam/ns-3-dev-git/ns-3.45/src/traffic-control/model/codel-queue-disc.cc
- https://raw.githubusercontent.com/nsnam/ns-3-dev-git/ns-3.45/src/internet/model/tcp-socket.cc
- https://raw.githubusercontent.com/nsnam/ns-3-dev-git/ns-3.45/src/internet/model/tcp-socket-base.cc
- https://raw.githubusercontent.com/nsnam/ns-3-dev-git/ns-3.45/src/internet/model/tcp-l4-protocol.cc
- https://www.nsnam.org/docs/release/3.45/models/html/tcp.html
- https://www.nsnam.org/docs/release/3.45/models/html/queue-discs.html
- https://www.nsnam.org/docs/release/3.45/installation/html/quick-start.html

Trang models PIE/RED/CoDel có version3.45 không truy cập được bằng web tool trong phiên này; đã dùng mã nguồn gắn tag chính xác thay thế, không lấy mặc định từ trang latest. Các tài liệu latest hoặc 3.27 đã dẫn trước đây không còn là căn cứ cho defaults hiện tại.

## Những thay đổi quan trọng

### PIE defaults thực tế

| Attribute | Mặc định NS-3.45 | Cấu hình thí nghiệm đề xuất hiện hành |
|---|---|---|
| MaxSize | 25p | 50p theo paper |
| A | 0.125 | 0.125 |
| B | 1.25 | 1.25 |
| Tupdate | 15ms | 30ms, override chủ động; khảo sát10/15/20/30ms |
| Supdate | 0s | 0s |
| DequeueThreshold | 16384 byte | 10000 byte, override; khảo sát5000/10000/16384/20000 |
| QueueDelayReference | 15ms | 5ms, override; khảo sát5/10/15/20ms |
| MaxBurstAllowance | 150ms | 100ms, override; khảo sát0/50/100/150ms |
| MeanPktSize | 1000 byte | Ban đầu1000; kiểm tra actual QueueDiscItem size |
| UseDequeueRateEstimator | false | true để dùng byte backlog / byte departure rate |
| UseCapDropAdjustment | true | true |
| UseDerandomization | false | false |
| UseEcn | false | false |
| UseL4s | false | false |
| ActiveThreshold | Time::Max() | Time::Max(): vô hiệu cổng kích hoạt tùy chọn |
| CeThreshold | Time::Max() | Time::Max() |
| MarkEcnThreshold | 0.1 | Không tác động khi UseEcn=false |

Giữ các tham số khởi đầu đã đề xuất trước để thay đổi phiên bản không đồng thời làm thay đổi mọi lựa chọn thí nghiệm; các giá trị khác default đều phải set explicit. Bộ mặc định NS-3.45 là cấu hình tham khảo riêng có thể chạy thêm, không gọi cấu hình override là default.

NS-3.45 mặc định tính delay bằng thời gian lưu gói đo ở dequeue. Muốn gần công thức4–6 paper phải đặt UseDequeueRateEstimator=true cho cả PIE và S-PIE. Hai cách ước lượng là hai biến thể thí nghiệm riêng. Với rate estimator, m_qDelay được cập nhật trong CalculateP theo Tupdate, không phải luôn là delay hiện thời ở mỗi arrival; log cả delay điều khiển và sojourn đo thực để tránh nhầm.

EWMA của rate estimator vẫn hard-code0.5; không có attribute Epsilon. Ở bộ chính giữ0.5 để PIE đối chứng là implementation chuẩn. Nếu khảo sát epsilon khác cần mở tham số trong cả hai implementation có kiểm chứng, ghi là phiên bản tùy biến; không quảng cáo có thể set Config::SetDefault("...Epsilon") trong mã chuẩn.

Controller3.45 dùng current delay ở số hạng A, có gain scaling ở các vùng xác suất nhỏ, cap adjustment, decay, burst và chặn m_dropProb trong[0,1]. Do đó ghi chú cũ về không tự clamp state để giữ hành vi3.27 không áp dụng cho3.45: giữ nguyên clamp của code3.45. Không ghép estimator3.45 với controller3.27 hoặc công thức paper rồi gọi đó là PIE chuẩn.

Rule Gk>Gthreshold vẫn đã chốt. S-PIE dùng cùng controller3.45, chỉ bổ sung thống kê và nhánh lựa chọn drop. Những khác biệt với công thức3 paper phải được mô tả là cách diễn giải triển khai.

### Queue API và S-PIE implementation

- Dùng MaxSize và QueueSizeValue(QueueSize("50p")) cho PIE, RED, CoDel và S-PIE. Bỏ Mode/QueueLimit/MaxPackets/MaxBytes cũ. Đơn vị packet được xác định bởi suffix p.
- Cài đúng root QueueDisc ở thiết bị Router1 hướng Router2. Mỗi netdevice có một root qdisc; kiểm tra queue đã tồn tại trước Install, chỉ Uninstall ở đúng device khi cần. Không Install đại trà cả hai hướng.
- Device queue bottleneck1p là cấu hình đề xuất riêng, không phải limit của qdisc. Theo dõi flow control và drop ở queue thiết bị. Khai báo rõ cấu hình các queue reverse/access để tránh qdisc tự động hoặc queue mặc định lớn che ảnh hưởng.
- Header PieQueueDisc3.45 đặt DoEnqueue, DoDequeue, CalculateP, DropEarly, InitializeParams và trạng thái controller ở private. Một subclass đơn giản không thể trực tiếp gọi những hàm hoặc sửa state này. Do đó không hứa chỉ kế thừa PieQueueDisc rồi thêm vài dòng.
- Đề xuất tạo SpiQueueDisc dẫn xuất QueueDisc dựa trên code PieQueueDisc3.45, giữ bản quyền và SPDX GPL-2.0-only, đổi TypeId/class và thêm CMS. Có switch SketchEnabled=false để kiểm chứng hành vi controller nền so với PieQueueDisc3.45 gốc. Không sửa hành vi đối chứng gốc một cách âm thầm.
- Nếu thực sự cần refactor shared controller sau này, làm riêng có kiểm chứng; trước mắt ưu tiên reference implementation dễ đối chiếu với tag3.45.
- Dùng DropBeforeEnqueue(item, reason) / DropAfterDequeue(item, reason) và hệ thống Stats chuẩn để counters/traces không thiếu. Có reason riêng cho SketchLargeFlowDrop, không tái dùng tên overflow.
- Theo code3.45 chữ ký CheckConfig() là bool không const; tài liệu overview QueueDisc có snippet const khác code thực tế, khi cài phải theo header/source.
- Hủy timer CalculateP và reset Sketch trong DoDispose. Sketch insertion chỉ sau internal Enqueue thành công; không đếm lại khi dequeue hoặc requeue. Giữ policy query-before-insert, reset đồng bộ0.5s và xử lý M=0 như ghi chú trước.

### TCP phải khóa cấu hình

Default3.45: congestion control TcpCubic, recovery TcpPrrRecovery, InitialCwnd10 segment. Vì paper nêu NewReno, bắt buộc set TcpL4Protocol::SocketType=TcpNewReno trước tạo stack/socket.

Đề xuất bộ chính: NewReno + PRR + InitialCwnd10, dùng chung mọi AQM; ghi đầy đủ ba lựa chọn. Đây là NewReno trên stack3.45, không đồng nhất với toàn bộ stack3.27. Đối chứng độ nhạy: InitialCwnd1 và classic recovery nếu cần nghiên cứu ảnh hưởng môi trường cũ; không đổi recovery/cwnd chỉ cho S-PIE.

Các default khác đã xác minh để set/log explicit:

- TcpSocket::SegmentSize536 byte -> override1000 như đề xuất.
- TcpSocket::SndBufSize/RcvBufSize131072 byte mỗi loại -> giữ128KiB cho bộ đầu và theo dõi backlog; không tăng lên buffer nhiều MiB tùy tiện vì làm mờ ON/OFF ở TCP output.
- TcpSocket::DelAckCount2, DelAckTimeout200ms -> giữ.
- TcpSocketBase::Sack=true, Timestamp=true -> giữ; UseEcn enum Off.
- TcpSocket::TcpNoDelay=true -> giữ.
- Không gọi BooleanValue(false) cho TcpSocketBase::UseEcn vì đây là enum; dùng EnumValue(TcpSocketState::Off).
- Set trước khi tạo socket; lưu actual attributes và build configuration vào manifest mỗi batch.

### RTT và traffic đo chính xác hơn

- Trong3.45, TcpSocketBase trace RTT = smoothed RTT (SRTT). LastRTT = RTT của gói được(S)ACK gần nhất. Đề xuất LastRTT cho chuỗi mẫu chính, RTT/SRTT lưu bổ sung. Không gọi LastRTT là phép đo đầy đủ mọi packet; callback TracedValue chỉ phát khi giá trị đổi, cần nói rõ nếu thống kê trên sự kiện trace.
- Nếu cần trung bình toàn bộ estimator samples kể cả giá trị bằng nhau liên tiếp, phải thêm instrumentation tại điểm cập nhật mẫu hoặc xác định cách đo riêng, không suy ra từ số callback LastRTT.
- SocketList trong TcpL4Protocol là map, không giả định socket đầu luôn index0. Kết nối trace tới socket nguồn thực và ghi flow ID; xác nhận callback đã gắn thành công, bao gồm giai đoạn đầu.
- OnOff3.45 sau khi kết nối thành công lập lịch qua OffTime trước lần On đầu. StartTime không bằng lúc data bắt đầu; jitter start0–0.1s và OffTime1s tạo thêm độ trễ đầu flow. Ghi lại thời điểm kết nối/lần gửi đầu, không diễn giải cả100 flow đều phát data tại t=0.
- OnOff gửi vào TCP buffer; OFF ứng dụng không bảo đảm link lập tức ngừng vì buffer còn dữ liệu. Giữ source ON/OFF chuẩn trước, đo application Tx và queue arrivals để kiểm tra burst thực tế.
- PacketSize ứng dụng1000 byte/MSS1000 không đồng nghĩa queue item1000 byte; header TCP timestamp/IP và packet nhỏ có thể thay đổi size. Ước lượng8ms queue trước đây là xấp xỉ, cần tính lại actual size.

### Drop và kiểm tra bảo toàn

- PIE3.45 FORCED_DROP là queue limit, UNFORCED_DROP là xác suất chủ động.
- RED forced drop do vượt ngưỡng trung bình vẫn là AQM chủ động, không tự gán overflow. Queue đầy có thể báo QueueDisc::INTERNAL_QUEUE_DROP.
- CoDel drop theo target là AQM chủ động ở dequeue, tách với overflow.
- Không dùng tên reason chung hoặc chỉ before/after enqueue để quyết định active/passive; ánh xạ theo từng algorithm và actual reason.
- Theo thống kê QueueDisc3.45: received = droppedBeforeEnqueue + enqueued; queued = enqueued - dequeued; dropped = droppedBeforeEnqueue + droppedAfterDequeue; sent = dequeued - droppedAfterDequeue, điều chỉnh gói requeued nếu có. Không trừ droppedAfterDequeue lần nữa trong công thức occupancy (dequeued đã bao gồm chúng). Đây là sửa đổi so với công thức sơ bộ ở ghi chú chuẩn bị.
- Dùng PacketsInQueue/BytesInQueue, SojournTime và reason traces/Stats; SojournTime bao gồm các gói dequeue rồi drop/requeue và không gồm thời gian giữ lại sau requeue. Chọn tập gói cần báo cáo rõ ràng.

## Build và kiểm chứng trước mô phỏng chính

NS-3.45 dùng CMake và wrapper ./ns3, không dùng ./waf. Quick-start version này yêu cầu GCC>=10 hoặc Clang>=11, Python>=3.8, CMake>=3.13 và make/ninja/Xcode. Có thể dùng môi trường Linux/WSL trên máy Windows; chưa kiểm tra máy hiện tại có NS-3/WSL hay chưa.

Lệnh dự kiến khi có source tree thật:

```bash
./ns3 configure --enable-examples --enable-tests
./ns3 build
./ns3 run "scratch/spie-experiment --help"
```

Tên scratch/spie-experiment là tên chương trình dự kiến, chưa tồn tại. Khi viết code phải thêm source/header vào CMake target tương ứng; không đưa file vào thư mục rồi giả định tự build. Chốt tag ns-3.45, commit và mọi patch tùy biến.

Thứ tự: build/tests nền -> kiểm tra controller SpiQueueDisc khi SketchDisabled tương đương PIE chuẩn -> kiểm tra CMS và decision paths -> smoke run2 scenario -> batch so sánh và sensitivity. Chưa tiến hành các bước này ở lượt nghiên cứu tài liệu.

## Cách ghi vào báo cáo sau này

"Thí nghiệm sử dụng NS-3.45. Nhóm tái hiện cơ chế S-PIE trên bộ điều khiển PIE của phiên bản này, với quy tắc loại gói Gk>Gthreshold và bộ ước lượng trễ dựa trên tốc độ dequeue. Do bài báo sử dụng NS-3.27 và không công bố đầy đủ cấu hình, báo cáo trình bày riêng các tham số từ bài báo, các tham số kế thừa NS-3.45 và những lựa chọn bổ sung của nhóm."

Không khẳng định tái hiện nguyên trạng code tác giả hoặc toàn bộ môi trường3.27. So sánh trực tiếp bốn AQM trong cùng môi trường3.45 là kết quả chính; số công bố của paper là mốc đối chiếu có hạn chế.
