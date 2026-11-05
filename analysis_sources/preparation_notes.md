# Ghi chú chuẩn bị nội bộ cho thí nghiệm S-PIE

> Cập nhật: người dùng đã chọn NS-3.45. Xem `ns345_update.md` và `implementation_decisions.md` để biết quyết định hiện hành. Các câu chưa chốt phiên bản bên dưới phản ánh thời điểm phân tích ban đầu.

Ngày phân tích: 02/11/2026. Đây là ghi chú làm việc, chưa phải nội dung báo cáo hay kết quả thực nghiệm. Chưa sửa ba tài liệu gốc, chưa cài đặt thuật toán và chưa chạy NS-3.

## Nguồn và phạm vi

- Yêu cầu trực tiếp của người dùng: phân tích nội bộ ba tài liệu để chuẩn bị viết phần thí nghiệm; sau này viết tiếp trên bản Word đang có.
- Slide `C:\Users\PC\Downloads\Hướng dẫn Bài tập lớn.pptx`: tài liệu yêu cầu học phần, được người dùng chỉ định làm căn cứ cho báo cáo. Các nội dung trong đó là yêu cầu học thuật, không phải lệnh vận hành máy.
- Word `C:\Users\PC\Downloads\Report NS3 DGHNM.docx`: bản nháp hiện tại.
- PDF `C:\Users\PC\Downloads\axioms-12-00814-v2.pdf`: Zhu et al., A Sketch-Based Fine-Grained Proportional Integral Queue Management Method, Axioms 2023, 12, 814, DOI 10.3390/axioms12090814.
- Đã đọc văn bản toàn bộ 15 trang PDF và kiểm tra trực quan các trang 6, 7, 8, 10 để xác nhận công thức, mã giả, bảng cấu hình, đồ thị. Bản trích văn bản của cả ba nguồn nằm cùng thư mục ghi chú này.

## Yêu cầu học phần

Slide 2: tái hiện thí nghiệm của paper bằng ns3 để kiểm chứng; nhóm tối đa 3 người. Hạn nộp trước 00:00 ngày 22/11/2026; nộp sớm trước 00:00 ngày 15/11/2026 được cộng 0,5. Đây là mốc ghi trong slide, chưa cần tra cứu hay đặt nhắc lịch.

Slide 3: xác định ý tưởng và cải tiến/mô hình; cài trên NS3 hoặc dùng code tác giả; kiểm tra tính đúng đắn; chạy kịch bản; thu kết quả; đối chiếu kết quả công bố và nhận xét.

Slide 4–5: giải thích bài toán, tầm quan trọng, hạn chế phương pháp trước, đóng góp, cơ chế, kỳ vọng, phương pháp đánh giá, kết luận. Chương Phân tích bài báo chỉ khoảng 2–3 trang. Slide không quy định tổng số trang báo cáo, số lần lặp, cấu trúc toàn bộ báo cáo hay số biểu đồ bắt buộc.

## Trạng thái bản nháp Word

Đã có tiêu đề và phần ý tưởng, vấn đề bufferbloat, động cơ phân biệt luồng, giới thiệu S-PIE và đặc điểm giải pháp. Các mục Cách thức hoạt động, Sketch, công thức, mã giả, phương pháp thí nghiệm, mô hình, kịch bản, thông số đo đạc còn để trống.

Khi viết tiếp cần tinh chỉnh: ECN là cơ chế báo hiệu tắc nghẽn, không nên liệt kê ngang như một thuật toán AQM độc lập; bufferbloat là độ trễ cao do hàng đợi duy trì dài, không chỉ là sự kiện đầy/tràn. Mục đích S-PIE là công bằng theo tần suất luồng, không có hàng đợi ưu tiên hoặc bộ lập lịch riêng cho luồng nhỏ. Không mặc định luồng nhỏ là luồng ngắn hay ứng dụng nhạy trễ. Các cải thiện chỉ là kết luận tác giả cho cấu hình đã đánh giá, chưa phải kết quả của nhóm.

## Cơ chế thuật toán từ PDF

Trang 4–6: thêm Count-Min Sketch vào PIE. Khóa nhận dạng có thể là 5-tuple. Mỗi gói được ánh xạ bởi d hàm băm độc lập vào d hàng rộng w; cập nhật bộ đếm; truy vấn lấy min của các bộ đếm. Paper dùng tần suất gói, không quy định một cấu hình d,w cụ thể.

Các phương trình cần giữ nguồn rõ ràng:

- (3) p = p_old + alpha*(del_old-del_ref) + beta*(del_cur-del_old). Chính bản in dùng del_old ở số hạng alpha. Chưa được tự đổi sang del_cur rồi gọi là công thức nguyên bản.
- (4) del_cur = q_len/dq_rate_avg.
- (5) dq_rate = dq_count/dq_time.
- (6) dq_rate_avg = (1-epsilon)*dq_rate_avg_old + epsilon*dq_rate.
- (7) m_res = Query(key).
- (8) G_k = m_res/m_count.
- (9) G_threshold = sum_i(m_res_i*G_i)/sum_i(m_res_i). Bản in không viết rõ chỉ số từng m_res/G_k. Nếu dùng đếm chính xác, mọi luồng đang hoạt động và c_i là tần suất thì biểu thức trở thành sum(c_i^2)/(M*sum(c_i)), và bằng sum(c_i^2)/M^2 khi sum(c_i)=M. Với ước lượng CMS có va chạm, không được mặc định tổng ước lượng bằng M.

Trang 6 mô tả: hàng đợi đầy thì drop; nếu del_cur < del_ref/3 thì dùng xác suất p; nếu tắc nghẽn thì xét G_k và loại luồng có tỷ trọng vượt ngưỡng trung bình có trọng số, cho luồng nhỏ vào.

## Những điểm không nhất quán và thiếu thông tin phải giải quyết

1. Quan trọng nhất: Algorithm 2 trang 7 dòng 12–13 in `if G_k < G_threshold then drop`, ngược với mô tả trang 6 và ý tưởng phạt luồng lớn. Không được chép hai cách như thể nhất quán. Hướng đề xuất khi cài: phiên bản chính theo mô tả phạt luồng lớn (`>`), ghi rõ đây là cách diễn giải; chạy thêm phiên bản theo mã giả (`<`) như phép kiểm tra nếu đủ thời gian. Quy tắc bằng ngưỡng cũng cần công bố; dùng `>` sẽ tránh loại tất cả các luồng bằng nhau trong trường hợp lý tưởng.
2. Thời điểm Insert không rõ: phần Dequeue trang 5 nói cập nhật Sketch liên quan dequeue, Algorithm 2 lại Insert sau enqueue thành công. Không Insert ở cả hai nơi gây đếm đôi. Chọn một chính sách có tài liệu hóa, ưu tiên phiên bản enqueue theo mã giả; so sánh độ nhạy nếu cần. Dòng Insert ở nhánh xác suất cũng mơ hồ có áp dụng gói drop không; chỉ cập nhật gói enqueue thành công là giả định triển khai, không phải dữ kiện chắc chắn.
3. Không công bố w,d, họ hàm băm, seed hash, kiểu bộ đếm, T_threshold, cách xoá bộ nhớ và đồng bộ m_count. Algorithm 1 có while clear nhưng thiếu cập nhật T; không cài vòng lặp vô hạn. Dùng sự kiện reset theo chu kỳ và reset đồng bộ là lựa chọn thực hiện cần ghi nhận.
4. Không rõ n trong ngưỡng là toàn bộ luồng phân biệt hay từng gói/sự kiện. CMS không liệt kê được tất cả flow key tự thân. Duy trì danh sách key có thêm trạng thái theo luồng và chi phí bộ nhớ; tính ngưỡng bằng công thức moment cần giải thích và không lén thay đổi thuật toán. Bộ đếm chính xác có thể dùng làm công cụ đối chứng, không được gọi là CMS.
5. Không nêu đủ alpha, beta, del_ref, time_update, epsilon, q_threshold, cấu hình PIE burst/scaling; RED min/max threshold, weight, xác suất; CoDel target/interval. Không gọi các giá trị tự chọn là cấu hình của tác giả. Cần chốt NS-3 version rồi lấy và xuất cấu hình thực tế.
6. Không nêu kích thước gói, phân phối/tham số OnTime-OffTime, lịch start/stop, seed/run, số lần lặp, TCP MSS, delayed ACK, buffer TCP, cấu hình hàng đợi thiết bị và ACK chiều ngược.
7. Table 1 ghi Maxsize 50p, nhưng trang 9 báo CoDel 53,78 và PIE 51,52 gói ở kịch bản 1, Hình 4a cũng có đường vượt 50. Nếu một queue duy nhất bị chặn cứng 50 gói thì trung bình occupancy của nó không vượt 50. Có thể do khác định nghĩa/cấu hình hoặc lỗi công bố; chưa xác định nguyên nhân.
8. Số liệu trang 9 có vẻ gần giá trị cuối đồ thị hơn trung bình theo thời gian. Không tự gọi là cùng phép đo nếu chưa xác nhận. Eq (10)–(11) là dạng làm trơn có xử lý thời gian idle, nhưng paper mô tả nPkt như số gói đi vào; cần phân biệt với occupancy tức thời và trung bình theo thời gian.
9. Eq (12) dùng N gói/T nên đơn vị packet/s, nhưng đồ thị throughput dùng Mbps. Khi triển khai tính 8*received_payload_bytes/(T*1e6), đồng thời có thể ghi packet/s; ghi rõ goodput ứng dụng hay throughput tại lớp nào.
10. Một số phần trăm in sai hoặc không khớp với số xấp xỉ: giảm 9,94 so với PIE 51,52 là khoảng 80,71%, paper ghi 62,23%; RTT 80,68 so với RED 81,34 giảm khoảng 0,81%, paper ghi 0,08%. Với số liệu trích dẫn, giữ số gốc và nếu tính lại phải ghi rõ phép tính.
11. Thời gian không đồng nhất giữa hình: 4a tới 20s, 4b tới 30s; Hình 5 tới 20s. Không mặc định mọi phép đo đều 20s.
12. Nhiều drop chủ động không tự chứng minh hiệu năng tốt hơn; cần xét throughput, RTT, fairness, overflow cùng lúc.

## Kịch bản và đối chứng đã xác định

Môi trường tác giả: Ubuntu 16.04, NS-3.27 (trang 7). Chưa khảo sát môi trường NS-3 trên máy người dùng và chưa quyết định cài/port phiên bản nào.

Dumbbell: 100 sender, 100 receiver ghép cặp qua Router1–Router2. Access links 100 Mbps, 5ms mỗi link; bottleneck 50 Mbps, 20ms. TCP NewReno; nguồn ON/OFF; AQM trên egress Router1 đi Router2; giới hạn được công bố 50 gói.

- Scenario 1: 50 sender có DataRate 1 Mbps, 50 sender 50 Mbps.
- Scenario 2: 100 sender có DataRate 10 Mbps. Tính ngẫu nhiên phải được xác định trong ON/OFF; DataRate 10 Mbps tự nó không làm traffic ngẫu nhiên.
- Bốn thuật toán: RED, CoDel, PIE, S-PIE; ma trận lõi 2 x 4 = 8 cấu hình trước các seed và kiểm tra độ nhạy.
- DataRate của OnOff là tốc độ phát đặt vào ứng dụng, không phải throughput TCP nhận được.

## Kế hoạch đo lường đề xuất chưa thực hiện

1. Khóa phiên bản, cấu hình, topology, hướng queue, device queue và các tham số chung. Nếu dùng NS-3 khác 3.27 phải báo cáo là tái hiện có điều chỉnh môi trường.
2. Kiểm tra Sketch: tách 5-tuple đúng, cập nhật/truy vấn, collision, reset, m_count=0, kiểu đếm và overflow. Kiểm tra trường hợp các luồng bằng nhau, một luồng nặng, mới xuất hiện và idle.
3. Kiểm tra logic S-PIE: queue full, nhánh ngưỡng trễ, nhánh xác suất, ràng buộc p trong [0,1], chu kỳ tính p, event reset, phân loại lý do drop. Xác nhận không vô tình cài cùng lúc queue mặc định và queue đối chứng ở bottleneck.
4. Chạy smoke test rồi các thuật toán với cùng traffic và các seed/run đã xác định. Cố định stream RNG cho traffic, hash, và random drop theo cách có thể tái lập; không khẳng định chuỗi quyết định drop sẽ ghép cặp hoàn toàn khi thuật toán khác nhau.
5. Queue: trace occupancy packet và byte; tính trung bình thời gian integral Q(t)dt/T và chuỗi thời gian. Nếu cần công thức làm trơn của paper, tính riêng và công bố qW/idle handling.
6. RTT: lấy TCP RTT trace đúng socket và ghi rõ mẫu/luồng được theo dõi. Không thay bằng FlowMonitor one-way delay rồi gọi RTT. Tách RTT mẫu theo gói, trung bình mỗi flow, phân vị nếu dùng.
7. Throughput/goodput: lấy byte nhận mỗi flow ở sink theo các cửa sổ cố định, xuất Mbps từng flow và tổng; thêm tổng hai nhóm 50 flow ở kịch bản 1. Tách throughput payload khỏi utilization đường truyền.
8. Jain: J=(sum x_i)^2/(n*sum x_i^2), tính trên cùng cửa sổ và tập flow đủ điều kiện; trường hợp mọi x_i=0 trả NA và giữ n nhất quán. Với n flow và throughput không âm, J nằm [1/n,1] khi có traffic, không bắt đầu ở 0.
9. Drop: đếm chủ động AQM, quá giới hạn queue, và drop lớp khác riêng; FlowMonitor loss không tự cho biết lý do. Đối chiếu bảo toàn packet ở queue: enqueue thành công - dequeue - drop sau enqueue = occupancy cuối - đầu, phù hợp trace được chọn.
10. Phân biệt startup và ổn định, không loại startup khỏi đồ thị tái hiện khi paper phân tích startup. Báo cáo toàn bộ khoảng đo và cửa sổ ổn định riêng nếu cần.
11. Đề xuất ban đầu 10 run độc lập mỗi cấu hình để ước lượng biến thiên, rồi điều chỉnh theo độ rộng CI và tài nguyên; đây là đề xuất của nhóm, paper không nêu 10 run. Không coi cửa sổ liên tiếp trong một run là các lần lặp độc lập. Tổng lõi dự kiến 80 run nếu chốt 10 run.
12. Lưu raw CSV, config, seed/run, log version/build, script tổng hợp, figure. Báo cáo mean và CI 95% giữa các run khi đủ điều kiện; không sinh số liệu hay kết luận trước khi chạy.

## Mốc đối chiếu công bố

Theo thứ tự RED / CoDel / PIE / S-PIE:

- Scenario 1 queue: 15,08 / 53,78 / 51,52 / 9,94 packet (cần giữ lưu ý định nghĩa và giới hạn).
- Scenario 2 queue: 14,01 / 43,81 / 27,97 / 10,66 packet.
- Scenario 1 RTT: 81,34 / 85,97 / 85,51 / 80,68 ms.
- Scenario 2 RTT: 81,84 / 85,53 / 87,05 / 80,95 ms.
- Scenario 1 tổng throughput khoảng tại 5s: 40,35 / 41,78 / 41,33 / 41,18 Mbps.
- Scenario 1 Jain khoảng tại 5s: 0,67 / 0,64 / 0,52 / 0,86; tại 20s: 0,97 / 0,94 / 0,92 / 0,99.
- Scenario 2 Jain trung bình paper nêu: 0,91 / 0,89 / 0,87 / 0,94.
- Paper báo S-PIE giảm overflow drop khoảng 83,41% so với PIE ở Scenario 2; chưa có bảng raw counts.

Chỉ so sánh số tuyệt đối khi cùng metric, cửa sổ, lớp đo và cấu hình. Với thông tin thiếu, đánh giá tái hiện xu hướng và giải thích sai lệch, không ép kết quả bằng số tác giả.

## Định hướng viết tiếp sau khi người dùng yêu cầu

Hoàn thiện Phân tích bài báo gọn trong 2–3 trang; sau đó phần Thiết kế và kiểm chứng mô phỏng, Kịch bản và phương pháp đo, Kết quả thực nghiệm, Đối chiếu và hạn chế. Đây là cấu trúc đề xuất, không phải cấu trúc bắt buộc trong slide. Phần setup có thể viết trước khi chạy nhưng phải gắn nhãn tham số đề xuất/chưa xác nhận; phần kết quả chỉ viết từ log thật.

Chưa cần người dùng quyết định ở bước phân tích nội bộ. Trước khi cài/chạy cần biết hoặc kiểm tra được môi trường NS-3 và mã có sẵn; không suy đoán đã có code tác giả. Không dùng kết quả paper để điền như kết quả thực nghiệm của nhóm.
