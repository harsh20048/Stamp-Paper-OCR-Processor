from flask import Flask
from flask_socketio import SocketIO
from config import config
import os

config_mode = os.environ.get('FLASK_ENV', 'default')

app = Flask(__name__, 
    static_folder='static',
    template_folder='templates'
)
app.config.from_object(config[config_mode])
socketio = SocketIO(app)
config[config_mode].init_app(app)

# Import routes at the end
from app import routes