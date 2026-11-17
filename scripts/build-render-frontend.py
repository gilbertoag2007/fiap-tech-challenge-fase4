"""Copy static frontend and write public runtime settings (never secrets)."""
import argparse
import json
import os
from pathlib import Path
import shutil
from urllib.parse import urlparse

parser = argparse.ArgumentParser()
parser.add_argument('--output', default='dist/frontend')
args = parser.parse_args()
url = os.environ.get('API_BASE_URL', '').strip().rstrip('/')
parsed = urlparse(url)
if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
    raise SystemExit('API_BASE_URL must be an HTTPS origin, e.g. https://your-api.onrender.com')
source = Path(__file__).resolve().parents[1] / 'analise-medica-frontend'
output = Path(args.output).resolve()
if output == source or source in output.parents:
    raise SystemExit('Output must be outside the frontend source directory.')
shutil.copytree(source, output, dirs_exist_ok=True)
config = {'apiBaseUrl': url, 'demoMode': os.environ.get('DEMO_MODE', '1').lower() in {'1', 'true', 'yes'}}
(output / 'assets/js/runtime-config.js').write_text('window.APP_CONFIG = ' + json.dumps(config) + ';\n', encoding='utf-8')
print(f'Static frontend ready: {output}')
