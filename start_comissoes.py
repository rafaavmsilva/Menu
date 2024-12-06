from comissoes.app import create_app
from waitress import serve
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    app = create_app()
    logger.info('Starting Comissoes module on http://127.0.0.1:5001')
    serve(app, host='127.0.0.1', port=5001)
