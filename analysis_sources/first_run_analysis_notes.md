# Chuẩn bị phân tích lần chạy đầu — 06/11/2026

Phạm vi: rà soát nội bộ, chưa vẽ biểu đồ, chưa sửa báo cáo Word hoặc dữ liệu gốc.

## Nguồn và quyết định hiện hành

Đã đọc các file .md trong analysis_sources và s-pie/README.md, bản trích yêu cầu học phần requirements.txt, paper.txt và văn bản bản Word hiện hành. Đã xem trực tiếp trang 10–13 của PDF gốc C:/Users/PC/Downloads/axioms-12-00814-v2.pdf (Hình 4–10). Bản Word gốc hiện hành theo current_document.md nằm ở thư mục dự án, không phải Downloads.

Yêu cầu học phần: tái hiện, kiểm chứng chương trình, chạy kịch bản, đối chiếu kết quả và nhận xét. Chương phân tích bài báo khoảng 2–3 trang; không có số biểu đồ hay số run bắt buộc trong slide. Giữ các lựa chọn đã thống nhất: NS-3.45, dấu Gk > Gthreshold; cập nhật Sketch sau enqueue thành công, query trước insert, reset đồng bộ; chưa chạy biến thể đảo dấu. Thông tin NS-3.27 trong quyết định cũ là lịch sử, không ghi thành môi trường đang chạy.

Mặc định lần chạy này là mặc định chương trình thí nghiệm, KHÔNG phải toàn bộ mặc định nguyên bản ns-3.45. Config S-PIE ghi ref=5ms, Tupdate=30ms, dequeue threshold=10000 byte, burst=100ms, rate estimator=true; CMS 4×1024, reset 0.5s. TCP NewReno+PRR, MSS=1000, initial cwnd=10. ON/OFF exponential mean 1s mỗi trạng thái, 30s phát và 5s drain. Những tham số paper không công bố phải ghi là lựa chọn triển khai.

## Dữ liệu có sẵn và kiểm tra

Có 28 CSV: 4 thuật toán × 7 file, chỉ scenario=1, seed=1, run=1. README có nhắc thử nghiệm bàn giao cả hai kịch bản nhưng không được suy ra Data hiện có kịch bản 2.

Đã tái tính summary từ raw bằng summarize.py và khớp mọi trường với summary cung cấp (sai số số thực <1e-8). Mỗi goodput CSV có đúng 3000 khóa (end_s,flow) riêng biệt; Mbps khớp payload_bytes×8/1e6. Các trace queue/rtt/drop/link có thời gian không giảm; queue trong [0,50] và có mốc kết thúc 35s; RTT có đủ 100 flow. Không có drop queue khác trong [0,30). Đây là kiểm tra nhất quán dữ liệu, không thay thế việc chứng minh toàn bộ thuật toán đúng. Chưa có build log/commit của lần chạy hoặc events trace để tái kiểm chứng độc lập mọi nhánh.

Kết quả chi tiết của kiểm tra và trích văn bản Word lưu trong first_run_review_output.txt. review_first_run.py là script kiểm tra hỗ trợ, không sửa raw.

## Kết quả sơ bộ (chỉ một run)

Khoảng [0,30), RTT là trung bình sự kiện thay đổi LastRTT, Jain tính trên tổng byte từng flow trong cả khoảng:

| AQM | Goodput Mbps | Queue trung bình thời gian, gói | LastRTT ms | Jain | Drop đầy | Drop chủ động |
|---|---:|---:|---:|---:|---:|---:|
| RED | 41.4235 | 8.0813 | 80.7279 | 0.97000 | 84 | 5128 |
| CoDel | 46.2888 | 30.9140 | 84.2425 | 0.94189 | 4649 | 252 |
| PIE | 46.4109 | 31.6181 | 84.3033 | 0.94226 | 4848 | 1 |
| S-PIE | 39.5213 | 5.4117 | 79.1541 | 0.97790 | 122 | 10621 |

S-PIE giảm queue và RTT, Jain toàn khoảng tốt hơn; goodput thấp hơn PIE khoảng 14.85%. Chưa tái hiện đầy đủ kết luận duy trì thông lượng gần đối chứng. Goodput nhóm nhỏ của S-PIE 18.5923 Mbps còn thấp hơn PIE 19.7880 Mbps; khoảng cách hai nhóm thu hẹp không đồng nghĩa nhóm nhỏ nhận nhiều dữ liệu hơn. Không kết luận ưu thế chung, ý nghĩa thống kê hoặc nguyên nhân từ một run.

PIE hầu hết drop do đầy (4848/4849), còn Sketch drop của S-PIE là 10621/10743. Cần xem tương tác estimator/controller, ref, burst, giới hạn queue và tải nếu khảo sát tiếp; dữ liệu hiện tại chưa đủ khẳng định lỗi controller. Không chỉnh tham số chỉ để khớp đường paper.

Khoảng [0,20) phục vụ đối chiếu scenario 1:

| AQM | Goodput Mbps | Queue gói | LastRTT ms | Jain toàn khoảng |
|---|---:|---:|---:|---:|
| RED | 41.1340 | 8.1713 | 80.4426 | 0.94793 |
| CoDel | 45.8804 | 30.4836 | 83.8292 | 0.92052 |
| PIE | 45.9444 | 30.5039 | 83.8940 | 0.91640 |
| S-PIE | 39.1100 | 5.6850 | 78.7528 | 0.96882 |

Đã tính thêm [5,20) trong output kiểm tra; không mặc định khoảng này là trạng thái ổn định nếu chưa xem chuỗi.

## Bản đồ biểu đồ và cách đo

| Hình paper | Dữ liệu và chuẩn bị | Trạng thái |
|---|---|---|
| 4a queue scenario 1 | queue.csv; tích phân Q(t) theo cửa sổ; panel 0–20s; giữ bản 0–30s để xem toàn run | Có dữ liệu |
| 5a RTT scenario 1 | rtt.csv, LastRTT; 4 panel cùng trục, 0–20s; ghi rõ tập flow và sự kiện trace | Có dữ liệu |
| 6 throughput small/large | goodput CSV, flow 1–50 và 51–100; các mốc 5,10,15,20s; giữ chuỗi 1s chẩn đoán | Có dữ liệu |
| 9a fairness | Jain đủ 100 flow, giữ cả flow=0; các mốc 5,10,15,20s | Có dữ liệu |
| 4b,5b,7,9b | Cần scenario 2 | Chưa có |
| 8 | Boxplot throughput qua nhiều thí nghiệm scenario 2 | Chưa có scenario 2 và run lặp |
| 10a,b | Boxplot overflow/active drop scenario 2 | Chưa có; drop scenario 1 chỉ là phân tích bổ sung |

Hình 6–8 ghi trục Throughput (1×10^6 Bytes/s), KHÔNG phải Mbps. Chuyển giá trị trục sang Mbps bằng nhân 8. Hình 6 và 9a có mốc 5/10/15/20s nhưng paper không nói rõ cửa sổ là từng 5s, lũy kế, hay giá trị cục bộ. Khi vẽ cần khai báo quy ước; nên chuẩn bị cả cửa sổ 5s và lũy kế từ đầu để đánh giá độ nhạy của cách tổng hợp, không chọn cách nào chỉ vì trông giống paper. Không nối số summary 0–30 thành đường thời gian.

Jain toàn khoảng khác trung bình Jain từng giây và khác Jain của giây cuối. Ví dụ S-PIE Jain [0,20)=0.96882 nhưng [19,20)=0.87553; PIE lần lượt 0.91640 và 0.62546. Đây là khác biệt phép đo, không phải sai số làm tròn.

Queue: raw là occupancy sau mỗi enqueue/dequeue. Dùng trung bình theo thời gian, không trung bình các hàng event. Paper Eq10–11 mô tả làm trơn có idle handling, chưa đủ thông tin để tái tạo chính xác; không gọi trung bình cửa sổ của nhóm là cùng phép đo. Giới hạn 50p được giữ; số queue công bố >50 ở CoDel/PIE scenario 1 cần nêu là điểm không nhất quán chưa giải thích, không tăng limit để khớp.

RTT: tách LastRTT và RTT/SRTT. Callback chỉ ghi khi giá trị đổi; trung bình theo event không phải trung bình tất cả packet hay trung bình đều các flow. Tránh nối các mẫu của nhiều flow thành một đường giả liên tục; dùng scatter/đường tổng hợp theo cửa sổ với quy tắc minh bạch. Paper không nêu rõ tập packet/flow theo dõi.

Goodput: byte payload tại sink; khác tốc độ wire có header/tái truyền. Không lấy goodput/50 rồi gọi là mức bận liên kết thực; wire.csv là phép đo riêng với quy ước khung theo thời điểm bắt đầu phát. Giữ [0,30) cho chính, [30,35] drain riêng.

Drop: lọc location=core-forward, layer=qdisc và cùng khoảng đo. PIE/S-PIE Forced drop là overflow; RED Unforced/Forced là AQM, Dropped by internal queue là overflow ở cấu hình này; CoDel Overlimit là overflow, Target exceeded là chủ động. Không dùng số drop tổng để thay cho tỉ lệ mất end-to-end. Một run chỉ vẽ count/bar, không dùng 30 giây của run làm 30 mẫu độc lập cho boxplot hoặc CI giữa run.

## Hướng phân tích báo cáo sau này

Trình bày setup thực tế và khác biệt paper -> tính đúng đắn/phép đo -> kết quả bốn AQM -> đối chiếu xu hướng và đánh đổi -> hạn chế. So sánh trong cùng ns-3.45 là chính; paper ns-3.27 là tham chiếu có giới hạn. Phân biệt số paper chép từ văn bản, số đọc xấp xỉ từ hình và số tính từ CSV; chưa số hóa đường gốc nên không tính RMSE hoặc sai số điểm-điểm.

Bản Word hiện hành còn vài câu nên chỉnh khi được yêu cầu viết báo cáo: ECN không phải AQM độc lập; bufferbloat không chỉ là tràn đầy; không mặc định luồng nhỏ nhạy trễ hoặc có cơ chế ưu tiên chuyển tiếp riêng. Phần kết quả paper trong Word là kết luận tác giả, không tự thay thành kết quả nhóm. Chưa sửa Word ở bước này.

Trước kết luận định lượng cuối: bổ sung scenario 2 và các run độc lập; đề xuất 10 run/config trước đây là kế hoạch, không phải yêu cầu paper. Mỗi run tính metric trước, rồi tổng hợp giữa run; giữ tham số và traffic pairing nhất quán. Không cần chạy thêm hoặc sửa mô phỏng trong bước chuẩn bị hiện tại.
