import importlib
import os
from pathlib import Path

import fisioterapia


def test_default_yolo_config_dir_is_existing_data_directory(monkeypatch, tmp_path):
    monkeypatch.delenv('YOLO_CONFIG_DIR', raising=False)
    monkeypatch.setenv('FISIOTERAPIA_DATA_DIR', str(tmp_path))

    importlib.reload(fisioterapia)

    assert Path(os.environ['YOLO_CONFIG_DIR']) == tmp_path
    assert Path(os.environ['YOLO_CONFIG_DIR']).is_dir()
