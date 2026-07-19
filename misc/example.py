# misc/example.py

import os
import cv2
import time
import logging
import numpy as np
# from tqdm import tqdm

from ultralytics import YOLO
from enum import Enum, EnumType
from typing import Any, List, Dict, Optional

# pip install acmenra-cv==0.2.0.1
from acmenra_cv import Tracker, TrackedObject
from acmenra_cv import Font, Fill, Stroke, Style, Drawer, LabelPosition
from acmenra_cv import Point, Obb, Box, Polygon, Instance, DeviceType, TaskType
from acmenra_cv import Backend, YOLOBackend

from core.enums.model import Coco



os.makedirs(os.path.join(os.getcwd(), 'logs'), exist_ok=True)
formatter = '[%(asctime)s] #%(levelname)-8s %(filename)s:%(lineno)d - %(name)s - %(message)s'
logging.basicConfig(level=logging.ERROR, format=formatter)

logger = logging.getLogger(__name__)
file_handler = logging.FileHandler(os.path.join(os.getcwd(), 'logs', 'logs.log'))
file_handler.setFormatter(logging.Formatter(formatter))
logger.root.addHandler(file_handler)


class Worker:
    def __init__(self,
                 style: Style,
                 model_path: str,
                 category: EnumType,
                 task_type: TaskType,
                 device: DeviceType,
                 conf: float = 0.7,
                 iou: float = 0.7,
                 imgsz: int = 640,
                 half: bool = False,
                 max_length: int = 100) -> None:

        self._drawer = Drawer(style=style)
        self._backend = YOLOBackend(
            model=YOLO(model_path, task=task_type.value),
            device=device,
            category=category,
            task_type=task_type,
            threshold=conf,
            iou=iou,
            imgsz=imgsz,
            half=half
        )
        self._tracker = Tracker(id=0,
                                backend=self._backend,
                                max_length=max_length)

    @property
    def device(self) -> DeviceType:
        return self._backend.device

    @device.setter
    def device(self, device: DeviceType) -> None:
        if not isinstance(device, DeviceType):
            raise TypeError(f"'device' must be '<DeviceType>', but got {type(device).__name__}")
        self._backend.device = device

    def work(self,
               frame: np.ndarray,
               is_box: bool = False,
               is_obb: bool = False,
               is_polygon: bool = False,
               is_trajectory: bool = False) -> (np.ndarray, List[TrackedObject]):

        tracked_objects = self._tracker.track(frame=frame, enable_tracking=True)
        frame = self._drawer.draw_instances(frame=frame,
                                            tracked_objects=tracked_objects,
                                            is_box=is_box,
                                            is_obb=is_obb,
                                            is_polygon=is_polygon,
                                            is_trajectory=is_trajectory)

        return frame, tracked_objects


style = Style(palette=np.random.randint(0, 255, (80, 3)).tolist(),
              font=Font(color=(255, 100, 150),
                        font=cv2.FONT_HERSHEY_PLAIN,
                        font_scale=1,
                        thickness=2),
              stroke=Stroke(thickness=1,
                            segment=0.08,
                            alpha=0.80),
              fill=Fill(alpha=0.35),
              smooth=0,
              alpha=0.99,
              show=True,
              rounding=0.05,
              label=LabelPosition.OFF)

worker = Worker(style=style,
                model_path='yolo26n-seg.pt', # *.enine, *.onnx, *.ncnn, etc.
                category=Coco,
                task_type=TaskType.SEGMENT,
                device=DeviceType.MPS,
                conf=0.60,
                iou=0.7,
                imgsz=1280,
                half=False,
                max_length=200)


cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break


    sub_frame, tracked_objects = worker.work(frame=frame, is_polygon=True)
    cv2.imshow(f"Frame", sub_frame)
    if cv2.waitKey(1):
        pass

cap.release()
cv2.destroyAllWindows()