from flask import Flask, Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
import pandas as pd
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional
import os
from werkzeug.utils import secure_filename
import logging
from logging.handlers import RotatingFileHandler
from flask_session import Session
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from PIL import Image
import io
import pdfkit
import fitz
import tempfile
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
from fpdf import FPDF
import locale
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import inch
from xhtml2pdf import pisa
from io import BytesIO
import imgkit
from PIL import Image, ImageEnhance
import tempfile
import os
import numpy as np
from PIL import Image, ImageEnhance
import cv2
from datetime import datetime

# Initialize Flask app
if __name__ == '__main__':
    app = Flask(__name__)
    app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'development_key')

    # Configure session and app
    app.config.update(
        SESSION_TYPE='filesystem',
        SESSION_COOKIE_SECURE=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
    )

    # Initialize Flask-Session
    Session(app)
else:
    app = Blueprint('comissoes', __name__, 
                template_folder='templates',
                static_folder='static')

app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'development_key')

# Configure session and app
app.config.update(
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=1800,  # 30 minutes
    SESSION_REFRESH_EACH_REQUEST=True,
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max file size
)

# Configure session interface for larger data
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Configure logging
if not app.debug:
    # Ensure the logs directory exists
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Create a file handler
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('App startup')

# Configure debug logging
if app.debug:
    app.logger.setLevel(logging.DEBUG)

@app.before_request
def before_request():
    """Ensure session is initialized with required data structures."""
    if 'dados' not in session:
        session['dados'] = []
    if 'comissoes' not in session:
        session['comissoes'] = {}
    if 'tabela_config' not in session:
        session['tabela_config'] = {}
        set_default_commission_config()
    session.modified = True

def set_default_commission_config():
    """Set default commission configurations for different tables."""
    default_config = {
        'BRAVE 1 - 50 a 250': {
            'tipo_comissao': 'percentual',
            'comissao_recebida': 28,
            'comissao_repassada': 26,
            'valor_minimo': 50,
            'valor_maximo': 250
        },
        'BRAVE 2 - 250,01 - 3800': {
            'tipo_comissao': 'percentual',
            'comissao_recebida': 24,
            'comissao_repassada': 22,
            'valor_minimo': 250.01,
            'valor_maximo': 3800
        },
        'BRAVE 3 - 3800,01 - 30.000': {
            'tipo_comissao': 'fixa',
            'comissao_fixa_recebida': 1200,
            'comissao_fixa_repassada': 1050,
            'valor_minimo': 3800.01,
            'valor_maximo': 30000
        },
        'BRAVE DIFERENCIADA - COM REDUÇÃO': {
            'tipo_comissao': 'percentual',
            'comissao_recebida': 8,
            'comissao_repassada': 6,
            'valor_minimo': 0,
            'valor_maximo': float('inf')
        },
        'VIA INVEST 1 - 75 A 250': {
            'tipo_comissao': 'percentual',
            'comissao_recebida': 26,
            'comissao_repassada': 24,
            'valor_minimo': 75,
            'valor_maximo': 250
        },
        'VIA INVEST 2 - 250,01 A 1.000': {
            'tipo_comissao': 'percentual',
            'comissao_recebida': 21,
            'comissao_repassada': 19,
            'valor_minimo': 250.01,
            'valor_maximo': 1000
        },
        'VIA INVEST 3 - 1.000,01 A 30.000': {
            'tipo_comissao': 'percentual',
            'comissao_recebida': 15,
            'comissao_repassada': 13,
            'valor_minimo': 1000.01,
            'valor_maximo': 30000
        },
        'VIA INVEST DIF - COM REDUÇAO': {
            'tipo_comissao': 'percentual',
            'comissao_recebida': 10,
            'comissao_repassada': 8,
            'valor_minimo': 0,
            'valor_maximo': float('inf')
        },
        'Via AF - TC Diferenciada': {
            'tipo_comissao': 'percentual',
            'comissao_recebida': 0,
            'comissao_repassada': 0,
            'valor_minimo': 0,
            'valor_maximo': float('inf')
        },
        'NÃO COMISSIONADO': {
            'tipo_comissao': 'percentual',
            'comissao_recebida': 0,
            'comissao_repassada': 0,
            'valor_minimo': 0,
            'valor_maximo': float('inf')
        }
    }
    
    session['tabela_config'] = default_config
    session.modified = True

def is_valid_file(filename: str) -> bool:
    """Validate if the file is a CSV or Excel file."""
    if not '.' in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ['csv', 'xls', 'xlsx']

def read_file(file):
    """Read CSV or Excel file into a pandas DataFrame."""
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file, encoding='utf-8-sig')
        elif file.filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(file)
        else:
            raise ValueError("Formato de arquivo não suportado")
        
        if df.empty:
            return None
            
        # Convert DataFrame to list of dictionaries
        dados = df.replace({pd.NA: None}).to_dict('records')
        
        # Log converted data
        app.logger.info(f"Converted data sample: {dados[:2] if dados else 'No data'}")
        
        return dados
    except Exception as e:
        app.logger.error(f"Erro ao ler arquivo: {str(e)}")
        raise e

def convert_to_float(value: str) -> float:
    """Convert a Brazilian currency string to float."""
    try:
        if value is None or pd.isna(value):
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        # Remove any non-numeric characters except comma and dot
        value = ''.join(c for c in str(value) if c.isdigit() or c in '.,')
        if not value:  # Se não houver números após a limpeza
            return 0.0
        # Replace comma with dot for float conversion
        value = value.replace('.', '').replace(',', '.')
        if not value:  # Se ainda não houver números
            return 0.0
        return float(value)
    except Exception as e:
        app.logger.error(f'Erro ao converter valor {value} para float: {str(e)}')
        return 0.0

def format_currency(value: any) -> str:
    """Format a number as Brazilian currency."""
    if value is None or pd.isna(value):
        return ''
    try:
        if isinstance(value, str):
            value = convert_to_float(value)
        return f"R$ {float(value):,.2f}".replace(',', '_').replace('.', ',').replace('_', '.')
    except (ValueError, TypeError):
        return ''

def format_client_name(nome: str, documento: str) -> str:
    """Format client name with document number."""
    if not nome:
        return ''
    if documento:
        return f"{nome} ({documento})"
    return nome

def get_table_config(tabela: str, valor: float = None):
    """Get commission configuration for a table based on value range."""
    try:
        tabela_config = session.get('tabela_config', {})
        
        # Se não houver configuração, retorna configuração padrão
        if not tabela_config:
            return {
                'tipo_comissao': 'percentual',
                'comissao_recebida': 0,
                'comissao_repassada': 0,
                'nome_tabela': tabela
            }
        
        # Se a tabela existir exatamente como está, retorna ela
        if tabela in tabela_config:
            config = tabela_config[tabela]
            config['nome_tabela'] = tabela
            return config
            
        # Se não encontrou a tabela exata, procura pela faixa de valor
        for nome_tabela, config in tabela_config.items():
            # Pula tabelas especiais
            if nome_tabela in ['NÃO COMISSIONADO', 'Via AF - TC Diferenciada']:
                continue
                
            # Se a tabela atual é diferenciada, só procura em tabelas diferenciadas
            if 'DIFERENCIADA' in tabela or 'DIF' in tabela:
                if 'DIFERENCIADA' not in nome_tabela and 'DIF' not in nome_tabela:
                    continue
            # Se a tabela atual é padrão (com números), só procura em tabelas padrão
            else:
                if 'DIFERENCIADA' in nome_tabela or 'DIF' in nome_tabela:
                    continue
            
            valor_minimo = float(config.get('valor_minimo', 0))
            valor_maximo = float(config.get('valor_maximo', float('inf')))
            
            # Verifica se é da mesma empresa (BRAVE ou VIA INVEST)
            mesma_empresa = False
            if tabela.startswith('BRAVE') and nome_tabela.startswith('BRAVE'):
                mesma_empresa = True
            elif tabela.startswith('VIA') and nome_tabela.startswith('VIA'):
                mesma_empresa = True
                
            if mesma_empresa and valor and valor_minimo <= valor <= valor_maximo:
                config['nome_tabela'] = nome_tabela
                return config
        
        # Se não encontrou nenhuma tabela correspondente
        return {
            'tipo_comissao': 'percentual',
            'comissao_recebida': 0,
            'comissao_repassada': 0,
            'nome_tabela': tabela
        }
        
    except Exception as e:
        app.logger.error(f'Erro ao obter configuração da tabela {tabela}: {str(e)}')
        return {
            'tipo_comissao': 'percentual',
            'comissao_recebida': 0,
            'comissao_repassada': 0,
            'nome_tabela': tabela
        }

def calcular_comissoes(dados: List[Dict]):
    """Calculate commissions based on provided data and table configurations."""
    comissoes = {}
    erros = []  # Lista para armazenar erros
    
    try:
        for linha in dados:
            ccb = linha.get("CCB", "")
            erro_linha = {}
            
            # Validação e limpeza do CCB
            if not ccb:
                ccb = f"SEM_CCB_{len(comissoes)}"
                erro_linha['ccb'] = 'CCB não encontrado'
            
            try:
                # Validação e limpeza do valor bruto
                valor_bruto = linha.get('Valor Bruto')
                tabela = linha.get('Tabela', '')
                
                # Format client name
                nome = linha.get('Nome', linha.get('nome', ''))
                documento = linha.get('Documento', linha.get('documento', linha.get('CPF', '')))
                linha['Cliente'] = format_client_name(nome, documento)
                
                if not tabela:
                    erro_linha['tabela'] = 'Tabela não especificada'
                    tabela = 'TABELA_PADRAO'  # Usar uma tabela padrão
                
                # Processamento do valor bruto
                try:
                    valor = convert_to_float(valor_bruto) if valor_bruto else 0
                    if valor <= 0:
                        erro_linha['valor'] = 'Valor Bruto inválido (zero ou negativo)'
                        valor = 0
                except (ValueError, TypeError) as e:
                    erro_linha['valor'] = f'Erro ao converter Valor Bruto: {str(e)}'
                    valor = 0
                
                linha['Valor Bruto'] = valor
                
                # Get table configuration based on value range
                config = get_table_config(tabela, valor)
                if not config:
                    erro_linha['config'] = f'Configuração não encontrada para tabela {tabela}'
                    config = {
                        'tipo_comissao': 'percentual',
                        'comissao_recebida': 0,
                        'comissao_repassada': 0,
                        'nome_tabela': tabela
                    }
                
                # Cálculo das comissões
                try:
                    tipo_comissao = config.get('tipo_comissao', 'percentual')
                    valor_liquido = linha.get('Valor Líquido', 0)
                    if isinstance(valor_liquido, str):
                        valor_liquido = convert_to_float(valor_liquido)
                    
                    # Garantir que valor_liquido seja um número
                    if not valor_liquido or valor_liquido <= 0:
                        valor_liquido = 0
                        app.logger.warning(f"Valor líquido inválido para CCB {ccb}")
                    
                    if tipo_comissao == 'fixa':
                        comissao_recebida_valor = float(config.get('comissao_fixa_recebida', 0))
                        comissao_repassada_valor = float(config.get('comissao_fixa_repassada', 0))
                        comissao_recebida_percentual = (comissao_recebida_valor / valor * 100) if valor > 0 else 0
                        comissao_repassada_percentual = (comissao_repassada_valor / valor_liquido * 100) if valor_liquido > 0 else 0
                    else:
                        # Pegar as porcentagens da configuração
                        comissao_recebida_percentual = float(config.get('comissao_recebida', 0))
                        comissao_repassada_percentual = float(config.get('comissao_repassada', 0))
                        
                        # Calcular valores - recebida sobre bruto, repassada sobre líquido
                        comissao_recebida_valor = valor * (comissao_recebida_percentual / 100)
                        comissao_repassada_valor = valor_liquido * (comissao_repassada_percentual / 100)
                        
                        app.logger.debug(f"""
                        CCB: {ccb}
                        Valor Bruto: {valor}
                        Valor Líquido: {valor_liquido}
                        Comissão Recebida %: {comissao_recebida_percentual}
                        Comissão Repassada %: {comissao_repassada_percentual}
                        Comissão Recebida Valor: {comissao_recebida_valor}
                        Comissão Repassada Valor: {comissao_repassada_valor}
                        """)
                
                    if 'nome_tabela' in config:
                        linha['Tabela'] = config['nome_tabela']
                    
                    linha['comissao_recebida_valor'] = comissao_recebida_valor
                    linha['comissao_repassada_valor'] = comissao_repassada_valor
                    linha['comissao_recebida_percentual'] = comissao_recebida_percentual
                    linha['comissao_repassada_percentual'] = comissao_repassada_percentual
                    linha['tipo_comissao'] = tipo_comissao
                    
                except (ValueError, TypeError) as e:
                    erro_linha['calculo'] = f'Erro ao calcular comissões: {str(e)}'
                    linha['comissao_recebida_valor'] = 0
                    linha['comissao_repassada_valor'] = 0
                    linha['comissao_recebida_percentual'] = 0
                    linha['comissao_repassada_percentual'] = 0
                    linha['tipo_comissao'] = 'percentual'
                
                # Convert other monetary values
                for campo in ['Valor Parcela', 'Valor Líquido']:
                    if campo in linha:
                        try:
                            linha[campo] = convert_to_float(linha[campo])
                        except (ValueError, TypeError) as e:
                            erro_linha[f'conversao_{campo}'] = f'Erro ao converter {campo}: {str(e)}'
                            linha[campo] = 0.0
                
                # Adicionar erros à linha se houver
                if erro_linha:
                    linha['erros'] = erro_linha
                    erros.append({
                        'ccb': ccb,
                        'erros': erro_linha
                    })
                
                comissoes[str(ccb)] = linha
                
            except Exception as e:
                app.logger.error(f'Erro ao processar CCB {ccb}: {str(e)}')
                erro_linha['geral'] = f'Erro geral: {str(e)}'
                erros.append({
                    'ccb': ccb,
                    'erros': erro_linha
                })
                continue
                
    except Exception as e:
        app.logger.error(f'Erro ao calcular comissões: {str(e)}')
        flash('Ocorreu um erro ao calcular as comissões, mas alguns dados foram processados.', 'warning')
    
    # Armazenar erros na sessão para exibição posterior
    session['erros_comissoes'] = erros
    
    return comissoes

@app.route('/', methods=['GET', 'POST'])
def index():
    """Handle the main page and file upload."""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Nenhum arquivo selecionado', 'error')
            return redirect(request.url)
            
        file = request.files['file']
        if file.filename == '':
            flash('Nenhum arquivo selecionado', 'error')
            return redirect(request.url)
            
        if file and is_valid_file(file.filename):
            try:
                dados = read_file(file)
                if dados:
                    session['dados'] = dados
                    flash('Arquivo carregado com sucesso!', 'success')
                    return redirect(url_for('dados'))
                else:
                    flash('O arquivo está vazio ou não contém dados válidos', 'error')
            except Exception as e:
                app.logger.error(f'Erro ao processar arquivo: {str(e)}')
                flash('Erro ao processar o arquivo. Verifique o formato e tente novamente.', 'error')
        else:
            flash('Tipo de arquivo não suportado. Use arquivos CSV ou Excel.', 'error')
            
    return render_template('Index.html')

@app.route('/dados')
def dados():
    """Display uploaded data."""
    dados = session.get('dados')
    if not dados:
        return render_template('error.html')
    return render_template('dados.html', dados=dados)

@app.route('/comissoes')
def comissoes():
    """Calculate and display commissions."""
    try:
        # Check if we have data
        dados = session.get('dados')
        if not dados:
            flash('Nenhum dado encontrado. Por favor, faça o upload do arquivo primeiro.', 'error')
            return redirect(url_for('index'))
        
        # Calculate commissions
        comissoes = calcular_comissoes(dados)
        if not comissoes:
            flash('Não foi possível calcular as comissões. Verifique os dados e tente novamente.', 'error')
            return redirect(url_for('index'))
        
        session['comissoes'] = comissoes
        
        # Get unique tables and users for filters
        tabelas = sorted(list(set(item.get('Tabela', '') for item in dados if item.get('Tabela'))))
        usuarios = sorted(list(set(item.get('Usuario', item.get('Usuário', '')) for item in dados if item.get('Usuario') or item.get('Usuário'))))
        
        # Calculate totals
        total_bruto = sum(float(item.get('Valor Bruto', 0)) for item in comissoes.values())
        total_liquido = sum(float(item.get('Valor Líquido', 0)) for item in comissoes.values())
        total_comissao_recebida = sum(float(item.get('comissao_recebida_valor', 0)) for item in comissoes.values())
        total_comissao_repassada = sum(float(item.get('comissao_repassada_valor', 0)) for item in comissoes.values())
        
        # Get errors if any
        erros = session.get('erros_comissoes', [])
        if erros:
            flash(f'Foram encontrados {len(erros)} problemas durante o processamento. Verifique os detalhes na tabela.', 'warning')
        
        # Convert dict_values to list before passing to template
        comissoes_list = list(comissoes.values())
        
        return render_template('comissoes.html', 
                             comissoes=comissoes_list, 
                             tabelas=tabelas,
                             usuarios=usuarios,
                             erros=erros,
                             totais={
                                 'bruto': total_bruto,
                                 'liquido': total_liquido,
                                 'comissao_recebida': total_comissao_recebida,
                                 'comissao_repassada': total_comissao_repassada
                             })
            
    except Exception as e:
        app.logger.error(f'Erro na rota /comissoes: {str(e)}')
        flash('Ocorreu um erro inesperado. Por favor, tente novamente.', 'error')
        return redirect(url_for('index'))

@app.route('/tabela', methods=['GET'])
def tabela():
    """Render the table configuration page."""
    dados = session.get('dados')
    if not dados:
        return render_template('error.html')
        
    # Get unique tables from the data
    tabelas = sorted(list(set(item['Tabela'] for item in dados if item.get('Tabela'))))
    
    # Get existing configuration
    tabela_config = session.get('tabela_config', {})
    
    # Prepare table data for template
    tabelas_data = {}
    for tabela in tabelas:
        config = tabela_config.get(tabela, {})
        tabelas_data[tabela] = {
            'comissao_recebida': config.get('comissao_recebida', 0),
            'comissao_repassada': config.get('comissao_repassada', 0)
        }
    
    return render_template('tabela.html', tabelas=tabelas_data)

@app.route('/salvar_tabela', methods=['POST'])
def salvar_tabela():
    """Save table configuration for both percentage-based and fixed commission."""
    try:
        tabela = request.form.get('tabela') or request.form.get('tabela_fixa')
        if not tabela:
            flash('Por favor, selecione uma tabela', 'error')
            return redirect(url_for('tabela'))
            
        # Check if it's fixed or percentage commission
        if request.form.get('comissao_fixa_recebida') is not None:
            # Fixed commission
            try:
                comissao_fixa_recebida = float(request.form.get('comissao_fixa_recebida', 0))
                comissao_fixa_repassada = float(request.form.get('comissao_fixa_repassada', 0))
            except ValueError:
                flash('Valores de comissão fixa inválidos', 'error')
                return redirect(url_for('tabela'))
                
            if comissao_fixa_recebida < 0 or comissao_fixa_repassada < 0:
                flash('Os valores de comissão não podem ser negativos', 'error')
                return redirect(url_for('tabela'))
                
            if comissao_fixa_repassada > comissao_fixa_recebida:
                flash('A comissão repassada não pode ser maior que a recebida', 'error')
                return redirect(url_for('tabela'))
                
            config = session.get('tabela_config', {})
            config[tabela] = {
                'tipo_comissao': 'fixa',
                'comissao_recebida': 0,
                'comissao_repassada': 0,
                'comissao_fixa_recebida': comissao_fixa_recebida,
                'comissao_fixa_repassada': comissao_fixa_repassada
            }
        else:
            # Percentage commission
            try:
                comissao_recebida = float(request.form.get('comissao_recebida', 0))
                comissao_repassada = float(request.form.get('comissao_repassada', 0))
            except ValueError:
                flash('Valores de comissão inválidos', 'error')
                return redirect(url_for('tabela'))
                
            if comissao_recebida < 0 or comissao_repassada < 0:
                flash('Os valores de comissão não podem ser negativos', 'error')
                return redirect(url_for('tabela'))
                
            if comissao_recebida > 100 or comissao_repassada > 100:
                flash('Os valores de comissão não podem ser maiores que 100%', 'error')
                return redirect(url_for('tabela'))
                
            if comissao_repassada > comissao_recebida:
                flash('A comissão repassada não pode ser maior que a recebida', 'error')
                return redirect(url_for('tabela'))
                
            config = session.get('tabela_config', {})
            config[tabela] = {
                'tipo_comissao': 'percentual',
                'comissao_recebida': comissao_recebida,
                'comissao_repassada': comissao_repassada
            }
        
        session['tabela_config'] = config
        session.modified = True
        
        flash(f'Configuração para tabela {tabela} salva com sucesso!', 'success')
        return redirect(url_for('comissoes'))
        
    except Exception as e:
        app.logger.error(f'Erro ao salvar configuração: {str(e)}')
        flash('Erro ao salvar configuração', 'error')
        return redirect(url_for('tabela'))

@app.route('/resultado', methods=['GET', 'POST'])
def resultado():
    """Display contract details."""
    dados = session.get('dados')
    if not dados:
        flash('Nenhum dado carregado. Por favor, faça o upload de um arquivo CSV primeiro.', 'error')
        return redirect(url_for('index'))

    ccb = request.args.get('ccb') if request.method == 'GET' else request.form.get('ccb')
    if not ccb:
        flash('Por favor, forneça um número de CCB válido', 'error')
        return redirect(url_for('busca'))
    
    # Tenta encontrar nos dados brutos primeiro
    contrato_raw = None
    ccb_str = str(ccb).strip()
    
    # Procura nos dados brutos
    for item in dados:
        if str(item.get('CCB', '')).strip() == ccb_str:
            contrato_raw = item
            break
    
    # Se não encontrou nos dados brutos, tenta nas comissões
    if not contrato_raw:
        comissoes = session.get('comissoes', {})
        contrato_raw = comissoes.get(ccb_str)
    
    if contrato_raw:
        # Restructure the data for the template
        contrato = {
            'Informações Básicas': {
                'Nome': contrato_raw.get('Nome', 'N/A'),
                'CPF': contrato_raw.get('CPF/CNPJ', 'N/A'),
                'Tabela': contrato_raw.get('Tabela', 'N/A'),
                'Parcelas': contrato_raw.get('Parcelas', 'N/A'),
                'Valor Parcela': format_currency(contrato_raw.get('Valor Parcela')),
                'Valor Bruto': format_currency(contrato_raw.get('Valor Bruto')),
                'Valor Líquido': format_currency(contrato_raw.get('Valor Líquido')),
                'Link de assinatura': contrato_raw.get('Link de assinatura', ''),
                'Parceiro': contrato_raw.get('Parceiro', 'N/A'),
                'Usuário': contrato_raw.get('Usuário', 'N/A'),
                'Status': contrato_raw.get('Status', 'N/A')
            }
        }
        
        return render_template('resultado.html', contrato=contrato, ccb=ccb)
    
    flash('CCB não encontrada. Verifique se o número está correto.', 'error')
    return redirect(url_for('busca'))

@app.route('/busca')
def busca():
    """Render the search page."""
    dados = session.get('dados')
    if not dados:
        return render_template('error.html')
    return render_template('busca.html')

from datetime import datetime

@app.route('/preview_ccbs')
def preview_ccbs():
    if 'usuario' not in session:
        return redirect(url_for('busca'))
    
    usuario = session['usuario']
    ccbs = session.get('ccbs', [])
    
    return render_template('print_usuario_ccbs.html', usuario=usuario, ccbs=ccbs)

@app.route('/usuario_ccbs')
def usuario_ccbs():
    if 'usuario' not in session:
        return redirect(url_for('busca'))
    
    usuario = session['usuario']
    ccbs = session.get('ccbs', [])
    
    return render_template('usuario_ccbs.html', usuario=usuario, ccbs=ccbs, preview_url=url_for('preview_ccbs'))

def carregar_dados():
    """Load data from session."""
    return session.get('dados', [])

@app.route('/verificar_ccb/<ccb>')
def verificar_ccb(ccb):
    try:
        dados = carregar_dados()
        if not dados:
            return jsonify({'exists': False, 'error': 'Nenhum dado carregado'})
        
        exists = any(str(linha.get('CCB', '')).strip() == str(ccb).strip() for linha in dados)
        return jsonify({'exists': exists})
    except Exception as e:
        app.logger.error(f"Error checking CCB {ccb}: {str(e)}")
        return jsonify({'exists': False, 'error': 'Erro ao verificar CCB'})

@app.route('/limpar_dados', methods=['POST'])
def limpar_dados():
    """Clear all session data."""
    try:
        session.clear()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

def generate_dark_pdf(output_path, usuario, ccbs):
    """Generate PDF directly using ReportLab with maximum darkness settings"""
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )
    
    # Create story for elements
    story = []
    
    # Create custom styles
    styles = getSampleStyleSheet()
    
    # Extra dark title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        alignment=TA_CENTER,
        spaceAfter=30,
        textColor=colors.black,
        borderWidth=2,
        borderColor=colors.black,
        borderPadding=10,
        leading=30
    )
    
    # Extra dark header style
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.black,
        leading=20,
        borderWidth=1,
        borderColor=colors.black,
        borderPadding=5
    )
    
    # Extra dark normal text style
    text_style = ParagraphStyle(
        'CustomText',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.black,
        leading=15
    )
    
    # Add title
    story.append(Paragraph(f"Relatório de CCBs - {usuario}", title_style))
    story.append(Spacer(1, 20))
    
    # Prepare table data
    table_data = [['Número', 'Valor', 'Data de Vencimento', 'Taxa', 'Valor Total']]
    
    # Add CCB data
    for ccb in ccbs:
        row = [
            str(ccb.get('numero', '')),
            f"R$ {ccb.get('valor', 0):,.2f}",
            ccb.get('data_vencimento', ''),
            f"{ccb.get('taxa', 0):.2f}%",
            f"R$ {ccb.get('valor_total', 0):,.2f}"
        ]
        table_data.append(row)
    
    # Create table with thick borders and dark text
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        # Extra thick outer border
        ('BOX', (0, 0), (-1, -1), 2.5, colors.black),
        
        # Extra thick inner borders
        ('INNERGRID', (0, 0), (-1, -1), 1.5, colors.black),
        
        # Dark header background
        ('BACKGROUND', (0, 0), (-1, 0), colors.black),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        
        # Extra dark text for data cells
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        
        # Bold all text
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        
        # Cell padding
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        
        # Alternating row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        
        # Extra alignment
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    story.append(table)
    
    # Add summary section
    story.append(Spacer(1, 30))
    
    # Calculate totals
    total_valor = sum(ccb.get('valor', 0) for ccb in ccbs)
    total_valor_total = sum(ccb.get('valor_total', 0) for ccb in ccbs)
    
    # Add summary with thick borders
    summary_style = ParagraphStyle(
        'Summary',
        parent=text_style,
        fontSize=14,
        borderWidth=2,
        borderColor=colors.black,
        borderPadding=10,
        backColor=colors.white
    )
    
    story.append(Paragraph(
        f"""
        <b>Resumo:</b><br/>
        Número total de CCBs: {len(ccbs)}<br/>
        Valor total inicial: R$ {total_valor:,.2f}<br/>
        Valor total com juros: R$ {total_valor_total:,.2f}
        """,
        summary_style
    ))
    
    # Generate PDF
    doc.build(story)

@app.route('/generate_pdf/<template_name>')
def generate_pdf(template_name):
    try:
        if template_name == 'usuario_ccbs':
            if 'usuario' not in session:
                return redirect(url_for('busca'))
            
            usuario = session['usuario']
            ccbs = session.get('ccbs', [])
            
            # Create temporary file for PDF
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as pdf_file:
                # Generate PDF directly
                generate_dark_pdf(pdf_file.name, usuario, ccbs)
                
                # Read the generated PDF
                with open(pdf_file.name, 'rb') as f:
                    pdf_content = f.read()
                
                # Clean up
                try:
                    os.unlink(pdf_file.name)
                except Exception as e:
                    app.logger.error(f'Error deleting temporary file {pdf_file.name}: {str(e)}')
                
                # Create response
                response = make_response(pdf_content)
                response.headers['Content-Type'] = 'application/pdf'
                response.headers['Content-Disposition'] = f'attachment; filename=CCBs_{usuario}.pdf'
                return response

    except Exception as e:
        app.logger.error(f'Error generating PDF: {str(e)}')
        flash('Erro ao gerar PDF. Por favor, tente novamente.', 'error')
        return redirect(url_for('usuario_ccbs'))

@app.route('/print_view/<template_name>')
def print_view(template_name):
    if template_name == 'usuario_ccbs':
        if 'usuario' not in session:
            return redirect(url_for('busca'))
        usuario = session['usuario']
        ccbs = session.get('ccbs', [])
        return render_template('print_usuario_ccbs.html', usuario=usuario, ccbs=ccbs)
    return redirect(url_for('index'))

@app.route('/print_comissoes')
def print_comissoes():
    """Render the print view for comissoes."""
    try:
        # Get selected user from query parameter
        selected_user = request.args.get('usuario', '')
        
        # Get existing comissoes from session
        comissoes = session.get('comissoes')
        if not comissoes:
            flash('Nenhum dado de comissão encontrado.', 'error')
            return redirect(url_for('comissoes'))
        
        # Convert dict_values to list
        if isinstance(comissoes, dict):
            comissoes_list = list(comissoes.values())
        else:
            comissoes_list = comissoes
            
        # Filter by user if specified
        if selected_user and selected_user.strip():
            filtered_list = []
            for item in comissoes_list:
                user = item.get('Usuário') or item.get('Usuario', '')
                if user and user.lower() == selected_user.lower():
                    filtered_list.append(item)
            comissoes_list = filtered_list
            
        if not comissoes_list:
            flash('Nenhuma comissão encontrada para o usuário selecionado.', 'error')
            return redirect(url_for('comissoes'))
            
        # Log the data being passed to template
        app.logger.info(f"Passing {len(comissoes_list)} comissões to template")
        app.logger.info(f"Sample comissão: {comissoes_list[0] if comissoes_list else 'No data'}")
        
        # Ensure all required fields are present
        for item in comissoes_list:
            if not item.get('Cliente'):
                nome = item.get('Nome', item.get('nome', ''))
                documento = item.get('Documento', item.get('documento', item.get('CPF', '')))
                item['Cliente'] = format_client_name(nome, documento)
        
        return render_template('print_comissoes.html', comissoes=comissoes_list)
            
    except Exception as e:
        app.logger.error(f'Erro detalhado na rota /print_comissoes: {str(e)}', exc_info=True)
        flash(f'Ocorreu um erro ao gerar a visualização de impressão: {str(e)}', 'error')
        return redirect(url_for('comissoes'))

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, debug=True)