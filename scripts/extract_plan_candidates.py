from pathlib import Path
import json
import pymupdf
from config import DATA
from academic.pdf_tables import extract_course_rows

def main():
    out=DATA/'inspection'
    for path in sorted((DATA/'incoming').glob('*.pdf')):
        if not any('\u0600'<=c<='\u06ff' for c in path.stem):continue
        pages=[]
        with pymupdf.open(path) as pdf:
            for i,p in enumerate(pdf):
                rows,issues=extract_course_rows(p)
                pages.append({'page':i+1,'rows':rows,'issues':issues})
        result={'filename':path.name,'pages':pages}
        (out/(path.stem+'.candidates.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(path.name,[(p['page'],len(p['rows']),sum(bool(r['validation_issues']) for r in p['rows']),len(p['issues'])) for p in pages])

if __name__=='__main__':main()
