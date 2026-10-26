from App import create_app
from App.route import app,socketio
import os

app = create_app(app)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    use_socketio = os.environ.get('USE_SOCKETIO', 'True').lower() == 'true'
    # 偵錯模式預設關閉；開發時在 .env 設 FLASK_DEBUG=true
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'

    if use_socketio:
        socketio.run(app, debug=debug, host='0.0.0.0', port=port)
    else:
        app.run(debug=debug, host='0.0.0.0', port=port)
