import json
from types import SimpleNamespace
import pytest
import providers.gemini as module

class FakeClient:
    def __init__(self, replies):
        self.replies=iter(replies);self.calls=0;self.models=self
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def generate_content(self,**kwargs):
        self.calls+=1
        reply=next(self.replies)
        if isinstance(reply,Exception):raise reply
        return SimpleNamespace(text=json.dumps(reply),usage_metadata=None)

class APIError(Exception):
    def __init__(self,code):self.code=code

@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setattr(module,'configuration',lambda:{'verified':True,'model':'gemini-3.5-flash-lite'})
    monkeypatch.setattr(module.time,'sleep',lambda n:None)
    monkeypatch.setenv('GEMINI_DAILY_REQUEST_LIMIT','10000')
    return module.GeminiProvider()

@pytest.mark.parametrize('code,expected',[(429,'quota_exhausted'),(403,'permission_denied'),(401,'invalid_key_or_request'),(404,'model_unavailable')])
def test_non_transient_errors_no_retry(configured,monkeypatch,code,expected):
    fake=FakeClient([APIError(code)]);monkeypatch.setattr(module,'client',lambda:fake)
    with pytest.raises(module.ProviderUnavailable) as e:configured.generate('q',[{'id':'x','text':'80%','synthetic':True}])
    assert e.value.code==expected and fake.calls==1

def test_transient_retries_are_bounded(configured,monkeypatch):
    fake=FakeClient([APIError(503),APIError(503)]);monkeypatch.setattr(module,'client',lambda:fake)
    with pytest.raises(module.ProviderUnavailable):configured.generate('q',[{'id':'x','text':'80%','synthetic':True}])
    assert fake.calls==2

@pytest.mark.parametrize('claim,code',[
    ({'text':'Attendance is 80%.','evidence_ids':['invented']},'invalid_citations'),
    ({'text':'Attendance is 70%.','evidence_ids':['x']},'unsupported_numbers')])
def test_generated_claim_validation(configured,monkeypatch,claim,code):
    fake=FakeClient([{'status':'answered','claims':[claim],'message':''}]);monkeypatch.setattr(module,'client',lambda:fake)
    with pytest.raises(module.ProviderUnavailable) as e:configured.generate('q',[{'id':'x','text':'Attendance 80%','synthetic':True}])
    assert e.value.code==code

def test_uncited_free_text_removed(configured,monkeypatch):
    fake=FakeClient([{'status':'answered','claims':[{'text':'80%','evidence_ids':['x']}],'message':'Invented academic policy'}]);monkeypatch.setattr(module,'client',lambda:fake)
    result,_=configured.generate('q',[{'id':'x','text':'80%','synthetic':True}])
    assert result.message==''

def test_busy_concurrency_rejected(configured):
    configured.lock.acquire()
    with pytest.raises(module.ProviderUnavailable) as e:configured.generate('q',[])
    assert e.value.code=='busy'
    configured.lock.release()

def test_daily_cap_no_network(configured,monkeypatch):
    monkeypatch.setenv('GEMINI_DAILY_REQUEST_LIMIT','0')
    with pytest.raises(module.ProviderUnavailable) as e:configured.generate('q',[])
    assert e.value.code=='daily_cap'

def test_timeout_is_sanitized_and_not_retried(configured,monkeypatch):
    fake=FakeClient([TimeoutError('credential-bearing details must never be exposed')]);monkeypatch.setattr(module,'client',lambda:fake)
    with pytest.raises(module.ProviderUnavailable) as e:configured.generate('q',[])
    assert e.value.code=='service_unavailable' and 'credential' not in str(e.value) and fake.calls==1

def test_unverified_provider_never_calls_network(monkeypatch):
    monkeypatch.setattr(module,'configuration',lambda:{'verified':False})
    provider=module.GeminiProvider()
    with pytest.raises(module.ProviderUnavailable) as e:provider.generate('q',[])
    assert e.value.code=='not_verified'

def test_context_budget_is_bounded(configured):
    with pytest.raises(module.ProviderUnavailable) as e:configured.generate('q',[{'text':'x'*30001}])
    assert e.value.code=='context_too_large'
