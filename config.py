from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')
DATA = Path(os.getenv('DATA_DIR', str(ROOT / 'data'))).resolve()
DATA.mkdir(parents=True, exist_ok=True)
(DATA / 'uploads').mkdir(exist_ok=True)
MAX_UPLOAD = int(os.getenv('MAX_UPLOAD_MB', '15')) * 1024 * 1024
CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '1400'))
CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', '150'))
