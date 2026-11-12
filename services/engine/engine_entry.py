"""PyInstaller entry point, loopback only. No transcript or audio logging."""
import uvicorn
from app.main import app

if __name__ == '__main__':
    config = uvicorn.Config(app, host='127.0.0.1', port=8765, access_log=False,
                            ws_max_size=262144, ws_max_queue=8, log_level='warning')
    server = uvicorn.Server(config)
    app.state.shutdown = lambda: setattr(server, 'should_exit', True)
    server.run()
