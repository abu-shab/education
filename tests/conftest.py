import pytest
from pathlib import Path
from rag import store
from rag.ingestion import ingest
from rag.retrieval import retriever
from config import ROOT

@pytest.fixture(scope='session', autouse=True)
def isolated_database(tmp_path_factory):
    """Tests never modify the user's live data or call Gemini."""
    original = store.DATA
    folder = tmp_path_factory.mktemp('academia')
    store.DATA = folder
    store.init()
    for name, title, kind, id in [('fictional_regulations.txt','Fictional regulations','regulations','demo-regs'),
                                 ('fictional_plan.txt','Fictional plan','plan','demo-plan')]:
        ingest(ROOT / 'sample_data' / name, title=title, version='DEMO-2026', program='DEMO-CS', synthetic=True, kind=kind, doc_id=id)
    model_loader = retriever.load_model
    retriever.load_model = lambda: False
    retriever.refresh()
    yield folder
    retriever.load_model = model_loader
    store.DATA = original

@pytest.fixture(autouse=True)
def no_network_provider(monkeypatch):
    from providers.gemini import provider, ProviderUnavailable
    def disabled(*args, **kwargs):
        raise ProviderUnavailable('test_offline', 'Gemini disabled in tests')
    monkeypatch.setattr(provider, 'generate', disabled)
