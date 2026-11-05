from pathlib import Path
from copy import deepcopy
import re
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path(__file__).resolve().parent.parent
src=ROOT/'Report NS3 DGHNM - Cap nhat cong thuc.docx'
out=ROOT/'Report NS3 DGHNM - Dinh dang bao cao.docx'
d=Document(src)
def content():
    return [re.sub(r'\s+','',''.join(p._p.xpath('.//w:t/text() | .//m:t/text()'))) for p in d.paragraphs]
before=content()
math_before=len(d._element.xpath('//m:oMath'))
for sec in d.sections:
    sec.page_width=Cm(21);sec.page_height=Cm(29.7)
    sec.left_margin=Cm(3);sec.right_margin=Cm(2)
    sec.top_margin=Cm(2);sec.bottom_margin=Cm(2)
    sec.footer_distance=Cm(1)

for name,size in [('normal',13),('Title',16),('Heading 1',15),('Heading 2',14),('Heading 3',13),('Formula Label',13),('Definition',12),('Algorithm',12.5)]:
    if name not in d.styles:d.styles.add_style(name,WD_STYLE_TYPE.PARAGRAPH)
    st=d.styles[name];st.font.name='Times New Roman';st.font.size=Pt(size)
    st.font.color.rgb=RGBColor(0,0,0)
    st.font.bold=name in ['Title','Heading 1','Heading 2','Heading 3','Formula Label']
    if name!='normal':st.base_style=d.styles['normal']
    pf=st.paragraph_format;pf.line_spacing=1.15;pf.space_after=Pt(6)
    pf.space_before=Pt(0);pf.widow_control=True
    pf.keep_with_next=name in ['Title','Heading 1','Heading 2','Heading 3','Formula Label']
    if name.startswith('Heading'):
        pf.space_before=Pt(10);pf.space_after=Pt(5)

main={'Vấn đề đặt ra','Thuật toán S-PIE','Đặc điểm của giải pháp S-PIE','Cách thức hoạt động của S-PIE','Phương pháp thí nghiệm'}
subs={'Cấu trúc dữ liệu Sketch','Các công thức','Mã giả','Mô hình thí nghiệm','Các kịch bản mạng','Các thông số đo đạc'}
labels={'Cập nhật bộ đếm Sketch','Truy vấn tần suất luồng','Xác suất loại bỏ gói tin','Độ trễ hàng đợi','Tốc độ dữ liệu rời hàng đợi','Tốc độ trung bình rời hàng đợi','Giá trị truy vấn của gói tin','Tỷ trọng của luồng dữ liệu','Ngưỡng phân biệt luồng'}
def remove_num(p):
    pr=p._p.get_or_add_pPr()
    for x in list(pr):
        if x.tag==qn('w:numPr'):pr.remove(x)
def font_run(r,size=None):
    r.font.name='Times New Roman';r.font.size=Pt(size) if size else None
    r.font.color.rgb=RGBColor(0,0,0)
    rp=r._element.get_or_add_rPr()
    rf=rp.get_or_add_rFonts()
    for x in ['ascii','hAnsi','eastAsia','cs']:rf.set(qn('w:'+x),'Times New Roman')
    for a in ['asciiTheme','hAnsiTheme','eastAsiaTheme','cstheme']:
        if rf.get(qn('w:'+a)) is not None:del rf.attrib[qn('w:'+a)]

formula_indices=[]
for i,p in enumerate(d.paragraphs):
    t=p.text.strip();pf=p.paragraph_format
    p.style=d.styles['normal']
    pf.left_indent=Cm(0);pf.right_indent=Cm(0);pf.first_line_indent=Cm(1)
    pf.space_before=Pt(0);pf.space_after=Pt(6);pf.line_spacing=1.15
    pf.keep_with_next=False;pf.keep_together=False;pf.widow_control=True
    p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
    # Clear paragraph-level run properties so inherited font/marker sizes are consistent.
    pr=p._p.get_or_add_pPr()
    for x in list(pr):
        if x.tag in [qn('w:rPr'),qn('w:pBdr'),qn('w:shd')]:pr.remove(x)
    for r in p.runs:font_run(r)
    if i in [0,1]:
        p.style=d.styles['Title'];remove_num(p)
        p.alignment=WD_ALIGN_PARAGRAPH.CENTER;pf.first_line_indent=Cm(0)
        pf.space_after=Pt(8 if i==1 else 4);pf.line_spacing=1.0
        pf.keep_with_next=True
        for r in p.runs:r.bold=True
        if i==1:
            title_text=p.text
            p.clear()
            a,b=title_text.split('THUẬT TOÁN',1)
            r=p.add_run(a.rstrip());r.add_break();p.add_run('THUẬT TOÁN'+b)
            for r in p.runs:font_run(r);r.bold=True
    elif t=='Ý tưởng chính của bài báo' or t in main or t in subs:
        level=1 if t=='Ý tưởng chính của bài báo' else 2 if t in main else 3
        p.style=d.styles[f'Heading {level}']
        p.alignment=WD_ALIGN_PARAGRAPH.LEFT
        pf.left_indent=Cm(0.75);pf.first_line_indent=Cm(-0.75)
        pf.space_before=Pt(12 if level==1 else 9);pf.space_after=Pt(5)
        pf.line_spacing=1.1;pf.keep_with_next=True;pf.keep_together=True
        for r in p.runs:r.bold=True
    elif t in labels:
        p.style=d.styles['Formula Label'];remove_num(p)
        pf.first_line_indent=Cm(0);pf.space_before=Pt(5);pf.space_after=Pt(2)
        pf.keep_with_next=True
        for r in p.runs:r.bold=True
    elif p._p.xpath('.//m:oMath'):
        remove_num(p);formula_indices.append(i)
        pf.first_line_indent=Cm(0);pf.left_indent=Cm(0);pf.right_indent=Cm(0)
        pf.line_spacing=1.0;pf.space_before=Pt(4);pf.space_after=Pt(4)
        pf.keep_with_next=True;pf.keep_together=True
        p.alignment=WD_ALIGN_PARAGRAPH.LEFT
        pf.tab_stops.clear_all()
        pf.tab_stops.add_tab_stop(Cm(8),WD_TAB_ALIGNMENT.CENTER)
        pf.tab_stops.add_tab_stop(Cm(16),WD_TAB_ALIGNMENT.RIGHT)
        # Move the equation number to the right margin without changing notation.
        om=p._p.xpath('.//m:oMath')[0]
        last=om[-1]
        mt=last.find(qn('m:t'))
        if mt is not None and re.fullmatch(r'\s*\(\d+\)',mt.text or ''):
            number=mt.text.strip();om.remove(last)
            om.getparent().remove(om)
            for old in list(p._p):
                if old.tag==qn('m:oMathPara'):p._p.remove(old)
            p.add_run('\t');p._p.append(om);p.add_run('\t'+number)
        for r in p.runs:font_run(r,12)
        for mr in om.iter(qn('m:r')):
            rp=mr.find(qn('w:rPr'))
            if rp is None:rp=OxmlElement('w:rPr');mr.insert(0,rp)
            sz=OxmlElement('w:sz');sz.set(qn('w:val'),'24');rp.append(sz)
    elif t.startswith('Bước '):
        p.style=d.styles['Algorithm'];remove_num(p)
        pf.left_indent=Cm(0.5);pf.first_line_indent=Cm(0)
        pf.space_after=Pt(3);pf.line_spacing=1.1;pf.keep_together=True
    elif i>0 and d.paragraphs[i-1]._p.xpath('.//m:oMath'):
        p.style=d.styles['Definition'];remove_num(p)
        pf.first_line_indent=Cm(0);pf.space_after=Pt(6);pf.line_spacing=1.1
    else:
        # Keep the existing three feature bullets, format other prose as report paragraphs.
        if i in [10,11,12]:
            pf.left_indent=Cm(0.6);pf.first_line_indent=Cm(-0.45)
        else:remove_num(p)
    if not t and not p._p.xpath('.//m:oMath'):
        pf.space_after=Pt(0);pf.line_spacing=1.0

# Formula labels, formulae and their definitions stay together when pagination permits.
for i in formula_indices:
    if i>0 and not d.paragraphs[i-1]._p.xpath('.//m:oMath'):
        d.paragraphs[i-1].paragraph_format.keep_with_next=True

for sec in d.sections:
    fp=sec.footer.paragraphs[0];fp.alignment=WD_ALIGN_PARAGRAPH.CENTER
    fp.paragraph_format.space_after=Pt(0)
    r=fp.add_run();font_run(r,11)
    fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE')
    rr=OxmlElement('w:r');tt=OxmlElement('w:t');tt.text='1';rr.append(tt);fld.append(rr);fp._p.append(fld)

# Formatting must not change any paragraph text, equation symbols, or equation count.
assert before==content(),'Text or equation content changed'
assert len(d._element.xpath('//m:oMath'))==math_before==13
d.save(out)
print('Paragraph text preserved:',len(before))
print('Equations preserved:',math_before)
print('Formatting saved.')
