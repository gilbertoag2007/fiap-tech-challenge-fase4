"""Análise acadêmica de fisioterapia no REHAB24-6."""
import os
from .config import root_path

# Ultralytics adds its own subdirectory; use the existing data root as its parent.
os.environ.setdefault('YOLO_CONFIG_DIR',str(root_path()))
