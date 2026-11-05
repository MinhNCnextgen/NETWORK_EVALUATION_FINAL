# Quyết định và đề xuất triển khai ngày 02/11/2026

> Cập nhật theo chỉ định mới của người dùng: dùng NS-3.45. Tài liệu `ns345_update.md` trong cùng thư mục là căn cứ hiện hành cho phiên bản, API, mặc định và cách triển khai. Các phần nhắc NS-3.27 bên dưới chỉ còn là lịch sử đối chiếu; không dùng controller 3.27 làm nền triển khai chính.

## Đã chốt theo người dùng

- Trong nhánh phân biệt luồng, drop nếu G_k > G_threshold. Bằng ngưỡng được enqueue nếu hàng đợi còn chỗ. Hoãn thí nghiệm đảo dấu; không chạy mặc định biến thể dấu <.
- Cần cấu hình hóa các tham số để khảo sát nhiều giá trị sau này.
- Các giá trị sau đây là đề xuất của trợ lý, chưa qua thí nghiệm, không được gọi là tối ưu hoặc cấu hình gốc của tác giả.

## Bộ khởi đầu đề xuất

Giữ topology và tải của Table 1: 100 cặp nguồn–đích; access 100Mbps/5ms; bottleneck 50Mbps/20ms; NewReno; queue disc 50 packet; hai kịch bản tải như bài báo. Ưu tiên NS-3.27 để gần nguồn; nếu cần port thì phải ghi rõ phiên bản thực tế.

### PIE và bộ điều khiển nền S-PIE

- QueueDelayReference 5ms, khảo sát 5/10/20ms. Đây là điều chỉnh có chủ đích so với mặc định NS-3.27 20ms. Hàng đợi 50 x khoảng 1000 byte ở 50Mbps chỉ chứa khoảng 8ms dữ liệu; cần tính lại với packet size thực tế gồm header. Với ref20ms thì ngưỡng phân biệt ref/3=6,67ms chỉ kích hoạt gần đầy.
- Tupdate 30ms, khảo sát 10/20/30ms; Supdate 0s.
- A=0,125; B=1,25; khảo sát theo cặp (0,0625;0,625), (0,125;1,25), (0,25;2,5), sau đó tách nếu cần.
- DequeueThreshold 10000 byte; khảo sát 5000/10000/20000 byte. Không đánh đồng với ngưỡng trễ hoặc queue limit 50 packet.
- epsilon=0,5, khảo sát 0,125/0,25/0,5. NS-3.27 hard-code EWMA 0,5; nếu mở thành tham số thì áp dụng cho cả PIE và S-PIE.
- MaxBurstAllowance 100ms, khảo sát 0/50/100ms; dùng cùng controller PIE ở hai thuật toán. Quy tắc burst của PIE áp dụng nhánh PIE và cách tính p; không tự dùng để miễn mọi drop luồng lớn trong nhánh Sketch.
- Ước lượng delay theo byte queue / byte dequeue rate, không trộn packet và byte. Nếu estimator chưa có số liệu thì bỏ qua quyết định Sketch và dùng xử lý khởi tạo PIE.
- Bộ điều khiển chính đề xuất dùng CalculateP của NS-3.27 cho cả PIE và S-PIE: sai số alpha dựa del_cur, có gain scaling và cơ chế burst. Khác với Eq3 paper in del_old phải ghi rõ như một diễn giải triển khai. Không viết Eq3 paper rồi khẳng định chạy nguyên công thức khi code dùng phiên bản này. Biến thể Eq3 nguyên bản là phép khảo sát riêng về sau.
- Phân biệt trạng thái điều khiển drop nội bộ của implementation với xác suất hiệu dụng dùng so U[0,1); không tự clamp trạng thái p của PIE chuẩn nếu làm thay đổi hành vi. Mọi mở rộng clamp phải áp dụng chung và công bố.

### Sketch

- CMS d=4, w=1024, bộ đếm uint64_t: 32KiB riêng mảng đếm. Khảo sát d=3/4/5, w=256/512/1024/2048.
- Reset cứng mỗi 0,5s; khảo sát 0,1/0,25/0,5/1s. Reset đồng bộ counters, M và tập key. Dùng sự kiện thời gian, không vòng while từ mã giả.
- Khóa 5-tuple có hướng; mỗi gói được chấp nhận +1, query trước insert; không cộng lại khi dequeue; gói drop không được cập nhật. Đây là lựa chọn theo Algorithm2, không phải điều bài báo mô tả nhất quán.
- M đếm số packet được insert, không phải tổng mọi bucket ở d hàng.
- G_i=c_hat_i/M. G_threshold=sum_i(c_hat_i*G_i)/sum_i(c_hat_i), tính trên tập key đã có packet được chấp nhận trong cửa sổ. Không rút gọn thành sum(c_hat_i^2)/M^2 khi có collision.
- Duy trì tập key phân biệt và query mỗi key để tính ngưỡng trước mỗi quyết định là reference implementation minh bạch cho 100 flow. Chi phí thêm O(F) bộ nhớ key và O(F*d) truy vấn mỗi quyết định; không khẳng định chỉ tốn 32KiB hoặc thời gian hằng số. Bảng đếm chính xác chỉ phục vụ kiểm chứng CMS, không thay cho CMS trong kết quả chính.
- Hash dùng họ băm có seed theo từng hàng, deterministic theo run; khi viết code phải chọn và ghi rõ họ/hàm cùng seed. Hash streams tách traffic/drop, giữ cùng hash seeds giữa các cấu hình so sánh trong một run. Chưa chốt tên hàm cụ thể khi chưa kiểm tra API/code.
- M=0: fallback PIE cho tới khi có dữ liệu; không tự thêm min-sample gate hoặc pseudocount. Theo dõi thiên lệch đầu cửa sổ; nếu sửa bằng min-sample gate phải là biến thể riêng có công bố.
- Nhánh Sketch khi có estimator và M hợp lệ: delay >= ref/3, drop lớn nếu > ngưỡng, còn lại enqueue nếu chưa full; không thêm một lần random drop p nữa trong nhánh này. Queue full luôn drop trước.

### Đối chứng

- RED: packet mode, limit50, MinTh5, MaxTh15, QW0,002, LInterm50 (maxP ban đầu 1/50), Gentle=true, Wait=true; ARED/AdaptMaxP/FengAdaptive/NLRED=false; LinkBandwidth50Mbps, LinkDelay20ms; MeanPktSize phù hợp kích thước đo thực tế. Khảo sát (5,15)/(10,30), QW 0,001/0,002/0,004, maxP 0,02/0,05/0,1. Cấp cơ hội khảo sát cho đối chứng trước khi tuyên bố ưu thế S-PIE.
- CoDel: Target5ms, Interval100ms, MinBytes1500, packet mode limit50; khảo sát Target2/5/10ms, Interval50/100/200ms. Đã xác minh giá trị Target/Interval/MinBytes trong tài liệu chính thức; tên attribute giới hạn thay đổi giữa các version, phải theo bản build.
- ECN tắt ở TCP và các queue hỗ trợ; dữ liệu so sánh chính dựa drop.

### Traffic và phép đo

- Đề xuất PacketSize OnOff1000 byte, TCP MSS1000 byte, MTU1500. PacketSize ứng dụng không đảm bảo một segment tương ứng một lần Send; trace size thực tế để đặt MeanPktSize và tính delay.
- OnTime và OffTime độc lập phân phối exponential, mean mỗi loại1s; cùng phân phối ở hai kịch bản. Duty cycle kỳ vọng0,5. Đây là giả định vì paper không công bố, không phải tham số của tác giả. Khảo sát thêm meanOn1s/meanOff0,1s, và nguồn liên tục là đối chứng traffic riêng.
- Nguồn start Uniform[0;0,1]s, stop30s; sinks start0; simulator stop35s để drain. Đo chính [0,30]s, xuất riêng [0,20]s và [5,20]s; không đưa 5s drain vào throughput chính. Đảm bảo sink được lập lịch trước source nếu cùng timestamp0.
- Device queue bottleneck1 packet, có flow control, trace để xác nhận không có drop thiết bị ngoài chủ ý; reverse bottleneck ACK queue FIFO limit50, không cài AQM thứ hai; access queues FIFO cố định100 packet và trace drop riêng. Không để queue mặc định lớn che tác động queue disc50.
- Chốt và xuất các thuộc tính TCP thực tế như InitialCwnd, DelAckCount/Timeout, SndBuf/RcvBuf, MSS và ECN. Không giả vờ paper quy định các giá trị không nêu; cần kiểm tra version trước khi điền config hoàn chỉnh.
- Goodput Mbps tại sink cửa sổ1s; Jain trên100 flow với cùng cửa sổ (cả flow0), NA nếu mọi flow0; queue trace theo event và trung bình thời gian; RTT TCP socket trace, ghi rõ cách tổng hợp; drop phân loại theo reason thực, không đồng nhất forced RED với overflow.
- 10 run độc lập/config ban đầu; cùng run traffic giữa thuật toán; CI95% giữa run. Các mô phỏng điều chỉnh tham số trước dùng3 run sàng lọc, xác nhận lại10 run và tập seed bổ sung nếu chọn cấu hình theo kết quả.

## Thứ tự khảo sát

Kiểm tra logic -> 8 cấu hình lõi (2 scenario x4 algorithm) -> ưu tiên ref, reset window, w -> khảo sát controller và đối chứng -> tương tác ref x reset và w x d khi có bằng chứng cần. Tránh tích Descartes toàn bộ tham số. Chọn cấu hình dựa đánh đổi fairness/delay/goodput/drop, không chỉ một metric hoặc khớp figure paper.

## Xử lý sai lệch công bố

- Giữ limit50 ở chính, không nâng queue để ép số queue >50. Chạy limit100 là độ nhạy bổ sung nếu cần. Nêu không thể có trung bình occupancy>50 của chính queue bị chặn50; chưa kết luận nguyên nhân sai ở paper.
- Báo cáo q(t), mean thời gian và EWMA riêng; không coi chúng tương đương. Mbps từ byte, không dùng packet/s rồi gắn Mbps. RTT không lấy one-way delay.
- Phần trăm tính lại từ số gốc; ghi rõ số tác giả và số tính lại khi có khác biệt.
- Không đo thời gian CPU simulator như độ trễ xử lý thực của router: chi phí tính toán C++ không tự trở thành thời gian mô phỏng. Báo cáo chi phí CPU/memory riêng nếu đánh giá overhead.
- Luồng small/large là nhóm DataRate cấu hình, khác phân loại tần suất động của Sketch; không dùng nhãn nhóm để oracle-drop.

## Nguồn web đã kiểm tra

- https://www.nsnam.org/docs/release/3.27/doxygen/pie-queue-disc_8cc_source.html : defaults, EWMA0,5, byte-based estimator, controller current-delay error, gain scaling, burst.
- https://www.nsnam.org/docs/release/3.27/doxygen/red-queue-disc_8cc_source.html : RED attributes/defaults.
- https://www.nsnam.org/docs/models/html/codel.html : Target5ms, Interval100ms, MinBytes1500 và cơ chế CoDel.
- https://www.nsnam.org/docs/models/html/pie.html : estimator default chuyển sang timestamp từ ns-3.32, nên không dùng ngầm default bản mới cho tái hiện bản cũ.

Chưa sửa Word và chưa chạy mô phỏng. Người dùng mới chốt rõ dấu >; các đề xuất còn lại phải được gọi đúng là đề xuất khi viết báo cáo.
