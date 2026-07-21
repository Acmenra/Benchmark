# Архитектура Edge AI Benchmark Suite

## Слои

Проект разбит на 3 слоя (dependency inversion: `core` ничего не знает о
`infrastructure`/`application`; `application` не знает о конкретных деталях
I/O, только вызывает интерфейсы `core` через реализации `infrastructure`).

```
edge_ai_benchmark/
├── cli.py                       # тонкий argparse-слой
├── core/
│   ├── enums.py                  # ModelFormat, ModelSource, Precision, PlatformType, ReportFormat
│   ├── entities.py                # ModelSpec, *Result, *Config, AppConfig
│   ├── interfaces.py               # ModelLoader(ABC), Reporter(ABC)
│   └── services/performance.py      # compute_fps, compute_percentiles, build_performance_result
├── infrastructure/
│   ├── config_loader.py           # YAML -> core.entities.AppConfig, валидация
│   ├── system_info.py              # OS/CPU/RAM/GPU/платформа (psutil/pynvml/platform/py-cpuinfo)
│   ├── hardware_monitor.py          # ResourceMonitor — фоновый сэмплер CPU/RAM/disk/GPU
│   ├── power.py                     # питание/температура (Jetson/RPi/десктоп с NVIDIA)
│   ├── dataset.py                    # bundled test_images + сборка YAML-датасета для accuracy/калибровки
│   ├── video.py                      # декодирование кадров из видео
│   ├── preprocessing.py               # letterbox-ресайз для не-ultralytics бэкендов
│   ├── postprocessing.py               # NMS/боксы/маски для не-ultralytics бэкендов
│   ├── visualization.py                # графики (matplotlib), опционально
│   ├── models/
│   │   ├── resolver.py                 # ModelSpec -> путь к весам, кэш-именование, очистка
│   │   ├── pytorch_loader.py
│   │   ├── onnx_loader.py
│   │   ├── openvino_loader.py
│   │   └── tensorrt_loader.py
│   └── reporters/
│       ├── json_reporter.py, csv_reporter.py, markdown_reporter.py, html_reporter.py
│       └── _serialize.py             # общая сериализация BenchmarkResult -> dict
└── application/
    └── benchmark_runner.py         # оркестратор: конфиг -> загрузчики -> метрики -> BenchmarkResult
```

## Graceful degradation

Опциональные зависимости (`onnxruntime`, `openvino`, `pynvml`, `py-cpuinfo`,
`huggingface_hub`, `tensorrt`+`cuda-python`, `matplotlib`, `plotly`)
импортируются в `try/except` на уровне модуля. `ModelLoader.is_available()`
позволяет `benchmark_runner` пропустить формат с WARNING-логом вместо
падения всего прогона. Метрики питания/температуры/GPU возвращают
`None`/`unsupported=True`, если источник недоступен на текущей платформе —
это единообразный паттерн по всему `infrastructure/`.

## Источники моделей (`ModelSource`)

- `BUILTIN` — стандартное имя (`yolov8n`), ultralytics скачивает сам при
  первом обращении.
- `LOCAL` — путь к файлу на диске (`models[].local_paths`).
- `HUGGINGFACE` — скачивание через `huggingface_hub` (`models[].hf_repo_id`/
  `hf_filenames`), кэшируется в `./.model_cache/`.

Для всех трёх источников на форматы, отличные от `pytorch`, действует
единый принцип: **либо файл уже в целевом формате — используется как есть,
либо это `.pt` — тогда он экспортируется** тем же пайплайном ultralytics,
что и для `BUILTIN`. Так `LOCAL`/`HUGGINGFACE` не требуют по отдельному
файлу на каждый формат — одного `.pt` достаточно для бенчмарка сразу по
всем `formats`. Всё, что фреймворк экспортировал сам (в том числе
промежуточные файлы при сборке TensorRT — см. ниже), удаляется в конце
`run` (`cleanup_builtin_artifacts` в `cli._cmd_run`); пользовательские
исходники (сам `.pt` или уже готовый файл нужного формата) не трогаются
никогда.

Разрешение пути и всё именование кэша реализовано в
`infrastructure/models/resolver.py`:
- `builtin_asset_stem(spec)` — имя ассета ultralytics, учитывает
  несовпадение "человекочитаемого" имени семейства (`yolov11` в конфигах) и
  реального имени файла у ultralytics (`yolo11n.pt`, без "v" начиная с
  YOLO11), а также суффикс `-seg` при `task == "segment"`.
- `exported_asset_stem(spec)` — то же самое + суффикс precision
  (`_fp16`/`_int8`) для `BUILTIN`.
- `already_in_target_format(spec)` — для LOCAL/HUGGINGFACE проверяет,
  подходит ли уже данный файл под `spec.fmt` напрямую (для `openvino` —
  расширение `.xml` или директория с `.xml` внутри); возвращает путь к нему
  либо `None`, если нужен экспорт.
- `resolve_export_pt_source(spec)` — путь к `.pt`, из которого экспортируем:
  для `BUILTIN` — стандартное имя, для `LOCAL`/`HUGGINGFACE` — тот же файл,
  если это `.pt` (иначе `RuntimeError`, т.к. экспортировать не из чего).
- `export_target_stem(spec)` — имя (без расширения) для результата экспорта
  с суффиксом precision; для `LOCAL`/`HUGGINGFACE` — по имени исходного
  `.pt`, чтобы кэш экспортов разных пользовательских чекпоинтов не
  пересекался (формат в имя не добавляется — его кодирует расширение/суффикс,
  который приписывает каждый загрузчик: `.onnx`/`.engine`/`_openvino_model`).
- `export_kwargs_for_precision(spec, fmt)` — собирает kwargs для
  `model.export()`/`model.val()` под `spec.precision` (единый параметр
  ultralytics `quantize=16|8|None` вместо устаревших `half`/`int8`) и
  `spec.input_size` (`imgsz=`).
- `cleanup_builtin_artifacts(specs)` — удаляет с диска все веса/экспорты,
  сделанные фреймворком: `.pt` для `BUILTIN`, ONNX/OpenVINO/TensorRT-экспорты
  для `BUILTIN` и для LOCAL/HUGGINGFACE с `.pt`-источником. Для TensorRT
  дополнительно чистит промежуточные файлы, которые ultralytics создаёт по
  пути `.pt → .onnx → .engine` (`.onnx`, и при `quantize` — ещё
  `.fp16.onnx`/`.int8.onnx`, см. `ultralytics/utils/export/engine.py`).

## Настраиваемое разрешение (`input_size`)

`ModelSpec.input_size` (из `BenchmarkConfig.input_size`) реально управляет
разрешением инференса, а не только размером прогревочной заглушки:
- при экспорте ONNX/OpenVINO/TensorRT передаётся как `imgsz=` в
  `export_kwargs_for_precision`, поэтому экспортированный файл компилируется
  под нужный размер;
- ONNX/OpenVINO-загрузчики letterbox'ят кадр под реальную форму входа,
  прочитанную из уже загруженной сессии/модели (`session.get_inputs()[0].shape`/
  `input_layer.shape`) — она автоматически совпадает с `input_size`, раз
  экспорт был сделан с тем же значением;
- TensorRT-загрузчик letterbox'ит под форму входа, прочитанную напрямую из
  скомпилированного `.engine` при аллокации I/O-тензоров (`_allocate_io_tensors`)
  — устойчиво и для готового LOCAL/HUGGINGFACE `.engine`, собранного под
  другое разрешение, чем в текущем конфиге;
- PyTorch-загрузчик и все вызовы `evaluate_accuracy()`/`model.val()`
  передают `imgsz=spec.input_size` явно.

## Переносимость рабочей директории

Все пути, которые фреймворк создаёт сам, — `results/`, `logs/`, `runs/`,
`.model_cache/`, экспортированные веса, `predictions/` — либо относительные
(резолвятся от текущей рабочей директории процесса), либо берутся из
конфига как есть. Ничего не завязано на расположение самого пакета
`edge_ai_benchmark` на диске. Поэтому `run` можно запускать из любой
директории (в том числе полностью снаружи клона репозитория — например,
`PYTHONPATH=<путь до репозитория> python -m edge_ai_benchmark run --config
/куда-угодно/config.yaml`, с абсолютными путями в конфиге на свои
модели/картинки/видео) — все создаваемые файлы лягут туда, откуда запущен
процесс, репозиторий с кодом останется нетронутым.

## Задачи (`task: detect | segment`)

`ModelSpec.task` определяет: какой BUILTIN-чекпоинт берётся (`yolov8n.pt`
против `yolov8n-seg.pt`), какая директория тестовых данных используется по
умолчанию, и какие поля `AccuracyResult` заполняются (`mask_precision`/
`mask_recall`/`mask_map50`/`mask_map50_95` — только при `segment`).
Прокидывается из `BenchmarkConfig.task` через `AppConfig.model_combinations()`.

## Latency: compute vs end-to-end

`PerformanceResult` разделяет:
- `compute_latency` — чистое время forward pass. Для PyTorch берётся из
  `ultralytics` `result.speed["inference"]`; для ONNX/OpenVINO/TensorRT
  каждый загрузчик сам замеряет время вокруг вызова инференса
  (`time.perf_counter()` строго вокруг `session.run()`/`compiled_model()`/
  `execute_async_v3()`, без препроцессинга/NMS/H2D-D2H) и переопределяет
  `ModelLoader.last_compute_ms()`.
- `end_to_end_latency` — полное время одного вызова `predict()`, включая
  препроцессинг, NMS/декодирование масок и передачу данных — то есть
  реальную задержку "кадр вошёл → готовы финальные детекции", как в
  продакшне на камере устройства. Одинаково честно для всех 4 форматов (см.
  `infrastructure/postprocessing.py` — раньше NMS для ONNX/OpenVINO/TensorRT
  не входил в замер, и `end_to_end_latency` этих трёх форматов был не
  сопоставим с PyTorch, который через ultralytics всегда включал NMS).
  FPS в отчётах считается по end-to-end.

Источник для `compute_latency` выбирается в
`benchmark_runner._extract_compute_ms()` по приоритету: ultralytics `speed`
→ `loader.last_compute_ms()` → тот же `end_to_end`, если ничего не доступно
(честная деградация вместо придуманного числа).

Все 4 формата реально протестированы на живом железе (Intel CPU + RTX 3060):
PyTorch/ONNX/OpenVINO на CPU, TensorRT на GPU (заметно быстрее за счёт
GPU-инференса и отдельного форматного пайплайна). См.
`infrastructure/models/tensorrt_loader.py._strip_ultralytics_metadata` про
формат `.engine`-файлов ultralytics (4 байта длины + JSON-метаданные +
чистый TensorRT plan) и `INSTALL.md` про требование CUDA-сборки torch для
экспорта TensorRT engine.

## Тестовые данные и accuracy — единый источник

Ключевое архитектурное решение: FPS/latency и accuracy считаются **на одной
и той же** директории с изображениями — никакого отдельного "скачиваемого
на лету" датасета для точности, не связанного с тем, на чём меряется
производительность.

- `infrastructure/dataset.py`:
  - `default_test_images_dir(task)` — путь к завезённой в репозиторий
    директории (`data/test_images/detect/images` или `.../segment/images`),
    используется, когда `benchmark.test_images` не задан.
  - `resolve_accuracy_dataset(images_dir, task)` — по конвенции ultralytics
    (`img2label_paths`: директория `images` должна иметь рядом директорию
    `labels` с YOLO-txt разметкой) собирает YAML-датасет
    (`train`/`val` указывают на тот же `images_dir` — `train` формально
    требуется ultralytics-схемой, но фактически никогда не используется, мы
    только вызываем `model.val()`; `names` — фиксированный словарь 80
    классов COCO). Если разметки нет — возвращает `None`.
- `application/benchmark_runner._resolve_measurement_dataset()` — общий
  хелпер поверх `resolve_accuracy_dataset`, с логированием причины отказа
  (нет разметки / источник — видео). Используется в двух местах:
  - для accuracy (`run_single_benchmark`, после замера производительности);
  - для калибровочного датасета при `precision: int8`, если
    `accuracy_dataset` не задан явно (перед `loader.load()` — `ModelSpec`
    пересобирается через `dataclasses.replace()` с резолвленным
    `calibration_dataset`, сам `ModelSpec` остаётся frozen-датаклассом).
- Пользовательская директория без разметки — accuracy для неё просто не
  считается (лог с объяснением), FPS/latency считаются в любом случае.
  Видео — accuracy не считается вообще (нет стандартной конвенции разметки
  кадров видео), если явно не задан `accuracy_dataset`.
- Явный `benchmark.accuracy_dataset` (путь/имя YAML) имеет приоритет и
  используется как есть, без резолва из `test_images` — годится, например,
  для валидации на классическом `coco128.yaml`, если так нужно осознанно.

`edge_ai_benchmark/data/test_images/{detect,segment}/{images,labels}/` — по
32 реальных фото с настоящей YOLO-разметкой на каждую задачу (не синтетика),
достаточно завезённых в репозиторий, чтобы фреймворк работал офлайн на
Jetson/RPi без доступа в интернет. Если директория `test_images` пуста/не
найдена — один синтетический кадр с явным предупреждением в лог (FPS в этом
случае не отражает реальную нагрузку).

`edge_ai_benchmark/data/test_videos/sample_clip.mp4` — пример видео для
`test_images`, декодируется через `infrastructure/video.py`
(`load_video_frames`/`load_video_frames_from_directory`,
`VIDEO_EXTENSIONS = (.mp4, .avi, .mov, .mkv, .webm)`).

## Режимы длительности прогона

`_frame_indices()` в `benchmark_runner.py` — единая точка, определяющая,
сколько раз и по каким индексам вызывать `predict()`:
1. `duration_minutes` задан → по времени (`time.perf_counter()` дедлайн),
   индексы кадров идут по кругу.
2. Иначе `main_iterations` задан числом → фиксированное число замеров,
   тоже по кругу.
3. Иначе (`main_iterations: null`, по умолчанию) → `range(image_count)`,
   каждый кадр ровно один раз.

`_log_progress()` вызывается каждые 10 секунд (`_PROGRESS_LOG_INTERVAL_S`)
из главного цикла и один раз финально, если прогон короче интервала —
печатает avg/min/max latency за прошедшее окно и снимок
`ResourceMonitor.snapshot()` (CPU/GPU/RAM/Power/temp), не останавливая сам
мониторинг.

## Мониторинг ресурсов (`ResourceMonitor`)

Фоновый поток (`infrastructure/hardware_monitor.py`), сэмплирующий раз в
`sample_interval_s` (по умолчанию 0.2с): CPU% процесса, RAM (RSS), disk I/O
(через `psutil.Process().io_counters()`), и — если доступен `pynvml` —
GPU utilization/VRAM/питание/температуру.

`nvmlInit()`/`nvmlDeviceGetHandleByIndex()` вызываются один раз в `start()`
(не на каждый сэмпл) и `nvmlShutdown()` — один раз в `stop()`; хендл GPU
переиспользуется в цикле сэмплирования — важно для долгих прогонов по
времени (`duration_minutes`), где иначе накапливались бы тысячи циклов
init/shutdown.

## Квантование (`Precision`)

`fp32` (по умолчанию, без изменений) / `fp16` (половинная точность,
безопасное ускорение на GPU/OpenVINO, PyTorch-CPU не поддерживает — остаётся
fp32 с WARNING) / `int8` (целочисленное квантование, требует калибровочный
датасет — `accuracy_dataset` явно или, если не задан, тот же `test_images`,
см. выше; заметно дольше первый экспорт, заметнее теряет accuracy;
PyTorch-бэкенд не поддерживает напрямую — молча остаётся fp32).

Единый параметр ultralytics `quantize=16|8|None` (вместо устаревших раздельных
`half`/`int8`) — см. `resolver.export_kwargs_for_precision`.

## Accuracy

`ModelLoader.evaluate_accuracy(dataset, task, run_id)` переиспользует
`ultralytics.YOLO.val()` — не реализуем свой расчёт mAP. Общее для всех
4 загрузчиков:
- `batch=1` — валидация идёт по одному кадру, как и в streaming-сценарии,
  который бенчмаркается (а не батчами разного размера в зависимости от
  бэкенда, что раньше давало несопоставимые между форматами диагностические
  картинки и метрики).
- `rect=False` — при `batch=1` сортировка по aspect ratio (`rect=True`,
  дефолт ultralytics) не даёт выигрыша в паддинге, зато делает порядок
  картинок разным между бэкендами; без неё порядок одинаков и естественен
  (совпадают побайтово `val_batch*.jpg` между форматами при одинаковом
  датасете).
- `project=run_id` — ultralytics сам подставляет его в
  `runs/<task>/<project>/<name>` (см. `ultralytics.cfg.get_save_dir`),
  поэтому диагностика конкретного `run` лежит в `runs/<task>/<run_id>/
  <model>_<format>/` — сопоставимо с `run_id` в имени файла результатов и
  лог-файла (см. `cli._cmd_run`).

Ограничение самой ultralytics (не наш баг): легенда по классам на
`Box*_curve.png` рисуется, только если классов < 21
(`ultralytics/utils/metrics.py: 0 < len(names) < 21`) — на 32 реальных фото
из COCO обычно встречается больше 20 уникальных классов, поэтому на этих
графиках остаётся только общая кривая "all classes" без подписей отдельных
классов.

## Сохранение аннотированных кадров (`save_predictions`)

`ModelLoader.annotate(image) -> np.ndarray` рисует поверх детекций,
посчитанных предыдущим `predict()` (`self._last_result`/`self._last_detections`
в загрузчиках) — второй инференс не нужен, раз `predict()` теперь и так
делает полный NMS/decode. Отрисовка — через
`ultralytics.engine.results.Results.plot()` (для ONNX/OpenVINO/TensorRT
`Results` собирается вручную из `postprocessing.Detections`,
`infrastructure/postprocessing.render_detections`) — свою отрисовку не пишем.

В `run_single_benchmark()`, если `save_predictions` включён, `annotate()`
вызывается **после** таймингового блока измерения (не искажает FPS/latency)
и пишет кадр в `predictions_root/<model>_<format>/frame_NNNNN.jpg` (по
умолчанию `predictions_root = <output.directory>/predictions/<run_id>/`, см.
`cli._cmd_run`). Работает одинаково для фото и видео — видео к этому моменту
уже превращено в список кадров (см. `infrastructure/video.py`).

## Reporters

`json_reporter`/`csv_reporter`/`markdown_reporter`/`html_reporter` — общий
вход `list[BenchmarkResult] + system_info: dict`, общая сериализация через
`reporters/_serialize.py`. HTML-отчёт дополнительно рисует графики через
`plotly`, если он установлен (extra `html`) — иначе просто без графиков, без
падения.

## Roadmap (не реализовано)

- Batch-size sweep, cold-start latency отдельно от steady-state.
- Отдельная точечная телеметрия compute-latency для ONNX/OpenVINO/TensorRT
  вместо замера вокруг всего вызова инференса (сейчас это уже сделано —
  каждый загрузчик мерит только сам вызов инференса, без пре/постобработки;
  дальнейшее уточнение — разделить H2D/D2H отдельно от самого forward pass
  для TensorRT).
- Leaderboard/агрегация результатов с нескольких устройств.
- Автогенерация PDF-отчёта, регрессионные алерты в CI по FPS.
- Плагинная система для новых форматов/платформ (entry_points).
- Remote benchmarking (агент на устройстве + оркестратор на хосте).
