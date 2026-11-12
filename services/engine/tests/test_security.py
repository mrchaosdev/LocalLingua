import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from app.main import app, session_token
from app.config import Settings

AUTH = {'Authorization':'Bearer '+session_token}

def test_local_api_requires_token_and_origin():
    with TestClient(app,base_url='http://127.0.0.1:8765') as client:
        assert client.get('/api/status').status_code == 401
        assert client.get('/api/status',headers=AUTH).status_code == 200
        assert client.post('/api/control',json={'mode':'stop'},headers={**AUTH,'Origin':'https://evil.example'}).status_code == 403

def test_reject_remote_ollama():
    with pytest.raises(ValueError): Settings(ollama_url='https://api.example.com')

def test_websocket_rejects_foreign_origin():
    with TestClient(app,base_url='http://127.0.0.1:8765') as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect('/ws/events',headers={**AUTH,'Origin':'https://evil.example'}): pass
