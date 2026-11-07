"""Read-only inspection outputs; the guide is never ingested into the academic KB."""
from pathlib import Path
import json
import subprocess
import cv2
import imageio_ffmpeg
import pymupdf

root = Path(__file__).resolve().parents[1]
out = root / 'tmp' / 'materials'
out.mkdir(parents=True, exist_ok=True)
pdf = next(root.glob('*.pdf'))
with pymupdf.open(pdf) as doc:
    text = '\n\n'.join(f'PAGE {i+1}\n{p.get_text(sort=True)}' for i, p in enumerate(doc))
    (out / 'guide.txt').write_text(text, encoding='utf-8')
    for i in (3, 6, 7):
        doc[i].get_pixmap(matrix=pymupdf.Matrix(1.4, 1.4)).save(out / f'guide-{i+1}.png')
video = next(root.glob('*.mp4'))
cap = cv2.VideoCapture(str(video))
fps = cap.get(cv2.CAP_PROP_FPS)
duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
for i, t in enumerate([0, duration * .25, duration * .5, duration * .75, max(0, duration-2)]):
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, frame = cap.read()
    if ok:
        cv2.imwrite(str(out / f'video-{i}.jpg'), frame)
cap.release()
probe = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-i', str(video)], capture_output=True, text=True)
(out / 'video-probe.txt').write_text(probe.stderr, encoding='utf-8')
print(json.dumps({'guide_pages': 10, 'video_seconds': duration, 'outputs': str(out)}))
