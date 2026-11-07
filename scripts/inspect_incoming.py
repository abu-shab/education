"""Reproducible source inspection; no academic facts are inferred here."""
from pathlib import Path
import json
import pymupdf
from config import DATA

def main():
    out=DATA/'inspection';out.mkdir(exist_ok=True)
    summary=[]
    for path in sorted((DATA/'incoming').glob('*.pdf')):
        with pymupdf.open(path) as pdf:
            pages=[]
            for i,page in enumerate(pdf):
                tables=[]
                try:
                    for t in page.find_tables().tables:
                        tables.append({'bbox':list(t.bbox),'rows':t.extract()})
                except Exception as e:
                    tables.append({'error':type(e).__name__})
                pages.append({'page':i+1,'text':page.get_text(sort=True),'raw_text':page.get_text(),
                              'tables':tables,'words':page.get_text('words')})
            record={'filename':path.name,'page_count':len(pdf),'metadata':pdf.metadata,'pages':pages}
            (out/(path.stem+'.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
            (out/(path.stem+'.txt')).write_text('\n\n'.join(f'PAGE {p["page"]}\n{p["text"]}' for p in pages),encoding='utf-8')
            summary.append({'file':path.name,'pages':len(pdf),'tables':sum(len(p['tables']) for p in pages),
                            'characters':sum(len(p['text']) for p in pages)})
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
