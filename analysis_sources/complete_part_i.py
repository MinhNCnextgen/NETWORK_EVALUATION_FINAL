from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Report NS3 DGHNM.docx'
doc = Document(r'C:\Users\PC\Downloads\Report NS3 DGHNM.docx')
for child in list(doc._element.body):
    if child.tag != qn('w:sectPr'):
        doc._element.body.remove(child)

normal = doc.styles['normal']
normal.font.name = 'Times New Roman'
normal.font.size = Pt(12)
normal.font.color.rgb = RGBColor(0,0,0)
normal.paragraph_format.space_after = Pt(5)
normal.paragraph_format.line_spacing = 1.08
for name, size in [('Title',16),('Heading 1',14),('Heading 2',12),('Heading 3',12)]:
    if name not in doc.styles:
        doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
    s = doc.styles[name]
    s.font.name = 'Times New Roman'
    s.font.size = Pt(size)
    s.font.bold = True
    s.font.color.rgb = RGBColor(0,0,0)
    s.paragraph_format.space_before = Pt(7)
    s.paragraph_format.space_after = Pt(4)
    s.paragraph_format.keep_with_next = True
    s.paragraph_format.line_spacing = 1.0
for name,size in [('Equation',11),('Algorithm',10.5),('Reference',10)]:
    if name not in doc.styles:
        doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
    s=doc.styles[name]
    s.font.name = 'Times New Roman'
    s.font.size=Pt(size)
    s.font.color.rgb=RGBColor(0,0,0)
    s.paragraph_format.space_after=Pt(3)
    s.paragraph_format.line_spacing=1.0
    s.paragraph_format.keep_together=True

def p(text='', style=None, align=None):
    x=doc.add_paragraph(text, style=style or normal)
    if align is not None:x.alignment=align
    return x
def h(text,level=2,page=False):
    x=p(text,f'Heading {level}')
    x.paragraph_format.page_break_before=page
    return x
def mr(t):
    x=OxmlElement('m:r');z=OxmlElement('m:t');z.text=t;x.append(z);return x
def sub(base,index):
    x=OxmlElement('m:sSub')
    for tag,t in [('m:e',base),('m:sub',index)]:
        z=OxmlElement(tag);z.append(mr(t));x.append(z)
    return x
def frac(num,den):
    x=OxmlElement('m:f')
    for tag,items in [('m:num',num),('m:den',den)]:
        z=OxmlElement(tag)
        for item in items:z.append(mr(item) if isinstance(item,str) else item)
        x.append(z)
    return x
def eq(items):
    x=p(style='Equation',align=WD_ALIGN_PARAGRAPH.CENTER)
    math=OxmlElement('m:oMathPara');m=OxmlElement('m:oMath')
    for item in items:m.append(mr(item) if isinstance(item,str) else item)
    math.append(m);x._p.append(math)
    return x

p('BÁO CÁO BÀI TẬP LỚN','Title',WD_ALIGN_PARAGRAPH.CENTER)
x=p('PHÂN TÍCH MÔ PHỎNG VÀ ĐÁNH GIÁ THUẬT TOÁN S-PIE','Title',WD_ALIGN_PARAGRAPH.CENTER)
x.runs[0].font.size=Pt(14)
h('I  Ý tưởng chính của bài báo',1)
p('Bài báo “A Sketch-Based Fine-Grained Proportional Integral Queue Management Method” của Zhu và cộng sự đề xuất S-PIE, một phương pháp kết hợp PIE với thống kê tần suất luồng bằng Sketch. Mục tiêu là cải thiện công bằng giữa các luồng và giảm trễ hàng đợi, đồng thời duy trì thông lượng [1].')
h('1  Vấn đề đặt ra')
p('Bufferbloat là hiện tượng bộ đệm duy trì lượng gói chờ lớn, làm tăng trễ và suy giảm chất lượng ứng dụng tương tác. Hiện tượng này có thể xảy ra trước khi bộ đệm đầy. Các thuật toán quản lý hàng đợi chủ động (AQM), như RED, CoDel và PIE, phát tín hiệu tắc nghẽn bằng cách loại hoặc đánh dấu gói sớm để nguồn TCP giảm tốc độ gửi.')
p('Hạn chế mà bài báo tập trung giải quyết là RED, CoDel và PIE thông thường không dùng mức chiếm dụng của từng luồng để quyết định loại gói. Luồng có tần suất cao có thể chiếm nhiều tài nguyên, trong khi luồng có tần suất thấp vẫn chịu tác động của chính sách AQM chung. Vì vậy, tác giả bổ sung khả năng nhận diện luồng để điều chỉnh việc loại gói khi tắc nghẽn. Luồng nhỏ ở đây được hiểu theo lưu lượng hoặc tần suất, không mặc định là luồng ngắn hay ứng dụng nhạy trễ.')
h('2  Thuật toán S-PIE')
p('S-PIE giữ bộ điều khiển trễ của PIE và bổ sung mô-đun Sketch để ước lượng tần suất gói của từng luồng trong một khoảng thống kê. Khi trễ đạt ngưỡng phân biệt, thuật toán so sánh tỷ trọng của luồng đang xét với một ngưỡng trung bình có trọng số. Gói thuộc luồng có tỷ trọng lớn hơn ngưỡng bị loại để giảm áp lực lên hàng đợi. Chính sách này không đòi hỏi tạo hàng đợi ưu tiên riêng cho luồng nhỏ [1, mục 3].')
h('3  Đặc điểm và đóng góp của giải pháp')
p('Đóng góp chính là đưa thông tin tần suất luồng vào quyết định AQM thay vì chỉ dựa vào trạng thái hàng đợi chung. Sketch lưu các bộ đếm dùng chung và truy vấn bằng hàm băm, nhờ đó giảm nhu cầu lưu bộ đếm đầy đủ cho từng luồng. Đổi lại, va chạm băm có thể làm ước lượng tần suất cao hơn thực tế. Việc xóa thống kê định kỳ giúp phản ánh lưu lượng mới. Hiệu quả và chi phí tổng thể còn phụ thuộc kích thước Sketch, cửa sổ thống kê và cách tính ngưỡng.')
h('4  Cách thức hoạt động của S-PIE')
h('4.1  Cấu trúc dữ liệu Sketch',3)
p('Cấu trúc Count-Min Sketch gồm d hàng, mỗi hàng có w bộ đếm và một hàm băm. Khóa k nhận diện luồng bằng địa chỉ IP nguồn, IP đích, cổng nguồn, cổng đích và giao thức vận chuyển. Khi cập nhật một gói, mỗi hàng tăng một bộ đếm tương ứng; khi truy vấn, lấy giá trị nhỏ nhất trong d bộ đếm. S-PIE dùng kết quả này để ước lượng mức xuất hiện tương đối của luồng [1, mục 3.1].')

h('4.2  Các công thức chính',3,page=True)
p('Gọi C là mảng bộ đếm, hᵢ là hàm băm hàng i và ĉₖ là tần suất ước lượng của luồng k. Phép cập nhật và truy vấn được viết gọn như sau [1, phương trình (1)–(2)]:')
eq(['C[i, ',sub('h','i'),'(k)] ← C[i, ',sub('h','i'),'(k)] + 1;     ',sub('ĉ','k'),' = minᵢ C[i, ',sub('h','i'),'(k)]'])
p('PIE ước lượng trễ hiện tại từ độ dài hàng đợi q và tốc độ dequeue trung bình r̄. Tốc độ mới được làm trơn với hệ số ε; q và tốc độ phải dùng đơn vị nhất quán:')
eq([sub('δ','cur'),' = ',frac(['q'],['r̄']),';     r̄ ← (1 − ε)',sub('r̄','old'),' + ε',frac([sub('B','out')],['Δt'])])
p('Trong biểu thức trên, Bₒᵤₜ là số byte rời hàng đợi trong thời gian Δt nếu q được đo bằng byte. Phương trình (3) của bài báo cập nhật xác suất p theo trễ tham chiếu δref, trễ trước đó δold và trễ hiện tại δcur:')
eq(['p ← ',sub('p','old'),' + α(',sub('δ','old'),' − ',sub('δ','ref'),') + β(',sub('δ','cur'),' − ',sub('δ','old'),')'])
p('Với M là tổng số gói được cập nhật trong cửa sổ và F là tập luồng được xét, tỷ trọng cùng ngưỡng phân biệt được biểu diễn theo phương trình (8)–(9):')
eq([sub('G','k'),' = ',frac([sub('ĉ','k')],['M']),';     ',sub('G','threshold'),' = ',frac(['Σᵢ∈F ',sub('ĉ','i'),sub('G','i')],['Σᵢ∈F ',sub('ĉ','i')])])
p('Gói của luồng k bị loại trong nhánh phân biệt nếu Gₖ > Gthreshold. Đây là quy tắc báo cáo lựa chọn theo mô tả phạt luồng lớn; dòng 12 của Algorithm 2 trong bài báo in dấu “<”, không thống nhất với phần diễn giải [1, trang 6–7].')
h('4.3  Mã giả dùng để tái hiện',3)
steps=[
'Định kỳ: cập nhật trễ và xác suất loại gói bằng bộ điều khiển PIE.',
'Khi nhận gói: nếu hàng đợi đầy, loại gói do vượt giới hạn.',
'Nếu chưa có ước lượng hợp lệ hoặc M = 0: xử lý theo PIE.',
'Nếu δcur < δref/3: dùng nhánh loại gói xác suất của PIE.',
'Ngược lại: truy vấn Sketch, tính Gₖ và Gthreshold; loại nếu Gₖ > Gthreshold.',
'Nếu được chấp nhận và enqueue thành công: cập nhật Sketch và tăng M.',
'Định kỳ hết cửa sổ: xóa đồng bộ Sketch, M và tập khóa luồng.'
]
for i,t in enumerate(steps,1):p(f'{i}. {t}','Algorithm')
p('Mã giả trên làm rõ các điểm bài báo mô tả chưa thống nhất: truy vấn trước cập nhật, chỉ đếm gói enqueue thành công và không cập nhật lại khi dequeue. Khi tái hiện trên NS-3.45, báo cáo dự kiến dùng bộ điều khiển PIE của phiên bản này cho cả PIE và S-PIE. Bộ điều khiển đó dùng δcur thay cho δold trong số hạng α và có các cơ chế điều chỉnh xác suất bổ sung; đây là khác biệt cần công bố so với công thức gốc [2].')

h('5  Phương pháp thí nghiệm của bài báo',2,page=True)
h('5.1  Mô hình thí nghiệm',3)
p('Tác giả đánh giá trên Ubuntu 16.04 và NS-3.27 bằng topology dumbbell: 100 nguồn gửi tới các đích qua hai router. Liên kết truy nhập có băng thông 100 Mbps, trễ 5 ms; liên kết nút thắt có băng thông 50 Mbps, trễ 20 ms. Nguồn dùng mô hình ON/OFF và TCP NewReno. AQM đặt tại Router1 theo hướng đi qua nút thắt, với giới hạn bộ đệm công bố là 50 gói. Bốn thuật toán được so sánh là RED, CoDel, PIE và S-PIE [1, mục 4.1].')
h('5.2  Các kịch bản mạng',3)
p('Kịch bản 1 phân biệt tải: 50 nguồn đặt tốc độ ứng dụng 1 Mbps và 50 nguồn đặt 50 Mbps, tương ứng hai nhóm luồng nhỏ và lớn. Kịch bản 2 đặt 10 Mbps cho cả 100 nguồn để đánh giá trường hợp không chia nhóm tốc độ. Các tốc độ này là cấu hình nguồn phát, không phải thông lượng TCP nhận được. Bài báo chưa nêu đầy đủ phân phối và tham số ON/OFF.')
h('5.3  Các thông số đo đạc',3)
p('Đánh giá gồm độ dài hàng đợi trung bình, RTT, thông lượng, chỉ số công bằng Jain và số gói bị loại chủ động hoặc do đầy bộ đệm. Hàng đợi ngắn hơn thường giảm thời gian chờ; RTT phản ánh thời gian trao đổi dữ liệu và ACK. Thông lượng được xem xét cùng với trễ để kiểm tra việc giảm hàng đợi có làm giảm khả năng truyền dữ liệu hay không. Với xᵢ là thông lượng luồng i và n luồng, chỉ số Jain là:')
eq(['J = ',frac(['(Σᵢ ',sub('x','i'),')²'],['n Σᵢ ',sub('x','i'),'²'])])
p('Khi có lưu lượng, J nằm trong khoảng [1/n, 1]; càng gần 1 thì phân bổ thông lượng càng đồng đều. Khi tái hiện, thông lượng theo Mbps cần tính từ số byte nhận trong cùng khoảng đo. Cần tách loại gói chủ động khỏi overflow và xét đồng thời với thông lượng, thay vì mặc định nhiều gói bị loại chủ động hơn luôn tốt hơn.')
h('5.4  Kết luận của tác giả và phạm vi kiểm chứng',3)
p('Tác giả kết luận S-PIE giảm hàng đợi và RTT, cải thiện công bằng, đồng thời giữ thông lượng gần các thuật toán đối chứng. Chẳng hạn, ở kịch bản 1, RTT trung bình công bố của PIE và S-PIE lần lượt là 85,51 ms và 80,68 ms; ở kịch bản 2, Jain trung bình lần lượt là 0,87 và 0,94 [1, mục 4.2]. Đây là kết quả của bài báo, chưa phải kết quả mô phỏng của báo cáo này.')
p('Phần thực nghiệm tiếp theo sẽ kiểm chứng xu hướng trên bằng NS-3.45, dùng cùng môi trường và tải cho các AQM. Các tham số còn thiếu sẽ được công bố và khảo sát độ nhạy. Riêng độ dài hàng đợi công bố có giá trị vượt giới hạn 50 gói, nên phải làm rõ phép đo trước khi đối chiếu số tuyệt đối. Kết luận tái hiện sẽ dựa trên dữ liệu đo được và có xét khác biệt phiên bản, cấu hình.')
p('[1] H. Zhu và cộng sự, “A Sketch-Based Fine-Grained Proportional Integral Queue Management Method,” Axioms, 12(9), 814, 2023. DOI: 10.3390/axioms12090814.','Reference')
p('[2] ns-3 Project, mã nguồn PIE, tag ns-3.45, src/traffic-control/model/pie-queue-disc.cc. https://github.com/nsnam/ns-3-dev-git/blob/ns-3.45/src/traffic-control/model/pie-queue-disc.cc','Reference')

# Preserve the original page geometry and use an editable, consistent font setup.
for x in doc.paragraphs:
    for run in x.runs:
        run.font.name='Times New Roman'
        run.font.color.rgb=RGBColor(0,0,0)
        rf=run._element.get_or_add_rPr().get_or_add_rFonts()
        for k in ['ascii','hAnsi','eastAsia','cs']:rf.set(qn('w:'+k),'Times New Roman')
doc.core_properties.title='Phân tích mô phỏng và đánh giá thuật toán S-PIE'
doc.core_properties.subject='Phần I Ý tưởng chính của bài báo'
doc.save(OUT)
print(str(OUT))
print('Paragraphs:',len(doc.paragraphs),'Equations:',len(doc._element.xpath('//m:oMath')))
