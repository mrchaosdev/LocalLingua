from fastapi.testclient import TestClient
from app.main import app,session_token

AUTH={'Authorization':'Bearer '+session_token}

def test_health_and_control():
    with TestClient(app,base_url='http://127.0.0.1:8765',headers=AUTH) as client:
        assert client.get('/health').json()['ok'] is True
        assert client.post('/api/control', json={'mode':'start'}).json()['mode']=='start'
        assert client.post('/api/control', json={'mode':'stop'}).json()['mode']=='stop'

def test_demo_ws():
    with TestClient(app,base_url='http://127.0.0.1:8765',headers=AUTH) as client:
        with client.websocket_connect('/ws/events',headers=AUTH) as ws:
            assert ws.receive_json()['type']=='status'
            assert client.post('/api/demo').status_code == 200
            # Receives at least the first event; demo is synthetic.
            event=ws.receive_json()
            assert event['type']=='caption'
            assert event['source']=='demo'
