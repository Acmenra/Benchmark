# Установка и использование

Подробное руководство: как поставить фреймворк на разных платформах, и как
пользоваться каждой командой/флагом CLI и каждым полем конфигурации.

## Содержание

- [Установка](#установка-1)
  - [Локально](#локально)
  - [Опциональные зависимости](#опциональные-зависимости)
  - [TensorRT (NVIDIA GPU/Jetson)](#tensorrt-только-nvidia-gpujetson)
  - [Docker](#docker)
- [Запуск из произвольной папки](#запуск-из-произвольной-папки)
- [CLI-команды и флаги](#cli-команды-и-флаги)
  - [`run`](#run)
  - [`sysinfo`](#sysinfo)
  - [`export`](#export)
  - [`clear-results`](#clear-results)
  - [`-v` / `--verbose`](#глобальный-флаг--v---verbose)
- [Конфигурация — все поля](#конфигурация--все-поля)
  - [`benchmark.models[]`](#benchmarkmodels)
  - [`benchmark.formats`](#benchmarkformats)
  - [`benchmark.input_size`](#benchmarkinput_size)
  - [`benchmark.*_iterations` / `duration_minutes`](#режимы-длительности-прогона)
  - [`benchmark.test_images` / `task` / `accuracy_dataset` / `measure_accuracy`](#тестовые-данные-и-accuracy)
  - [`benchmark.precision`](#квантование-precision)
  - [`benchmark.save_predictions` / `predictions_dir`](#сохранение-аннотированных-кадров)
  - [`output.*`](#outputdirectory--formats--timestamp)
  - [`system_info.*`](#system_info)
- [Типовые сценарии](#типовые-сценарии)
- [Что реализовано](#что-реализовано)

---

## Установка

### Локально

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate | Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

### Опциональные зависимости

Уже включены в `requirements.txt`, но доступны и по отдельности через
extras в `pyproject.toml` — удобно, если ставите только на конкретную
платформу (например RPi5 без GPU-стека):

```bash
pip install -e ".[onnx,openvino,gpu,cpu-info,huggingface,viz,html]"
```

| Extra | Даёт | Нужен для |
|---|---|---|
| `onnx` | `onnxruntime` | формат `pytorch`→`onnx` |
| `openvino` | `openvino` | формат `openvino` |
| `tensorrt` | `tensorrt`, `cuda-python` | формат `tensorrt` (см. ниже, отдельная установка) |
| `gpu` | `pynvml` | GPU utilization/VRAM/power/temperature (NVIDIA) |
| `cpu-info` | `py-cpuinfo` | более точная модель/кэши CPU в `sysinfo` |
| `huggingface` | `huggingface_hub` | `source: huggingface` в конфиге моделей |
| `viz` | `matplotlib` | графики (`infrastructure/visualization.py`) |
| `html` | `plotly` | интерактивные графики в HTML-отчёте |
| `dev` | `pytest`, `ruff` | тесты и линтер |
| `all` | всё из перечисленного (кроме `tensorrt`/`dev`) | — |

Каждая зависимость импортируется через `try/except` — без неё
соответствующий формат/метрика просто пропускается с WARNING в логе, а не
роняет процесс (graceful degradation, см. README.md).

### TensorRT (только NVIDIA GPU/Jetson)

`tensorrt`/`cuda-python` не входят в `requirements.txt` — ставятся отдельно.
Проверенный рабочий способ (без системного CUDA Toolkit/`nvcc`, без
компилятора C++, только официальные wheel'ы NVIDIA):

```bash
pip install tensorrt cuda-python --extra-index-url https://pypi.nvidia.com
```

Важно: **torch должен быть CUDA-сборкой**, а не `+cpu` — иначе экспорт
`model.export(format="engine")` внутри ultralytics падает на этапе выбора
устройства с ошибкой `torch.cuda.is_available(): False`, даже если сам GPU/
драйвер/tensorrt работают. Проверить и поставить нужную версию:

```bash
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
# Если версия оканчивается на "+cpu" — переустановите под вашу CUDA:
pip install --force-reinstall torch torchvision --index-url https://download.pytorch.org/whl/cu124
```

(`--force-reinstall` обязателен: pip не видит разницу между `X.Y.Z+cpu` и
`X.Y.Z+cu124` по номеру версии и без него не переустановит. `torchvision`
обновляйте той же командой — версии torch/torchvision должны быть парными,
иначе будет `RuntimeError: operator torchvision::nms does not exist`.)

Мы не используем `pycuda` (классический выбор для TensorRT-инференса в
Python) — он требует компиляции C++-расширения при установке (нужен
Visual Studio Build Tools на Windows / gcc на Linux). `cuda-python` — те же
операции с памятью GPU (`cudaMalloc`/`cudaMemcpy`), но официальные NVIDIA
байндинги, распространяемые как готовые wheel'ы без компиляции.

Особенность формата: `model.export(format="engine")` в ultralytics пишет
файл в собственном контейнере (4 байта длины + JSON-метаданные + чистый
TensorRT-план) — `tensorrt_loader.py` это учитывает
(`_strip_ultralytics_metadata`) перед передачей в `trt.Runtime.deserialize_cuda_engine`.

- **Jetson**: TensorRT и совместимый torch уже идут в составе JetPack —
  доустанавливать не нужно.

Без TensorRT фреймворк продолжает работать — формат `tensorrt` пропускается
с WARNING в логах (`TensorRTLoader.is_available() == False`), остальные
форматы гоняются как обычно.

**`precision: fp16`/`int8` + `tensorrt`**: для квантованного TensorRT-экспорта
ultralytics использует `nvidia-modelopt` — если его нет, ultralytics
попытается доустановить его сама на лету при первом экспорте (что при
неудачно совпавшем по времени параллельном использовании `onnxruntime` в
том же процессе может упасть на Windows с ошибкой доступа к залоченной DLL).
Надёжнее поставить его заранее, отдельной командой, до `run`:

```bash
pip install "nvidia-modelopt[onnx]"
```

Важно: эта команда требует `torch>=2.8`, и если у вас установлена
CUDA-сборка ниже этой версии, `pip` может незаметно подменить её на
**CPU-сборку** последней версии PyPI (та же ловушка с `+cpu` vs `+cu124`,
что и в начале этого раздела). После установки `nvidia-modelopt` **всегда**
проверяйте `torch.cuda.is_available()` и при необходимости переустановите
torch/torchvision CUDA-сборкой (команда выше).

### Docker

```bash
docker compose build
docker compose run benchmark sysinfo
docker compose up
```

Для GPU/TensorRT — см. закомментированный блок `deploy.resources` в
`docker-compose.yml` (требует `nvidia-container-runtime`).

---

## Запуск из произвольной папки

Фреймворк не привязан к тому, откуда его запускают — рабочая директория
(`--config`, `output.directory`, `predictions_dir`, `test_images`, пути к
локальным моделям) может быть любой, в том числе полностью снаружи клона
репозитория. Всё, что фреймворк создаёт сам (`results/`, `runs/`,
`.model_cache/`, экспортированные веса, файл лога) — пишется относительно
текущей рабочей директории процесса, а не относительно расположения кода.

Например, чтобы прогнать бенчмарк над своими картинками/видео/моделью,
лежащими в отдельной папке `C:\my_bench`, а не внутри репозитория:

```powershell
# из любой директории — репозиторий с кодом можно вообще не трогать
$env:PYTHONPATH = "C:\path\to\edge_ai_benchmark_repo"
cd C:\my_bench
python -m edge_ai_benchmark run --config C:\my_bench\my_config.yaml
```

В `my_config.yaml` при этом просто указываются абсолютные пути:

```yaml
benchmark:
  models:
    - family: yolov8
      sizes: [n]
      source: local
      local_paths:
        n: "C:/my_bench/my_model/yolov8n.pt"
  test_images: "C:/my_bench/my_images/images"   # своя разметка рядом в labels/
  save_predictions: true
  predictions_dir: "C:/my_bench/output/predictions"
output:
  directory: "C:/my_bench/output"
```

После `run` в `C:\my_bench` окажутся: `output/results_*.json/csv/md/html`,
`output/logs/run_*.log`, `output/predictions/<model>_<format>/*.jpg`,
`runs/<task>/<run_id>/` (диагностика ultralytics) и временный
`.model_cache/` — репозиторий с кодом остаётся полностью нетронутым, в нём
не появляется ни одного файла результатов. Это же работает и при обычной
установке через `pip install -e .` (тогда `PYTHONPATH` не нужен — пакет уже
виден из любой директории через консольный скрипт `edge-ai-benchmark`).

---

## CLI-команды и флаги

Точка входа: `python -m edge_ai_benchmark <команда> [флаги]` (или
консольный скрипт `edge-ai-benchmark`, если пакет установлен через `pip
install -e .` — см. `pyproject.toml: [project.scripts]`).

### `run`

Прогнать бенчмарк по конфигурации.

```bash
python -m edge_ai_benchmark run [--config PATH] [--model NAME] [--format FMT]
```

| Флаг | Обязателен | По умолчанию | Описание |
|---|---|---|---|
| `--config PATH` | нет | `edge_ai_benchmark/configs/default.yaml` | Путь к YAML-конфигу (см. раздел ниже про все поля). |
| `--model NAME` | нет | все модели из конфига | Отфильтровать один конкретный `<family><size>`, например `--model yolov8n`. Убирает из `benchmark.models` все размеры/семейства, не совпавшие точно; если после фильтра ничего не осталось — ошибка и код возврата `1`. |
| `--format FMT` | нет | все форматы из конфига | Отфильтровать один формат: `pytorch`, `onnx`, `tensorrt`, `openvino`. Если формата нет в конфиге — ошибка и код возврата `1`. |

Что происходит при `run` (см. `cli._cmd_run` → `application/benchmark_runner.py`):

1. Генерируется `run_id` (`YYYYMMDDTHHMMSS`, момент запуска) — используется
   как имя лог-файла, как суффикс имени файла результатов (если
   `output.timestamp: true`) и как имя подпапки в `runs/<task>/<run_id>/`
   с диагностикой ultralytics (`val_batch*.jpg`, PR-кривые, confusion
   matrix). Даже если `output.timestamp: false`, в лог всё равно пишется
   `Результаты (run_id=...) записаны: <путь>` — так файл результатов и
   `runs/` всегда можно сопоставить.
2. Логи прогона дублируются в файл `<output.directory>/logs/run_<run_id>.log`
   (в дополнение к stdout) — на устройстве без монитора/после отключения
   можно посмотреть, что происходило.
3. Применяются фильтры `--model`/`--format`, если заданы.
4. Загружаются тестовые кадры (`benchmark.test_images`, см. ниже) один раз
   на весь прогон и переиспользуются для всех комбинаций модель×формат.
5. Для каждой комбинации семейство×размер×формат (декартово произведение
   `benchmark.models` и `benchmark.formats`):
   - Проверяется `ModelLoader.is_available()` — если рантайм (`onnxruntime`/
     `openvino`/`tensorrt`) не установлен, комбинация пропускается с
     WARNING, весь `run` продолжается.
   - Модель грузится (скачивается/экспортируется при необходимости),
     прогревается `warmup_iterations` раз.
   - Измеряется производительность по режиму `main_iterations`/
     `duration_minutes` (см. ниже), с фоновым мониторингом CPU/RAM/disk
     I/O/GPU/VRAM и раз в 10 секунд — прогресс-логом (avg/min/max latency +
     CPU/GPU/RAM/Power/temp за последнее окно).
   - Если `measure_accuracy: true` — считается accuracy (mAP/precision/
     recall) на том же `test_images` (или явном `accuracy_dataset`).
   - Замеряются питание/температура (если включены в `system_info`).
   - Если `save_predictions: true` — для каждого кадра дополнительно
     сохраняется отрисованная картинка (не влияет на FPS/latency, см. ниже).
6. Собранные `BenchmarkResult` пишутся во все форматы из `output.formats`.
7. Все веса/экспорты, которые фреймворк создал сам за этот прогон,
   удаляются с диска (`cleanup_builtin_artifacts`) — при следующем `run`
   они будут скачаны/экспортированы заново. Это: `.pt` для `builtin`;
   ONNX/OpenVINO/TensorRT-экспорты для `builtin` **и** для LOCAL/HUGGINGFACE
   с `.pt`-источником (включая промежуточные файлы TensorRT-пайплайна —
   `.onnx`, `.fp16.onnx`/`.int8.onnx`). Пользовательские файлы — исходный
   `.pt` LOCAL/HUGGINGFACE или уже готовый файл нужного формата — никогда
   не трогаются.

Код возврата: `0` — успех (даже если часть форматов пропущена как
недоступная); `1` — ошибка конфигурации, недоступный `--model`/`--format`.

### `sysinfo`

Только сбор характеристик системы, без запуска моделей.

```bash
python -m edge_ai_benchmark sysinfo [--output PATH]
```

| Флаг | Обязателен | По умолчанию | Описание |
|---|---|---|---|
| `--output PATH` | нет | не задан → печать в stdout | Сохранить JSON в файл вместо печати. Родительские директории создаются автоматически. |

Возвращает JSON с секциями `os`, `python`, `cpu`, `ram`, `disk`, `gpu`,
`accelerators`, `platform` (см. `infrastructure/system_info.py`).

### `export`

Переформатировать уже сохранённый JSON-отчёт в другой формат — без
повторного запуска бенчмарка.

```bash
python -m edge_ai_benchmark export --format {json,csv,markdown,html} --output PATH --input PATH
```

| Флаг | Обязателен | Описание |
|---|---|---|
| `--format` | да | Целевой формат: `json`, `csv`, `markdown`, `html`. |
| `--output PATH` | да | Куда записать результат. |
| `--input PATH` | да | Путь к ранее сохранённому `results*.json` (от `run`). |

Используется, например, чтобы получить HTML-отчёт с графиками из старого
JSON без повторного прогона моделей, или прогнать несколько запусков через
один и тот же `csv`-шаблон.

### `clear-results`

Полная очистка накопленных артефактов бенчмарка.

```bash
python -m edge_ai_benchmark clear-results [--config PATH]
```

| Флаг | Обязателен | По умолчанию | Описание |
|---|---|---|---|
| `--config PATH` | нет | `edge_ai_benchmark/configs/default.yaml` | Только чтобы узнать `output.directory` (какую именно директорию результатов удалять). Если конфиг не найден/невалиден — используется `./results`. |

Удаляет:
- `<output.directory>` целиком (файлы результатов + `logs/`);
- `./runs/` (диагностика ultralytics — `val_batch*.jpg`, PR-кривые, confusion matrix);
- `./.model_cache/` (HF-веса, сгенерированные accuracy/calibration YAML);
- любые `*.pt`/`*.onnx`/`*.engine`/`*_openvino_model` в текущей директории
  (на случай прерванного прогона, когда автоочистка после `run` не успела
  сработать).

Безопасно вызывать в любой момент — если чего-то из перечисленного нет,
просто логируется «уже отсутствует».

### Глобальный флаг `-v` / `--verbose`

Работает с любой командой, ставится перед именем команды:

```bash
python -m edge_ai_benchmark -v run --config edge_ai_benchmark/configs/default.yaml
```

Включает уровень `DEBUG` вместо `INFO` (детали сэмплирования ресурсов,
трейсбеки неудавшихся best-effort операций типа чтения GPU-температуры).

---

## Конфигурация — все поля

Пример полного файла — `edge_ai_benchmark/configs/default.yaml`. Ниже —
описание каждого поля с допустимыми значениями.

### `benchmark.models[]`

Список групп моделей. Каждая группа:

```yaml
models:
  - family: yolov8          # yolov8 | yolov9 | yolov10 | yolov11 | yolov12 | yolov26
    sizes: [n, s, m, l, x]  # непустой список размеров
    source: builtin         # builtin (по умолчанию) | local | huggingface
    # --- только для source: local ---
    local_paths:
      n: "/path/to/my_yolov8n.pt"
    # --- только для source: huggingface ---
    hf_repo_id: "Ultralytics/YOLOv8"
    hf_filenames:
      n: "yolov8n.pt"
```

- `source: builtin` — стандартное имя ultralytics (`yolov8n.pt`), скачивается
  автоматически при первом обращении и удаляется в конце `run`
  (`cleanup_builtin_artifacts`). Для семейств `yolov11`/`yolov12`/`yolov26`
  ultralytics называет файлы без "v" (`yolo11n.pt`) — это учтено внутри
  (`resolver._FAMILY_ASSET_PREFIXES`), в конфиге всё равно пишите `yolov11`.
- `source: local` — `local_paths[size]` обязателен для каждого используемого
  `size`. Путь может указывать:
  - на **готовый файл нужного формата** (`.onnx`/`.engine`/`.xml` для
    openvino-директории) — используется как есть, не трогается;
  - **или на один `.pt`-чекпоинт для всех форматов сразу** — для каждого
    запрошенного формата (`onnx`/`openvino`/`tensorrt`) он автоматически
    экспортируется тем же пайплайном, что и для `builtin` (см.
    `resolver.resolve_export_pt_source`), с кэшированием рядом с исходным
    `.pt` под именем, учитывающим `precision`. Сам исходный `.pt`
    (пользовательский файл) никогда не удаляется и не изменяется; экспорты,
    которые сделал сам фреймворк, подчищаются в конце `run` так же, как и
    для `builtin` (см. ниже про `cleanup_builtin_artifacts`).
  - Несуществующий путь — `FileNotFoundError` при загрузке.
- `source: huggingface` — требует установленный `huggingface_hub` (см.
  extras) и оба поля `hf_repo_id`/`hf_filenames[size]`; без библиотеки —
  понятный `RuntimeError` при попытке загрузки. Скачанный файл кэшируется в
  `./.model_cache/` (сам кэш скачанного не удаляется автоматически — это
  переиспользуемый кэш, а не временный экспорт); если скачанный файл — `.pt`,
  для него действует та же авто-конвертация в остальные форматы, что и для
  `local` выше.

### `benchmark.formats`

Список форматов из `[pytorch, onnx, tensorrt, openvino]`. Для каждой
комбинации модель×формат создаётся `ModelSpec`; недоступные в этом
окружении форматы (нет `onnxruntime`/`openvino`/`tensorrt`+`cuda-python`,
или нет NVIDIA GPU для TensorRT) пропускаются в `run` с WARNING, а не
роняют весь прогон.

Для BUILTIN- и (при `.pt`-источнике) LOCAL/HUGGINGFACE-моделей все форматы,
кроме `pytorch`, экспортируются средствами самого ultralytics
(`model.export(format=...)`) — своей конвертации нет.

### `benchmark.input_size`

```yaml
input_size: 640   # сторона квадратного входа модели, по умолчанию 640
```

Реально управляет разрешением инференса для всех форматов: прокидывается в
`imgsz=` при экспорте ONNX/OpenVINO/TensorRT, в `predict()`/`val()` для
PyTorch и во все accuracy-вызовы (`model.val(..., imgsz=...)`) — а не только
в размер прогревочной "заглушки". Для TensorRT, если задействован уже
готовый `.engine` (LOCAL/HUGGINGFACE без `.pt`-источника), letterbox
подстраивается под реальный размер входа, скомпилированный в самом engine,
а не под значение из конфига — на случай, если готовый файл собран под
другое разрешение.

### Режимы длительности прогона

Три взаимоисключающих режима, приоритет сверху вниз:

| Поле | Тип | Поведение |
|---|---|---|
| `duration_minutes` | `float \| null` | Если задано (не `null`/`0`) — каждая комбинация модель×формат гоняется указанное время в минутах, циклически повторяя доступные кадры. **Приоритет над `main_iterations`.** |
| `main_iterations` | `int \| null` | Если `duration_minutes` не задан: число — фиксированное количество замеров (кадры переиспользуются циклически, если их меньше, чем `main_iterations`). |
| `main_iterations: null` | (по умолчанию) | Каждый кадр из `test_images` используется ровно один раз, без повторов — "прогнать весь датасет один раз". |

`warmup_iterations` (по умолчанию `10`) — число прогревочных вызовов перед
измерением, на синтетическом кадре, не учитывается в метриках.

Каждые 10 секунд (`_PROGRESS_LOG_INTERVAL_S`) в лог пишется промежуточный
итог: средняя/мин/макс latency за окно + средние CPU/GPU/RAM/Power/temp с
начала прогона. Финальный неполный интервал (если весь прогон короче 10с)
тоже логируется перед завершением.

### Тестовые данные и accuracy

```yaml
test_images: null           # null | путь к директории | путь к видеофайлу
task: detect                 # detect | segment
measure_accuracy: true
accuracy_dataset: null       # null | путь/имя YAML-датасета ultralytics
```

- **`test_images: null` (по умолчанию)** — используются 32 реальных фото с
  настоящей YOLO-разметкой, завезённые в репозиторий под текущий `task`:
  `edge_ai_benchmark/data/test_images/detect/{images,labels}/` или
  `.../segment/{images,labels}/`. Работает офлайн (важно для Jetson/RPi в
  поле, без сети). FPS/latency и accuracy считаются **на одних и тех же**
  кадрах — никакого отдельного скачиваемого датасета для точности.
- **Своя директория с фото** — должна называться `images` и иметь рядом
  директорию `labels` с YOLO-txt разметкой (конвенция ultralytics
  `img2label_paths`: `.../images/x.jpg` ↔ `.../labels/x.txt`). Пример:
  `test_images: "/data/my_images"` (где `/data/my_images` — сама папка
  `images`, а `/data/labels` — разметка рядом). Без разметки: FPS/latency
  считаются как обычно, а accuracy для этой комбинации не считается — в лог
  пишется явное сообщение, вместо падения или подмены посторонним
  датасетом.
- **Видеофайл** — `test_images: "./edge_ai_benchmark/data/test_videos/sample_clip.mp4"`
  (расширения `.mp4`/`.avi`/`.mov`/`.mkv`/`.webm`) или директория с
  несколькими видео/фото сразу — все кадры декодируются и объединяются.
  Accuracy для видео не считается (нет стандартной конвенции разметки
  кадров видео), **если явно не задан `accuracy_dataset`**.
- **`task`** — `detect` (обычная детекция) или `segment` (сегментация).
  Влияет на: какой BUILTIN-чекпоинт берётся (`yolov8n.pt` vs
  `yolov8n-seg.pt`), какая дефолтная директория `test_images` используется,
  какие accuracy-метрики заполняются (`mask_precision`/`mask_recall`/
  `mask_map50`/`mask_map50_95` — только при `segment`).
- **`measure_accuracy: false`** — полностью пропускает измерение точности
  (быстрее, если нужен только FPS).
- **`accuracy_dataset`** — явный путь/имя YAML-датасета ultralytics
  (например `"coco128.yaml"` или свой путь). Если задан — используется как
  есть, **не строится** из `test_images`. Также используется как
  калибровочный датасет для `precision: int8` (см. ниже); если не задан —
  калибровка при INT8 автоматически берёт тот же `test_images`.

### Квантование (`precision`)

```yaml
precision: fp32   # fp32 (по умолчанию) | fp16 | int8
```

| Значение | Поведение |
|---|---|
| `fp32` | Без изменений, полная точность. |
| `fp16` | Половинная точность. На GPU (PyTorch) и при экспорте в ONNX/OpenVINO/TensorRT — без калибровки, обычно безопасное ускорение. На CPU-only PyTorch-бэкенде FP16 не поддерживается — WARNING в лог, остаётся fp32. |
| `int8` | Целочисленное квантование, максимальное ускорение, заметнее теряет accuracy. Требует калибровочный датасет: `accuracy_dataset`, если задан, иначе автоматически — тот же `test_images` (если там есть разметка; без неё калибровка идёт без данных калибровки, что может ухудшить или сломать экспорт — задайте `accuracy_dataset` явно в этом случае). Заметно дольше при первом экспорте. PyTorch-бэкенд INT8 не поддерживает напрямую (нужен экспорт в ONNX/OpenVINO/TensorRT) — молча остаётся на FP32 с INFO-логом. |

Файлы экспорта разных precision одной модели кэшируются отдельно
(суффикс `_fp16`/`_int8` в имени файла — см. `resolver.exported_asset_stem`),
чтобы не затирать друг друга при последовательных прогонах с разной
точностью.

### Сохранение аннотированных кадров

```yaml
save_predictions: false   # true -> сохранять каждый обработанный кадр с отрисовкой
predictions_dir: null     # null -> results/predictions/<run_id>/<model>_<format>/
```

- **`save_predictions: true`** — для каждого обработанного кадра (фото или
  кадра видео) во время измерения сохраняется картинка с отрисованными
  боксами/классами/confidence (и масками для `task: segment`) — то же, что
  рисует `ultralytics.engine.results.Results.plot()`. Работает одинаково для
  **любого** формата (PyTorch/ONNX/OpenVINO/TensorRT) и любого источника
  `test_images` (директория фото, видео — каждый кадр видео сохраняется
  отдельным файлом `frame_00001.jpg`, `frame_00002.jpg`, ...).
- Сама отрисовка не требует повторного инференса — рисует поверх детекций,
  уже посчитанных замеряемым `predict()` (NMS/маски входят в него, см. ниже
  про `end_to_end_latency`), поэтому не добавляет времени сверх записи файла
  на диск.
- **`predictions_dir`** — куда сохранять. `null` (по умолчанию) —
  `<output.directory>/predictions/<run_id>/<model>_<format>/` (тот же
  `run_id`, что у файла результатов и `runs/<task>/<run_id>/`). Можно
  задать свой абсолютный путь — тогда подпапка `<model>_<format>/` всё
  равно создаётся внутри него для каждой комбинации.
- Ошибка сохранения одного кадра (например, не удалось создать директорию)
  не роняет прогон — пишется WARNING в лог, остальные кадры продолжают
  сохраняться.

### `output.directory` / `formats` / `timestamp`

```yaml
output:
  directory: "./results/"
  formats: [json, csv, markdown, html]
  timestamp: true
```

- `directory` — куда писать `results*.json/csv/md/html` и `logs/`.
- `formats` — любое подмножество `[json, csv, markdown, html]`.
- `timestamp: true` (по умолчанию) — имя файла результатов получает суффикс
  `_<run_id>` (например `results_20260721T120000.json`), прошлые результаты
  никогда не перезаписываются. `timestamp: false` — фиксированное имя
  `results.json`; при коллизии (повторный запуск) добавляется `_1`, `_2`,
  ... — тоже без перезаписи. Независимо от этого флага, `run_id` всегда
  явно пишется в лог рядом с путём к файлу (`Результаты (run_id=...)
  записаны: ...`), поэтому файл результатов и соответствующая ему
  диагностика в `runs/<task>/<run_id>/` всегда сопоставимы.

### `system_info`

```yaml
system_info:
  collect_cpu: true
  collect_ram: true
  collect_disk: true
  collect_gpu: true
  collect_power: true
  collect_temperature: true
```

`collect_cpu`/`collect_ram`/`collect_disk` — данные всегда дёшево доступны
через `platform`/`psutil`, включены по умолчанию. `collect_gpu` требует
`pynvml` + NVIDIA GPU. `collect_power`/`collect_temperature` best-effort:
Jetson (`/sys/bus/i2c/drivers/ina3221x/`, thermal_zone), Raspberry Pi
(`vcgencmd measure_temp`), десктоп с NVIDIA (`pynvml`) — на неподдерживаемой
комбинации железа/ОС корректно возвращают `unsupported: true`/`null` вместо
падения.

---

## Типовые сценарии

**Быстрая проверка после установки:**
```bash
python -m edge_ai_benchmark sysinfo
python -m edge_ai_benchmark run --config edge_ai_benchmark/configs/default.yaml
```

**Прогнать одну модель в одном формате (быстро, для отладки):**
```bash
python -m edge_ai_benchmark run --model yolov8n --format onnx
```

**Долгий прогон "на время" вместо фиксированного числа кадров** — в
конфиге: `duration_minutes: 5` (закомментировано по умолчанию в
`default.yaml`).

**Собственные картинки без разметки, только FPS:**
```yaml
test_images: "/data/my_photos"
measure_accuracy: false
```

**Собственные картинки с разметкой, чтобы считать и accuracy:**
```yaml
test_images: "/data/my_dataset/images"   # рядом должна быть /data/my_dataset/labels
```

**Видео вместо статичных фото:**
```yaml
test_images: "./edge_ai_benchmark/data/test_videos/sample_clip.mp4"
```

**Сегментация вместо детекции:**
```yaml
task: segment
```

**Ускорить инференс ценой точности:**
```yaml
precision: fp16   # или int8
```

**Сохранить картинки/кадры видео с отрисованными боксами/масками для каждой модели:**
```yaml
save_predictions: true
# predictions_dir: "/data/annotated_output"   # опционально, иначе results/predictions/<run_id>/<model>_<format>/
```

**Один свой `.pt`-чекпоинт на все форматы сразу (без ручной конвертации):**
```yaml
models:
  - family: yolov8
    sizes: [n]
    source: local
    local_paths:
      n: "/data/my_model/yolov8n.pt"
formats: [pytorch, onnx, openvino, tensorrt]
```

**Другое разрешение инференса:**
```yaml
input_size: 512   # или 320, 1280 — кратно 32
```

**Переформатировать уже посчитанные результаты в HTML без повторного прогона:**
```bash
python -m edge_ai_benchmark export --format html --output results/report.html --input results/results_20260721T120000.json
```

**Убрать всё накопленное (веса, кэш, диагностику, результаты) перед чистым прогоном:**
```bash
python -m edge_ai_benchmark clear-results --config edge_ai_benchmark/configs/default.yaml
```

---

## Что реализовано

- 4 формата: PyTorch (.pt), ONNX (.onnx), TensorRT (.engine), OpenVINO
  (.xml+.bin) — все протестированы на реальном железе (Intel CPU + NVIDIA
  RTX 3060: CPU для PyTorch/ONNX/OpenVINO, GPU для TensorRT).
- 3 источника весов: `builtin` (авто-скачивание ultralytics), `local`
  (чекпоинт на диске), `huggingface` (Hugging Face Hub) — для всех трёх
  один `.pt` автоматически конвертируется в любой запрошенный формат
  (ONNX/OpenVINO/TensorRT), не только `builtin`.
- Настраиваемое разрешение инференса (`input_size`), реально прокидываемое
  в экспорт и в замеряемый инференс для всех форматов, а не только в
  прогревочную заглушку.
- Полностью переносимый рабочий каталог — `run` можно запускать из любой
  директории (в том числе снаружи клона репозитория), все создаваемые
  файлы (результаты, кэш весов, диагностика, предсказания) пишутся
  относительно текущей рабочей директории, репозиторий не засоряется.
- 2 задачи: `detect` и `segment`, с автоматическим выбором нужного
  чекпоинта (`yolov8n.pt` vs `yolov8n-seg.pt`) и accuracy-метрик
  (box vs box+mask).
- 3 режима длительности: по числу кадров датасета (по умолчанию), по
  фиксированному числу итераций, по времени (`duration_minutes`).
- Квантование: `fp32`/`fp16`/`int8`, с раздельным кэшем экспортов на диске.
- Собственный bundled-датасет (32 фото + реальная разметка на detect/
  segment) — FPS и accuracy считаются на одних и тех же кадрах; поддержка
  пользовательских директорий (с разметкой и без) и видео, с корректным
  пропуском accuracy там, где разметки нет — вместо падения или подмены
  посторонним датасетом.
- Метрики: FPS, compute-latency (чистый forward pass) и end-to-end-latency
  (p50/p95/p99 у обеих) раздельно — end-to-end включает NMS/декодирование
  масок одинаково для всех 4 форматов, честно отражая реальную задержку
  кадра на устройстве; CPU/RAM/disk I/O/GPU utilization/VRAM;
  питание и температура (Jetson/RPi/десктоп с NVIDIA, отдельно GPU/CPU);
  accuracy (precision/recall/mAP50/mAP50-95, +mask-варианты для segment).
- Периодический прогресс-лог каждые 10 секунд + финальный флеш для
  коротких прогонов.
- Сохранение аннотированных кадров (`save_predictions`) — боксы/классы/
  confidence и маски (segment) для любого формата и источника (фото/видео),
  без искажения измеренных FPS/latency.
- 4 формата отчётов: JSON, CSV, Markdown, HTML (с графиками через
  plotly, если установлен).
- CLI: `run` (с фильтрами `--model`/`--format`), `sysinfo`, `export`,
  `clear-results`, глобальный `-v/--verbose`.
- `run_id`, единый для лог-файла, имени файла результатов (при
  `timestamp: true`) и подпапки диагностики `runs/<task>/<run_id>/` —
  всегда прослеживаемая связка, даже при `timestamp: false`.
- Автоматическая очистка скачанных/экспортированных весов после каждого
  `run` — для `builtin` и для LOCAL/HUGGINGFACE с `.pt`-источником (включая
  промежуточные файлы TensorRT-пайплайна); пользовательские исходники и
  уже готовые файлы нужного формата никогда не трогаются.
- Graceful degradation по всему стеку: отсутствие `onnxruntime`/`openvino`/
  `tensorrt`/`pynvml`/`py-cpuinfo`/`huggingface_hub`/`matplotlib`/`plotly`
  не роняет процесс — соответствующий формат/метрика/фича пропускается с
  логом.
- Автоопределение платформы (desktop/Jetson/Raspberry Pi) для системной
  информации и выбора источника питания/температуры.
