"""Análise acadêmica de fisioterapia no REHAB24-6."""
import os
from .config import root_path

# Keep optional estimator settings with the generated local artifacts.
os.environ.setdefault('YOLO_CONFIG_DIR',str(root_path()/'ultralytics-settings'))
