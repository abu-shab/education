import shutil
from config import ROOT, DATA
from rag import store
from rag.ingestion import ingest

def seed():
    store.init()
    for name, title, kind, id in [
        ('fictional_regulations.txt', 'لوائح أكاديمية المدار — خيالية للاختبار', 'regulations', 'demo-regs'),
        ('fictional_plan.txt', 'خطة علوم الحاسوب — خيالية للاختبار', 'plan', 'demo-plan')]:
        path = DATA / 'uploads' / name
        shutil.copyfile(ROOT / 'sample_data' / name, path)
        ingest(path, title=title, version='DEMO-2026', program='DEMO-CS', synthetic=True, kind=kind, doc_id=id)
    print('Indexed two clearly fictional test documents. No genuine university policies loaded.')

if __name__ == '__main__':
    seed()
