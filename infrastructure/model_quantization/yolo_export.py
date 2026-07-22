# infrastructure/model_quantization/yolo_export.py

import shutil
from pathlib import Path

from ultralytics import YOLO


class ModelExportError(RuntimeError):
    """Ошибка экспорта модели в runtime-формат."""


def export_yolo_model(
    pt_path: Path,
    export_format: str,
    target_path: Path,
    export_kwargs: dict[str, object] | None = None,
) -> Path:
    """Экспортировать YOLO .pt в target_path, если артефакт еще не существует."""
    pt_path = Path(pt_path)
    target_path = Path(target_path)

    if target_path.exists():
        return target_path
    if not pt_path.exists():
        raise ModelExportError(f"Исходная .pt модель не найдена: {pt_path}")

    kwargs = dict(export_kwargs or {})
    kwargs["format"] = export_format

    exported = YOLO(str(pt_path)).export(**kwargs)
    exported_path = Path(exported)
    if not exported_path.exists():
        raise ModelExportError(f"Экспорт завершился без артефакта: {exported_path}")

    if exported_path == target_path:
        return target_path

    if target_path.exists():
        return target_path

    shutil.move(str(exported_path), str(target_path))
    return target_path

