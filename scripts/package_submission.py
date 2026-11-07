"""Allowlisted code archive. Never includes .env, user data, caches or credentials."""
from pathlib import Path
import zipfile
from config import ROOT

def main():
    out = ROOT / 'output'
    out.mkdir(exist_ok=True)
    target = out / 'ACADEMIA_AI_submission.zip'
    roots = ['rag','providers','academic','evaluation','tests','scripts','templates','static','sample_data','docs']
    files = ['app.py','config.py','README.md','requirements.txt','requirements-inspection.txt','requirements-lock.txt',
             'env.example','.env.example','.gitignore','TASKS.md','TEAM_HANDOFF.md','DATA_INGESTION_REPORT.md','start.ps1','start.bat']
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for name in files:
            path=ROOT/name
            if path.is_file():z.write(path,name)
        for name in roots:
            for path in (ROOT/name).rglob('*'):
                if not path.is_file() or '__pycache__' in path.parts or path.suffix in ('.pyc','.log'):
                    continue
                z.write(path,path.relative_to(ROOT))
    with zipfile.ZipFile(target) as z:
        names=z.namelist()
        assert '.env' not in names and not any(n.startswith(('data/','.venv/')) for n in names)
    print(f'Created {target.name}: {len(names)} code/documentation files; final Student 3 slides must be added separately.')

if __name__=='__main__':main()
