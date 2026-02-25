import os
import socket
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Detectar IP automaticamente
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return '127.0.0.1'

LOCAL_IP = os.environ.get('LOCAL_IP', get_local_ip())

# Configurar servidor para aceitar conexões externas
app.config['SERVER_NAME'] = f'{LOCAL_IP}:5000'
app.config['PREFERRED_URL_SCHEME'] = 'http'

# Configurações de Segurança - CHAVE ÚNICA
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'talentos-budel-2024-secret-key-unique')

# Configuração SQLite com suporte a múltiplos acessos
db_path = os.path.join(os.path.dirname(__file__), 'talentos_budel.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}?check_same_thread=False'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuração de Sessão - COOKIE
app.config['SESSION_COOKIE_NAME'] = 'talentos_budel_session'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 horas

# Configurações de Upload
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Configurações de Email
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')

db = SQLAlchemy(app)
mail = Mail(app)

# Headers de Segurança
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    return response

# Health check
@app.route('/health')
def health():
    return {'status': 'ok', 'ip': LOCAL_IP}

from routes import *
from models import *

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'True') == 'True'
    with app.app_context():
        db.create_all()
    # threaded=True permite múltiplos acessos simultâneos
    print(f"\n🌐 Servidor rodando em: http://{LOCAL_IP}:5000")
    print(f"📱 Acesse pelo celular na mesma rede: http://{LOCAL_IP}:5000\n")
    app.run(debug=debug_mode, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), threaded=True)
