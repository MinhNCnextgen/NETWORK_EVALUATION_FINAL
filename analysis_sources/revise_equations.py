from pathlib import Path
from copy import deepcopy
from zipfile import ZipFile
from lxml import etree as E

ROOT=Path(__file__).resolve().parent.parent
TARGET=ROOT/'Report NS3 DGHNM.docx'
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
M='http://schemas.openxmlformats.org/officeDocument/2006/math'
NS={'w':W,'m':M}
with ZipFile(TARGET) as z:
    entries=[(i,z.read(i.filename)) for i in z.infolist()]
root=E.fromstring(dict((i.filename,b) for i,b in entries)['word/document.xml'])
body=root.find('w:body',NS)
def txt(p):return ''.join(p.xpath('.//w:t/text()',namespaces=NS))
def find(s):return next(p for p in body.findall('w:p',NS) if txt(p).strip()==s)
start=find('Các công thức');end=find('Mã giả');metric=find('Các thông số đo đạc')
template=next(p for p in body.findall('w:p',NS) if txt(p).startswith('Cấu trúc dữ liệu Sketch được sử dụng'))
before=[E.tostring(x) for x in body]
def el(tag,text=None):
    pref,key=tag.split(':'); x=E.Element('{'+{'w':W,'m':M}[pref]+'}'+key)
    if text is not None:x.text=text
    return x
def mr(t):
    r=el('m:r');r.append(el('m:t',t));return r
def app(parent,items):
    for i in items:parent.append(mr(i) if isinstance(i,str) else i)
def sub(base,index):
    r=el('m:sSub');a=el('m:e');a.append(mr(base));b=el('m:sub');b.append(mr(index));r.extend([a,b]);return r
def sup(items,power):
    r=el('m:sSup');a=el('m:e');app(a,items);b=el('m:sup');b.append(mr(power));r.extend([a,b]);return r
def frac(a,b):
    r=el('m:f')
    for tag,items in [('m:num',a),('m:den',b)]:
        t=el(tag);app(t,items);r.append(t)
    return r
def sigma(items,lower='i=1',upper='n'):
    r=el('m:nary');pr=el('m:naryPr')
    for tag,val in [('m:chr','∑'),('m:limLoc','subSup')]:
        x=el(tag);x.set('{'+M+'}val',val);pr.append(x)
    r.append(pr)
    for tag,vals in [('m:sub',[lower]),('m:sup',[upper]),('m:e',items)]:
        x=el(tag);app(x,vals);r.append(x)
    return r
def paragraph(text=None,math=None,bullet=True,keep=False):
    p=el('w:p');pr=deepcopy(template.find('w:pPr',NS));p.append(pr)
    if math is not None or not bullet:
        for n in pr.findall('w:numPr',NS):pr.remove(n)
    if keep:
        pr.append(el('w:keepNext'))
    if math is not None:
        jc=pr.find('w:jc',NS)
        if jc is None:jc=el('w:jc');pr.append(jc)
        jc.set('{'+W+'}val','center')
        mp=el('m:oMathPara');m=el('m:oMath');app(m,math);mp.append(m);p.append(mp)
    else:
        r=el('w:r');rpr=deepcopy(template.find('w:r/w:rPr',NS))
        if rpr is not None:r.append(rpr)
        t=el('w:t',text);t.set('{http://www.w3.org/XML/1998/namespace}space','preserve');r.append(t);p.append(r)
    return p
def label(t):return paragraph(t,keep=True)
def eq(items,n):return paragraph(math=items+['     ('+str(n)+')'],keep=True)
def defs(t):return paragraph(t,bullet=False)

formulas=[
label('Cập nhật bộ đếm Sketch'),
eq(['count[i, ',sub('h','i'),'(',sub('key','i'),')] += value,     i = 1, 2, …, d'],1),
defs('count[i, hᵢ(keyᵢ)]: bộ đếm tại vị trí ánh xạ của hàng i; hᵢ: hàm băm thứ i; keyᵢ: khóa nhận diện luồng; value: giá trị cập nhật bộ đếm; d: số hàng của Sketch.'),
label('Truy vấn tần suất luồng'),
eq(['query(',sub('key','i'),') = Mincount[i, ',sub('h','i'),'(',sub('key','i'),')]'],2),
defs('query(keyᵢ): tần suất ước lượng của luồng; Mincount: giá trị nhỏ nhất trong các bộ đếm tương ứng với khóa đang xét.'),
label('Xác suất loại bỏ gói tin'),
eq(['p = ',sub('p','old'),' + α(',sub('del','cur'),' − ',sub('del','ref'),') + β(',sub('del','cur'),' − ',sub('del','old'),')'],3),
defs('p: xác suất loại gói hiện tại; p_old: xác suất ở chu kỳ trước; del_cur: độ trễ hàng đợi hiện tại; del_old: độ trễ hàng đợi ở chu kỳ trước; del_ref: độ trễ tham chiếu; α, β: các hệ số điều chỉnh.'),
label('Độ trễ hàng đợi'),
eq([sub('del','cur'),' = ',frac([sub('q','len')],[sub('dq_rate','avg')])],4),
defs('q_len: lượng dữ liệu trong hàng đợi; dq_rate_avg: tốc độ trung bình của dữ liệu rời hàng đợi.'),
label('Tốc độ dữ liệu rời hàng đợi'),
eq([sub('dq','rate'),' = ',frac([sub('dq','count')],[sub('dq','time')])],5),
defs('dq_rate: tốc độ dữ liệu rời hàng đợi trong lần đo; dq_count: lượng dữ liệu đã rời hàng đợi trong lần đo; dq_time: thời gian đo. q_len và dq_count dùng cùng đơn vị.'),
label('Tốc độ trung bình rời hàng đợi'),
eq([sub('dq_rate','avg'),' = (1 − ε) × ',sub('dq_rate_avg','old'),' + ε × ',sub('dq','rate')],6),
defs('dq_rate_avg_old: tốc độ trung bình ở lần cập nhật trước; ε: hệ số làm trơn.'),
label('Giá trị truy vấn của gói tin'),
eq([sub('m','res'),' = Query(key)'],7),
defs('m_res: tần suất ước lượng của luồng tương ứng với gói tin; Query(key): kết quả truy vấn Sketch theo khóa key.'),
label('Tỷ trọng của luồng dữ liệu'),
eq([sub('G','k'),' = ',frac([sub('m','res')],[sub('m','count')])],8),
defs('Gk: tỷ trọng ước lượng của luồng k; m_count: tổng số gói đã được thống kê trong cửa sổ hiện tại.'),
label('Ngưỡng phân biệt luồng'),
eq([sub('G','Threshold'),' = ',frac([sigma([sub('m','res'),' × ',sub('G','k')])],[sigma([sub('m','res')])])],9),
defs('GThreshold: ngưỡng phân biệt luồng; n: số luồng được xét; i: chỉ số luồng trong phép tổng. m_res và Gk trong mỗi số hạng là các giá trị tương ứng của luồng đang xét.'),
paragraph('Điều kiện loại gói của luồng lớn: Gk > GThreshold.')
]

measure=[
label('Độ dài hàng đợi trung bình: phản ánh mức tồn đọng gói tin tại router. Giá trị càng lớn thì thời gian chờ trong hàng đợi thường càng cao.'),
eq(['m = ',sub('m','ptc'),' × (nTime − sTime)'],10),
eq([sub('new_q','Avg'),' = qW × nPkt + ',sub('old_q','Avg'),' × ',sup(['(1 − qW)'],'m')],11),
defs('m: hệ số xét khoảng thời gian hàng đợi rỗi; m_ptc: hằng số tốc độ gói; nTime: thời điểm hiện tại; sTime: thời điểm bắt đầu khoảng rỗi; new_qAvg: độ dài hàng đợi trung bình mới; old_qAvg: độ dài hàng đợi trung bình trước đó; qW: trọng số của mẫu hàng đợi; nPkt: số gói đi vào hàng đợi trong khoảng xét.'),
paragraph('Độ trễ khứ hồi RTT: thời gian từ lúc nguồn gửi dữ liệu đến khi nhận ACK tương ứng. RTT được dùng để đánh giá độ trễ truyền thông.'),
label('Thông lượng: lượng gói tin nhận thành công trong một đơn vị thời gian.'),
eq(['Throughput = ',frac(['N'],['T'])],12),
defs('N: tổng số gói nhận được tại các nút đích trong khoảng đo; T: thời gian đo; Throughput: thông lượng, đơn vị gói/giây trong công thức này.'),
label('Chỉ số công bằng Jain: đánh giá mức chia sẻ thông lượng giữa các luồng. Giá trị càng gần 1 thì các luồng càng có thông lượng đồng đều.'),
eq(['FairnessIndex = ',frac([sup(['(',sigma([sub('th','i')]),')'],'2')],['n ',sigma([sup([sub('th','i')],'2')])])],13),
defs('thᵢ: thông lượng của luồng i; n: số luồng; FairnessIndex: chỉ số công bằng Jain.'),
paragraph('Số gói tin bị loại: thống kê riêng gói bị loại chủ động bởi AQM và gói bị loại do hàng đợi đầy. Chỉ số này được xem xét cùng thông lượng và độ trễ để đánh giá khả năng xử lý tắc nghẽn.')
]

removed=[]
removed_xml=[]
cursor=start.getnext()
while cursor is not end:
    nxt=cursor.getnext();removed_xml.append(E.tostring(cursor));removed.append(cursor);body.remove(cursor);cursor=nxt
anchor=start
for p in formulas:anchor.addnext(p);anchor=p

summary=next(p for p in body.findall('w:p',NS) if txt(p).startswith('Kết quả đánh giá của bài báo cho thấy'))
cursor=metric.getnext()
while cursor is not summary:
    nxt=cursor.getnext();removed_xml.append(E.tostring(cursor));removed.append(cursor);body.remove(cursor);cursor=nxt
anchor=metric
for p in measure:anchor.addnext(p);anchor=p

remaining=[b for b in before if b not in removed_xml]
after=[E.tostring(x) for x in body if x not in formulas and x not in measure]
assert remaining==after,'Unexpected change outside the two requested blocks'

payload=E.tostring(root,encoding='UTF-8',xml_declaration=True,standalone=True)
tmp=ROOT/'analysis_sources'/'equations-revised.docx'
with ZipFile(tmp,'w') as z:
    for info,data in entries:z.writestr(info,payload if info.filename=='word/document.xml' else data)
TARGET.write_bytes(tmp.read_bytes())
assert len(root.xpath('//m:oMath',namespaces=NS))==13
print('Only formula and measurement blocks changed; 13 editable equations present.')
