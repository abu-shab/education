"""Download one multilingual model, recording the immutable resolved revision."""
import json
import os
from pathlib import Path
from huggingface_hub import HfApi, snapshot_download
from config import DATA

def main():
    model = os.getenv('EMBEDDING_MODEL', 'intfloat/multilingual-e5-small')
    requested = os.getenv('EMBEDDING_REVISION') or 'main'
    revision = HfApi().model_info(model, revision=requested).sha
    local = snapshot_download(model, revision=revision,
        allow_patterns=['*.json', '*.safetensors', 'tokenizer*', '*.txt', '*.model', '1_Pooling/*'],
        ignore_patterns=['onnx/*', 'openvino/*'])
    from sentence_transformers import SentenceTransformer
    encoder = SentenceTransformer(local, device='cpu', local_files_only=True)
    test = encoder.encode(['query: ما قواعد الحضور؟', 'passage: وثيقة تجريبية عن الحضور'], normalize_embeddings=True)
    info = {'model': model, 'revision': revision, 'local_path': local, 'dimensions': int(test.shape[1]), 'device': 'cpu'}
    (DATA / 'embedding_model.json').write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in info.items() if k != 'local_path'}))

if __name__ == '__main__':
    main()
