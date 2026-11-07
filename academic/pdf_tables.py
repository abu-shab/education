"""Geometry-aware extraction of the supplied Hebron plan grids.

The built-in table finder is retained in inspection files. This adapter uses
actual PDF grid borders and original cell text because that finder splits
several of these grids into spurious narrow columns.
"""
import re
import pymupdf

COURSE_CODE = re.compile(r'(?:[A-Za-z]{1,6}\d{3,6}|\d{5}|\d{2,3}[A-Za-z]{1,3}\d{1,3})')

def compact(text):
    return re.sub(r'\s+', ' ', text).strip()

def clusters(values,tolerance=2):
    groups=[]
    for value in sorted(values):
        if groups and value-groups[-1][-1]<tolerance:groups[-1].append(value)
        else:groups.append([value])
    return [sum(g)/len(g) for g in groups]

def borders(page):
    horizontal=[];vertical=[]
    for drawing in page.get_drawings():
        for item in drawing['items']:
            if item[0]=='re':
                r=item[1]
                if r.height<2 and r.width>25:horizontal.append((r.x0,r.x1,(r.y0+r.y1)/2))
                if r.width<2 and r.height>5:vertical.append(((r.x0+r.x1)/2,r.y0,r.y1))
            elif item[0]=='l':
                a,b=item[1:3]
                if abs(a.y-b.y)<1 and abs(a.x-b.x)>25:horizontal.append((min(a.x,b.x),max(a.x,b.x),(a.y+b.y)/2))
                if abs(a.x-b.x)<1 and abs(a.y-b.y)>5:vertical.append(((a.x+b.x)/2,min(a.y,b.y),max(a.y,b.y)))
    return horizontal,vertical

def extract_course_rows(page):
    h,v=borders(page);rows=[];seen=set();issues=[]
    for word in page.get_text('words'):
        x0,y0,x1,y1,code,*_=word
        if not COURSE_CODE.fullmatch(code) or x0 < page.rect.width*.45:continue
        cx,cy=(x0+x1)/2,(y0+y1)/2
        ys=clusters([y for a,b,y in h if a-2<=cx<=b+2],1)
        above=[y for y in ys if y<cy];below=[y for y in ys if y>cy]
        if not above or not below:continue
        top,bottom=max(above),min(below)
        if bottom-top>100:continue
        xs=clusters([x for x,a,b in v if a-2<=cy<=b+2],2)
        left=[x for x in xs if x<cx];right=[x for x in xs if x>cx]
        if len(left)<4 or not right:
            issues.append({'code_candidate':code,'reason':'Cannot identify five source columns','bbox':[x0,y0,x1,y1]})
            continue
        # Two actual source layouts differ: the standalone cybersecurity plan
        # places code BEFORE Arabic name. Detect that geometric position.
        code_index=len(left)-1
        if code_index not in (3,4):
            issues.append({'code_candidate':code,'reason':'Unexpected code-column position','bbox':[x0,y0,x1,y1]})
            continue
        bounds=xs[:6]
        if len(bounds)<6:continue
        cells=[]
        for a,b in zip(bounds,bounds[1:]):
            cells.append(compact(page.get_text('text',clip=pymupdf.Rect(a+.7,top+.1,b-.7,bottom-.1),sort=False)))
        if tuple((round(top,1),code)) in seen:continue
        seen.add((round(top,1),code))
        english,prerequisite,credits=cells[:3]
        if code_index==4:arabic,raw_code=cells[3:5]
        else:raw_code,arabic=cells[3:5]
        status='extracted_unverified';reasons=[]
        if compact(raw_code)!=code:reasons.append('Course-code cell differs from the code word')
        if not re.fullmatch(r'[0-6](?:\.5)?',credits):reasons.append('Missing or invalid credit cell')
        if not re.search('[A-Za-z]',english):reasons.append('English-name column missing')
        if not re.search('[\u0600-\u06ff]',arabic):reasons.append('Arabic-name column missing')
        rows.append({'code':code,'name_ar':arabic,'name_en':english,
            'credit_hours':float(credits) if re.fullmatch(r'[0-6](?:\.5)?',credits) else None,
            'prerequisite_expression':prerequisite or None,
            'prerequisite_presence':'blank_unknown' if not prerequisite else 'explicit',
            'bbox':[bounds[0],top,bounds[-1],bottom], 'code_bbox':[x0,y0,x1,y1],
            'raw_cells':cells,'validation_issues':reasons,'review_status':status})
    return sorted(rows,key=lambda r:r['bbox'][1]),issues
