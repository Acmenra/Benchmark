# infrastructure/model_quantization/yolo_export.py

import shutil
import logging
from pathlib import Path
from ultralytics import YOLO

from infrastructure.exceptions import ModelExportError

logger = logging.getLogger(__name__)


def ensure_yolo_pt_model(pt_path: Path) -> Path:
    """
    Guarantees the presence of the source YOLO `.pt` model in the specified cache.

    If the model does not exist locally, it attempts to download it via Ultralytics
    and moves it to the target cache directory.

    Args:
        pt_path: The target path where the `.pt` model should reside.

    Returns:
        Path: The resolved path to the cached `.pt` model.

    Raises:
        ModelExportError: If the download fails or the file is not found post-download.
    """
    if pt_path.exists():
        return pt_path

    model_name = pt_path.name
    logger.info(f"Модель не найдена в кэше, скачиваю {model_name}...")

    try:
        YOLO(model_name)
        downloaded_path = Path(model_name).resolve()

        if downloaded_path.exists():
            pt_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(downloaded_path), str(pt_path))
            logger.info(f"Модель успешно перемещена в кэш: {pt_path}")

    except Exception as error:
        raise ModelExportError(f"Не удалось скачать .pt модель {model_name}: {error}") from error

    if not pt_path.exists():
        raise ModelExportError(f"После загрузки .pt модель не найдена по пути: {pt_path}")

    return pt_path

def export_yolo_model(pt_path: Path,
                      export_format: str,
                      target_path: Path,
                      export_kwargs: dict[str, object] | None = None) -> Path:
    """
    Exports a YOLO `.pt` model to the specified target path if the artifact doesn't exist.

    Args:
        pt_path: Path to the source PyTorch model.
        export_format: The target format string (e.g., 'onnx', 'openvino').
        target_path: The desired destination path for the exported artifact.
        export_kwargs: Additional keyword arguments for `YOLO.export()`.

    Returns:
        Path: The resolved path to the exported artifact.

    Raises:
        ModelExportError: If the export completes but no artifact is generated.
    """
    pt_path = Path(pt_path)
    target_path = Path(target_path)

    if target_path.exists():
        return target_path

    pt_path = ensure_yolo_pt_model(pt_path)

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
