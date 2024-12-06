from flask import Flask, render_template, redirect, url_for
from flask_session import Session
import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    
    # Configurações da aplicação
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'sua_chave_secreta_aqui')
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['SESSION_TYPE'] = 'filesystem'
    
    # Initialize Flask-Session
    Session(app)
    
    # Import blueprints
    from comissoes import comissoes_blueprint
    from financeiro import financeiro_blueprint
    
    # Registrando os blueprints
    app.register_blueprint(comissoes_blueprint, url_prefix='/comissoes')
    app.register_blueprint(financeiro_blueprint, url_prefix='/financeiro')
    
    # Ensure the uploads directory exists
    os.makedirs('uploads', exist_ok=True)
    
    # Logging configuration
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Application startup')
    
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/redirect/comissoes')
    def redirect_comissoes():
        return redirect(url_for('comissoes.index'))
    
    @app.route('/redirect/financeiro')
    def redirect_financeiro():
        return redirect(url_for('financeiro.index'))
    
    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)