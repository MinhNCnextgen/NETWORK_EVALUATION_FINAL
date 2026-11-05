from pathlib import Path
from copy import deepcopy
from zipfile import ZipFile
from lxml import etree as E

ROOT=Path(__file__).resolve().parent.parent
SOURCE=Path(r'C:\Users\PC\Downloads\Report NS3 DGHNM.docx')
OUTPUT=ROOT/'Report NS3 DGHNM.docx'
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
M='http://schemas.openxmlformats.org/officeDocument/2006/math'
NS={'w':W,'m':M}
def el(tag,text=None):
    prefix,name=tag.split(':'); x=E.Element('{'+{'w':W,'m':M}[prefix]+'}'+name)
    if text is not None:x.text=text
    return x
def mr(t):
    r=el('m:r');r.append(el('m:t',t));return r
def sub(a,b):
    s=el('m:sSub');e=el('m:e');e.append(mr(a));i=el('m:sub');i.append(mr(b));s.extend([e,i]);return s
def frac(a,b):
    f=el('m:f')
    for tag,items in [('m:num',a),('m:den',b)]:
        n=el(tag)
        for i in items:n.append(mr(i) if isinstance(i,str) else i)
        f.append(n)
    return f

with ZipFile(SOURCE) as z:
    raw=z.read('word/document.xml')
root=E.fromstring(raw)
body=root.find('w:body',NS)
original=body.findall('w:p',NS)
original_xml=[E.tostring(p) for p in original]
template=original[10]
def newp(text=None,math=None,plain=False):
    p=el('w:p');pr=deepcopy(template.find('w:pPr',NS));p.append(pr)
    if math is not None or plain:
        for n in pr.findall('w:numPr',NS):pr.remove(n)
    if math is not None:
        jc=pr.find('w:jc',NS)
        if jc is None:jc=el('w:jc');pr.append(jc)
        jc.set('{'+W+'}val','center')
        mp=el('m:oMathPara');m=el('m:oMath')
        for i in math:m.append(mr(i) if isinstance(i,str) else i)
        mp.append(m);p.append(mp)
    else:
        r=el('w:r');rpr=deepcopy(template.find('w:r/w:rPr',NS))
        if rpr is not None:r.append(rpr)
        t=el('w:t',text);t.set('{http://www.w3.org/XML/1998/namespace}space','preserve');r.append(t);p.append(r)
    return p
added=[]
def insert(index,items):
    anchor=original[index]
    for item in items:
        n=newp(text=item) if isinstance(item,str) else newp(**item)
        anchor.addnext(n);anchor=n;added.append(n)

insert(14,[
'Sketch là một cấu trúc dữ liệu dùng để thống kê tần suất xuất hiện của các luồng dữ liệu. Trong S-PIE, Sketch gồm một mảng hai chiều có d hàng và w cột. Mỗi hàng có một hàm băm riêng để ánh xạ thông tin của luồng vào một bộ đếm tương ứng. Thông tin nhận diện luồng có thể sử dụng bộ 5 giá trị: địa chỉ IP nguồn, địa chỉ IP đích, cổng nguồn, cổng đích và giao thức truyền tải.',
'Khi một gói tin được cập nhật vào Sketch, các bộ đếm mà luồng đó ánh xạ tới sẽ được tăng lên. Khi truy vấn, thuật toán lấy giá trị nhỏ nhất trong các bộ đếm để ước lượng tần suất của luồng. Việc lấy giá trị nhỏ nhất giúp hạn chế ảnh hưởng của những luồng khác cùng ánh xạ vào một vị trí. Tuy nhiên, kết quả vẫn có thể cao hơn tần suất thực tế do xảy ra va chạm băm. Các bộ đếm được xóa theo chu kỳ để thông tin thống kê phản ánh lưu lượng trong khoảng thời gian mới.'
])
insert(15,[
'Công thức cập nhật bộ đếm: với k là khóa của luồng, hᵢ là hàm băm của hàng i và C là mảng bộ đếm, mỗi gói tin được thống kê sẽ làm tăng một bộ đếm ở từng hàng:',
{'math':['C[i, ',sub('h','i'),'(k)] ← C[i, ',sub('h','i'),'(k)] + 1,     i = 1, …, d']},
'Công thức truy vấn tần suất: giá trị ước lượng của luồng k là giá trị nhỏ nhất trong d bộ đếm tương ứng:',
{'math':[sub('ĉ','k'),' = minᵢ C[i, ',sub('h','i'),'(k)]']},
'Công thức ước lượng độ trễ hàng đợi: độ trễ hiện tại được tính từ lượng dữ liệu đang chờ trong hàng đợi và tốc độ trung bình của dữ liệu rời hàng đợi:',
{'math':[sub('del','cur'),' = ',frac([sub('q','len')],[sub('dq_rate','avg')])]},
'Trong đó, q_len là lượng dữ liệu trong hàng đợi và dq_rate_avg là tốc độ trung bình rời hàng đợi. Khi thực hiện trên NS3.45, hai đại lượng này lần lượt được tính theo byte và byte trên giây để thu được độ trễ theo giây. Tốc độ trung bình được cập nhật bằng phương pháp làm trơn:',
{'math':[sub('dq_rate','avg'),' ← (1 − ε)',sub('dq_rate','avg_old'),' + ε',frac([sub('dq','count')],[sub('dq','time')])]},
'Trong đó, dq_count là số byte rời hàng đợi trong thời gian đo dq_time. Hệ số ε quyết định mức ảnh hưởng của số đo mới đến giá trị trung bình. Bộ ước lượng tốc độ dequeue của PIE trong NS3.45 sử dụng ε = 0,5.',
'Công thức cơ sở để cập nhật xác suất loại gói của bộ điều khiển PIE trong NS3.45 được viết như sau:',
{'math':['p ← ',sub('p','old'),' + α(',sub('del','cur'),' − ',sub('del','ref'),') + β(',sub('del','cur'),' − ',sub('del','old'),')']},
'Trong đó, p_old là xác suất ở chu kỳ trước, del_ref là độ trễ mong muốn và del_old là độ trễ đã ước lượng ở chu kỳ trước. Hệ số α điều chỉnh theo mức chênh lệch với độ trễ mong muốn, còn β điều chỉnh theo xu hướng thay đổi độ trễ. NS3.45 còn có các bước điều chỉnh hệ số và giới hạn xác suất trong khoảng từ 0 đến 1. Công thức in trong bài báo sử dụng del_old ở số hạng α; khi tái hiện, báo cáo sử dụng bộ điều khiển của NS3.45 cho cả PIE và S-PIE để thống nhất cách so sánh.',
'Công thức xác định luồng lớn: gọi M là tổng số gói đã được thống kê trong cửa sổ hiện tại và ĉₖ là tần suất ước lượng của luồng k. Tỷ trọng của luồng được tính như sau:',
{'math':[sub('G','k'),' = ',frac([sub('ĉ','k')],['M']),';     ',sub('G','threshold'),' = ',frac(['Σᵢ∈F ',sub('ĉ','i'),sub('G','i')],['Σᵢ∈F ',sub('ĉ','i')])]},
'Trong đó, F là tập các luồng được xét trong cửa sổ thống kê. Ngưỡng Gthreshold là trung bình có trọng số của tỷ trọng các luồng, với trọng số là tần suất ước lượng tương ứng. Trong báo cáo này, khi Gk > Gthreshold, luồng được xem là luồng lớn và gói tin bị loại ở nhánh phân biệt luồng. Nếu Gk bằng hoặc nhỏ hơn ngưỡng thì gói tin được phép vào hàng đợi nếu còn chỗ.'
])
insert(16,[
'Quá trình xử lý của S-PIE khi thực hiện trong báo cáo được mô tả như sau:',
{'text':'Bước 1: Cập nhật độ trễ hàng đợi và xác suất loại gói theo chu kỳ bằng bộ điều khiển PIE.','plain':True},
{'text':'Bước 2: Khi một gói tin tới, kiểm tra hàng đợi. Nếu hàng đợi đầy thì loại gói tin do vượt giới hạn bộ đệm.','plain':True},
{'text':'Bước 3: Nếu chưa có đủ thông tin để ước lượng hoặc M = 0, xử lý gói tin theo PIE.','plain':True},
{'text':'Bước 4: Nếu del_cur < del_ref/3, sử dụng nhánh loại gói theo xác suất của PIE.','plain':True},
{'text':'Bước 5: Nếu del_cur ≥ del_ref/3 và đã có thống kê hợp lệ, truy vấn Sketch để tính Gk và Gthreshold. Nếu Gk > Gthreshold thì loại gói tin; ngược lại cho phép vào hàng đợi.','plain':True},
{'text':'Bước 6: Nếu gói tin được chấp nhận và đưa vào hàng đợi thành công, cập nhật Sketch và tăng M lên 1.','plain':True},
{'text':'Bước 7: Khi hết cửa sổ thống kê, xóa đồng thời các bộ đếm Sketch, tổng số gói M và tập khóa luồng để bắt đầu một cửa sổ mới.','plain':True},
'Để tránh đếm một gói tin nhiều lần, báo cáo lựa chọn cập nhật Sketch sau khi gói tin vào hàng đợi thành công và không cập nhật lại khi gói tin rời hàng đợi. Các gói đã bị loại không được cộng vào thống kê. Đây là cách thực hiện được sử dụng để làm rõ những điểm chưa thống nhất giữa mô tả và mã giả của bài báo.'
])
insert(18,[
'Bài báo thực hiện mô phỏng trên NS3.27 với hệ điều hành Ubuntu 16.04. Mô hình mạng được sử dụng là dumbbell, trong đó các nút gửi và nhận kết nối qua hai router. Liên kết giữa Router1 và Router2 là liên kết nút thắt, có băng thông 50 Mbps và độ trễ 20 ms. Các liên kết nối nút đầu cuối với router có băng thông 100 Mbps và độ trễ 5 ms.',
'Mô hình có 100 nút gửi, sử dụng nguồn ON/OFF và thuật toán điều khiển tắc nghẽn TCP NewReno. Thuật toán AQM được đặt tại hàng đợi của Router1 theo hướng truyền qua liên kết nút thắt. Giới hạn hàng đợi được công bố là 50 gói. Các thuật toán đối chứng gồm RED, CoDel và PIE để đánh giá sự thay đổi khi bổ sung Sketch vào S-PIE.',
'Trong báo cáo này, các thí nghiệm sẽ được thực hiện trên NS3.45. Mô hình mạng và hai kịch bản chính được giữ theo bài báo, còn những tham số chưa được nêu đầy đủ sẽ được thiết lập rõ ràng và khảo sát với nhiều giá trị. Các thuật toán được so sánh trong cùng một môi trường mô phỏng.'
])
insert(19,[
'Kịch bản 1: Chia 100 nút gửi thành hai nhóm. Nhóm thứ nhất gồm 50 nút có tốc độ phát đặt tại ứng dụng là 1 Mbps để mô phỏng các luồng nhỏ. Nhóm thứ hai gồm 50 nút có tốc độ phát là 50 Mbps để mô phỏng các luồng lớn. Kịch bản này đánh giá khả năng phân biệt luồng và cải thiện tính công bằng khi lưu lượng giữa các nhóm có sự chênh lệch.',
'Kịch bản 2: Cả 100 nút gửi đều được đặt tốc độ phát tại ứng dụng là 10 Mbps. Kịch bản này không chia nhóm tốc độ, nhằm đánh giá hiệu năng khi các nguồn có cùng cấu hình tốc độ phát nhưng lưu lượng thực tế thay đổi theo hoạt động ON/OFF và điều khiển tắc nghẽn của TCP.',
'Các tốc độ trên là tốc độ phát được cấu hình tại ứng dụng, không phải thông lượng đảm bảo tại đầu nhận. Bài báo chưa nêu đầy đủ phân phối và tham số ON/OFF, vì vậy khi mô phỏng cần ghi rõ các thiết lập này để có thể thực hiện lại thí nghiệm.'
])
insert(20,[
'Độ dài hàng đợi trung bình: phản ánh lượng gói tin tồn đọng tại router. Hàng đợi càng dài thì thời gian chờ của gói tin thường càng lớn. Khi thực hiện thí nghiệm, cần theo dõi cả số gói tức thời và giá trị trung bình trong khoảng thời gian đo.',
'Độ trễ khứ hồi RTT: là thời gian từ lúc nguồn gửi dữ liệu đến khi nhận được ACK tương ứng. Chỉ số này được dùng để đánh giá ảnh hưởng của hàng đợi đến độ trễ truyền thông. Trong NS3.45, cần phân biệt mẫu RTT gần nhất với RTT đã làm trơn khi thu thập kết quả.',
'Thông lượng: phản ánh lượng dữ liệu nhận thành công trong một đơn vị thời gian. Báo cáo sẽ tính theo số byte nhận tại đích và quy đổi sang Mbps. Thông lượng được theo dõi cùng độ dài hàng đợi và RTT để đánh giá việc giảm độ trễ có làm giảm khả năng truyền dữ liệu hay không.',
'Chỉ số công bằng Jain: phản ánh mức độ chia sẻ thông lượng giữa các luồng. Với xᵢ là thông lượng của luồng i và n là số luồng, công thức được tính như sau:',
{'math':['J = ',frac(['(Σᵢ ',sub('x','i'),')²'],['n Σᵢ ',sub('x','i'),'²'])]},
'Khi có lưu lượng, chỉ số Jain nằm trong khoảng từ 1/n đến 1. Giá trị càng gần 1 thì thông lượng giữa các luồng càng đồng đều. Các luồng cần được tính trong cùng khoảng thời gian để việc so sánh có ý nghĩa.',
'Số gói tin bị loại: bao gồm gói bị loại chủ động bởi AQM và gói bị loại do hàng đợi đầy. Cần thống kê riêng hai loại này để đánh giá khả năng xử lý tắc nghẽn. Số gói bị loại chủ động phải được xem xét cùng thông lượng và độ trễ, không thể dùng riêng để kết luận hiệu năng tốt hơn.',
'Kết quả đánh giá của bài báo cho thấy S-PIE có thể giảm độ dài hàng đợi và RTT, cải thiện tính công bằng, đồng thời duy trì thông lượng gần các thuật toán đối chứng. Phần thí nghiệm của báo cáo sẽ kiểm chứng những nhận xét này bằng kết quả thu được trên NS3.45 và phân tích các khác biệt so với bài báo.'
])

# Existing paragraphs and all package parts other than document.xml remain intact.
assert [E.tostring(p) for p in original] == original_xml
payload=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
with ZipFile(SOURCE) as zin, ZipFile(OUTPUT,'w') as zout:
    for info in zin.infolist():
        zout.writestr(info,payload if info.filename=='word/document.xml' else zin.read(info.filename))
with ZipFile(OUTPUT) as z:
    edited=E.fromstring(z.read('word/document.xml'))
    survivors=[p for p in edited.find('w:body',NS) if p.tag=='{'+W+'}p' and p.get('{http://schemas.microsoft.com/office/word/2010/wordml}paraId')]
    assert [E.tostring(p) for p in survivors] == original_xml
    with ZipFile(SOURCE) as src:
        for name in src.namelist():
            if name!='word/document.xml':assert src.read(name)==z.read(name),name
assert b'[1]' not in payload and b'[2]' not in payload
print('Preserved original paragraphs:',len(original))
print('Added paragraphs:',len(added))
print('Unchanged package parts: verified')
print('Output bytes:',OUTPUT.stat().st_size)
