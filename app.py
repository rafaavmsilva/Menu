from flask import Flask, render_template, redirect
import os
import sys
import subprocess
import time

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'development_key')

# Configure session
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30 minutes

# Import blueprints
from Comissoes import comissoes_blueprint
from financeiro.routes import financeiro_blueprint

# Configure blueprint paths
comissoes_blueprint.static_folder = os.path.join('Comissoes', 'static')
comissoes_blueprint.template_folder = os.path.join('Comissoes', 'templates')

financeiro_blueprint.template_folder = os.path.join('financeiro', 'templates')
financeiro_blueprint.static_folder = os.path.join('financeiro', 'static')

# Register blueprints
app.register_blueprint(comissoes_blueprint, url_prefix='/comissoes')
app.register_blueprint(financeiro_blueprint, url_prefix='/financeiro')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/redirect/comissoes')
def redirect_comissoes():
    """Start and redirect to the comissoes module."""
    # Check if we're in production (Render) or local development
    if os.environ.get('RENDER'):
        # In production, just redirect to the comissoes port
        return redirect('http://127.0.0.1:5001/')
    else:
        # In local development, start the app
        comissoes_app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Comissoes.af360bank', 'app.py')
        try:
            # Start the Comissoes app in a new window
            if os.name == 'nt':  # Windows
                process = subprocess.Popen(
                    [sys.executable, comissoes_app_path],
                    cwd=os.path.dirname(comissoes_app_path),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:  # Linux/Unix
                process = subprocess.Popen(
                    [sys.executable, comissoes_app_path],
                    cwd=os.path.dirname(comissoes_app_path),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            
            # Wait a moment for the app to start
            time.sleep(3)
            
            # Check if process started successfully
            if process.poll() is None:  # Process is still running
                return redirect('http://127.0.0.1:5001/')
            else:
                # Process failed to start
                out, err = process.communicate()
                print(f"Error starting Comissoes app: {err.decode()}")
                return "Failed to start Comissoes app. Please check the console for errors.", 500
                
        except Exception as e:
            print(f"Error starting Comissoes app: {e}")
            return f"Error: {str(e)}", 500

@app.route('/redirect/financeiro')
def redirect_financeiro():
    """Start and redirect to the financeiro module."""
    # Check if we're in production (Render) or local development
    if os.environ.get('RENDER'):
        # In production, just redirect to the financeiro port
        return redirect('http://127.0.0.1:5002/')
    else:
        # In local development, start the app
        financeiro_app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'financeiro.af360bank', 'run.py')
        try:
            # Start the Financeiro app in a new window
            if os.name == 'nt':  # Windows
                process = subprocess.Popen(
                    [sys.executable, financeiro_app_path],
                    cwd=os.path.dirname(financeiro_app_path),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:  # Linux/Unix
                process = subprocess.Popen(
                    [sys.executable, financeiro_app_path],
                    cwd=os.path.dirname(financeiro_app_path),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            
            # Wait a moment for the app to start
            time.sleep(3)
            
            # Check if process started successfully
            if process.poll() is None:  # Process is still running
                return redirect('http://127.0.0.1:5002/')
            else:
                # Process failed to start
                out, err = process.communicate()
                print(f"Error starting Financeiro app: {err.decode()}")
                return "Failed to start Financeiro app. Please check the console for errors.", 500
                
        except Exception as e:
            print(f"Error starting Financeiro app: {e}")
            return f"Error: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
