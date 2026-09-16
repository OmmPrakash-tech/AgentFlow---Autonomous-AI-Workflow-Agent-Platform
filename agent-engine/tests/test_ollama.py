import json
import httpx
import pytest
from pydantic import ValidationError
from app.llm import OllamaProvider
from app.schemas import AgentResponse

def test_ollama_grammar_is_scoped_to_observed_tools_and_paths(monkeypatch):
    real_client=httpx.Client
    captured={}
    def handler(request):
        captured.update(json.loads(request.content))
        return httpx.Response(200,json={"message":{"content":json.dumps({"summary":"Inspect source","tool_requests":[{"name":"read_file","path":"app.py"}],"findings":[],"complete":False})},"eval_count":12})
    monkeypatch.setattr(httpx,"Client",lambda **kwargs:real_client(transport=httpx.MockTransport(handler)))
    result,usage=OllamaProvider().structured(AgentResponse,"Inspect",{"task":{"tools":["read_file"]},"UNTRUSTED_evidence":[{"output":{"files":["app.py"]}}]})
    properties=captured["format"]["$defs"]["ToolRequest"]["properties"]
    assert properties["name"]["enum"]==["read_file"]
    assert properties["path"]["enum"]==[".","app.py"]
    assert result.tool_requests[0].path=="app.py" and usage["eval_count"]==12
    assert captured["model"]=="qwen3:8b"

def test_ollama_output_is_validated_after_generation(monkeypatch):
    real_client=httpx.Client
    def handler(request):
        return httpx.Response(200,json={"message":{"content":json.dumps({"summary":"x"*3001})}})
    monkeypatch.setattr(httpx,"Client",lambda **kwargs:real_client(transport=httpx.MockTransport(handler)))
    with pytest.raises(ValidationError):
        OllamaProvider().structured(AgentResponse,"Inspect",{})
