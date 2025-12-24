from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
from os.path import exists, dirname

# init SQLAlchemy so we can use it later in our models
db = SQLAlchemy()
_KEY_LENGTH_ = 64


def create_app(testing=None, database=None):
    # Definir caminho padrão absoluto se não fornecido
    if database is None:
        # Pega o diretório pai de 'src' (raiz do projeto)
        basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        database = os.path.join(basedir, 'src', 'database', 'sqlite.db')

    load_dotenv()

    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.getenv(
        "SECRET_KEY") or 'secret-key-goes-here'
    if(testing is None or testing is False):
        # Garantir URI absoluta compatível com SQLAlchemy (3 barras + caminho absoluto)
        # O SQLAlchemy trata corretamente caminhos com letras de drive no Windows
        abs_db_path = os.path.abspath(database)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + abs_db_path
    else:
        # in-memory db for testing
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'main.index'
    login_manager.init_app(app)

    # Importar todos os modelos ANTES de criar as tabelas
    from .models import User, Product, Client, Key, Registration, Changelog, Validationlog  # pylint: disable=C0415
    from .auth import auth as auth_blueprint  # pylint: disable=C0415
    from .main import main as main_blueprint  # pylint: disable=C0415

    @ login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # blueprint for auth routes in our app
    app.register_blueprint(auth_blueprint)

    # blueprint for non-auth parts of app
    app.register_blueprint(main_blueprint)

    with app.app_context():
        # Extrair o caminho do arquivo do URI do SQLite
        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        # Garantir que o diretório existe
        if db_path != ':memory:':
            db_dir = dirname(db_path)
            if db_dir and not exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
        
        # Verificar se o banco existe e se tem as colunas necessárias
        needs_recreate = False
        if exists(db_path):
            try:
                # Verificar se as novas colunas existem
                from sqlalchemy import inspect
                inspector = inspect(db.engine)
                columns = [col['name'] for col in inspector.get_columns('key')]
                required_columns = ['expirytype', 'expirydays', 'activationdate']
                if not all(col in columns for col in required_columns):
                    print("Database schema outdated. Recreating database...", flush=True)
                    needs_recreate = True
            except Exception as e:
                print(f"Error checking database schema: {e}. Recreating database...", flush=True)
                needs_recreate = True
        else:
            needs_recreate = True
        
        # Recriar o banco se necessário
        if needs_recreate:
            if exists(db_path):
                db.drop_all()
            db.create_all()
            print("Database created successfully with new schema.", flush=True)
        
        from . import database_api as DBAPI  # pylint: disable=C0415
        DBAPI.generateUser(os.getenv("ADMINUSERNAME"), os.getenv(
            "ADMINPASSWORD"), os.getenv("ADMINEMAIL"))

    return app
