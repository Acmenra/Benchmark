# Edge AI Benchmark Suite

## 🎯 Что это и зачем

Вы работаете над **бенчмарк-фреймворком** для тестирования моделей компьютерного зрения на разных устройствах.

**Зачем это нужно:**
- Acmenra.studio разрабатывает системы Edge AI для промышленности, логистики и транспорта
- Нужно понимать, какая модель на каком железе работает быстрее и точнее
- Результаты бенчмарка используются для:
  - Выбора железа для клиентов ("Вам хватит Raspberry Pi 5" или "Нужен Jetson Orin")
  - Коммерческих предложений с техническим обоснованием
  - Демонстрации возможностей на выставках

**Ваш результат:** Инструмент, который будет использоваться в реальных проектах.

---

## 📋 Что нужно сделать

Разработать **Edge AI Benchmark Suite** — Python-фреймворк для автоматизированного бенчмаркинга моделей детекции объектов.

### Основные функции:

1. **Тестирование моделей**
   - YOLOv8, YOLOv10, YOLOv11, YOLOv12, YOLOv26 (размеры: n, s, m, l, x)
   - Форматы: PyTorch (.pt), ONNX (.onnx), TensorRT (.engine), OpenVINO (.xml)

2. **Поддержка разных платформ**
   - Desktop/Laptop (CPU + NVIDIA GPU)
   - NVIDIA Jetson (Nano, Orin)
   - Raspberry Pi 5
   - Автоматическое определение доступных ресурсов

3. **Сбор метрик**
   - **Производительность:** FPS, latency (p50, p95, p99)
   - **Ресурсы:** GPU/CPU utilization, VRAM/RAM usage
   - **Энергопотребление:** Power consumption (GPU, system)
   - **Температура:** GPU, CPU

4. **Сбор характеристик железа** 
   - OS, Python version, architecture
   - CPU: модель, ядра, частота
   - RAM: total, available
   - GPU: модель, VRAM, CUDA version, driver version
   - Ускорители: TensorRT, OpenVINO, Hailo RT

5. **Экспорт результатов**
   - JSON (машиночитаемый)
   - CSV (для Excel/pandas)
   - Markdown (для документации)
   - Визуализация (графики, heatmaps)

---

## 🛠️ Технические требования

### Стек технологий:
- **Язык:** Python 3.11+
- **ML-фреймворк:** PyTorch 2.0+, Ultralytics
- **Форматы:** ONNX Runtime, TensorRT, OpenVINO
- **Системные метрики:** psutil, pynvml, cpuinfo, platform
- **Конфигурация:** YAML (pyyaml)
- **Тестирование:** pytest
- **Контейнеризация:** Docker + docker-compose

### Требования к коду:
- Code style: PEP 8 (проверка через `ruff` или `flake8`)
- Type hints: обязательны для всех публичных функций
- Docstrings: Google style для всех модулей, классов, функций
- Error handling: корректная обработка исключений
- Logging: информативные логи с уровнями DEBUG/INFO/WARNING/ERROR
- Testing: покрытие ключевых модулей тестами

---

## 📅 Этапы работы

### Этап 1: Инициализация (29.06 — 05.07)
**Что сделать:**
- Настроить окружение (Python, Docker, Git)
- Изучить кодовую базу acmenra-cv
- Спроектировать архитектуру Фреймворка
- Написать ARCHITECTURE.md

**Результат:** Настроенное окружение, архитектурная документация

---

### Этап 2: Ядро Фреймворка (06.07 — 12.07)
**Что сделать:**
- Реализовать модуль `system_info.py` (сбор характеристик железа)
- Реализовать базовые загрузчики моделей (PyTorch, ONNX)
- Реализовать модуль метрик (FPS, latency, GPU/CPU usage)
- Написать CLI-интерфейс

**Результат:** Работающий прототип, тестирующий PyTorch + ONNX на одной платформе

---

### Этап 3: Расширение (13.07 — 19.07)
**Что сделать:**
- Добавить загрузчики TensorRT и OpenVINO
- Добавить поддержку Jetson и Raspberry Pi
- Реализовать модуль power/temperature
- Тестирование на разных платформах

**Результат:** Фреймворк работает на 3+ платформах, поддерживает 4 формата

---

### Этап 4: Отчётность и документация (20.07 — 23.07)
**Что сделать:**
- Реализовать reporters (JSON, CSV, Markdown)
- Добавить визуализацию (графики, heatmaps)
- Написать README.md, INSTALL.md
- Обновить ARCHITECTURE.md

**Результат:** Полная документация, отчёты во всех форматах

---

### Этап 5: Тестирование и сдача (24.07 — 26.07)
**Что сделать:**
- Финальное тестирование
- Исправление ошибок
- Прогон полного бенчмарка
- Подготовка отчёта для УрФУ
- Защита практики

**Результат:** Финальный отчёт, код в репозитории, защита практики

---

## 📁 Структура проекта

```
edge_ai_benchmark/
├── __init__.py
├── cli.py                  # CLI-интерфейс
├── config.py               # Загрузка конфигурации
├── system_info.py          # Сбор характеристик железа
├── models/                 # Загрузчики моделей
│   ├── __init__.py
│   ├── base.py             # Абстрактный базовый класс
│   ├── pytorch_loader.py
│   ├── onnx_loader.py
│   ├── tensorrt_loader.py
│   └── openvino_loader.py
├── metrics/                # Сбор метрик
│   ├── __init__.py
│   ├── performance.py      # FPS, latency
│   ├── hardware.py         # GPU/CPU/RAM usage
│   └── power.py            # Power consumption
├── reporters/              # Формирование отчётов
│   ├── __init__.py
│   ├── json_reporter.py
│   ├── csv_reporter.py
│   └── markdown_reporter.py
├── utils/                  # Утилиты
│   ├── __init__.py
│   ├── preprocessing.py    # Предобработка изображений
│   └── visualization.py    # Графики
├── configs/                # Примеры конфигураций
│   ├── default.yaml
│   ├── jetson_orin.yaml
│   └── rpi5.yaml
├── tests/                  # Тесты
│   ├── test_system_info.py
│   ├── test_models.py
│   └── test_metrics.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
├── README.md
├── INSTALL.md
└── ARCHITECTURE.md
```

---

## ⚙️ Конфигурация

Все параметры задаются через YAML-файлы:

```yaml
# configs/default.yaml
benchmark:
  models:
    - family: yolov8
      sizes: [n, s, m]
    - family: yolov11
      sizes: [n, s]
  
  formats: [pytorch, onnx, tensorrt, openvino]
  
  input_size: 640
  batch_size: 1
  warmup_iterations: 10
  main_iterations: 100
  confidence_threshold: 0.25
  
  test_images: "./data/test_images/"

output:
  directory: "./results/"
  formats: [json, csv, markdown]
  timestamp: true

system_info:
  collect_gpu: true
  collect_power: true
  collect_temperature: true
```

---

## 💻 Использование

### Запуск с дефолтной конфигурацией
```bash
python -m edge_ai_benchmark run
```

### Запуск с кастомной конфигурацией
```bash
python -m edge_ai_benchmark run --config configs/jetson_orin.yaml
```

### Только сбор системной информации
```bash
python -m edge_ai_benchmark sysinfo
```

### Тест конкретной модели
```bash
python -m edge_ai_benchmark run --model yolov8n --format onnx
```

### Экспорт результатов
```bash
python -m edge_ai_benchmark export --format csv --output results/summary.csv
```

---

## 📊 Пример отчёта

### JSON
```json
{
  "timestamp": "2026-06-05T12:00:00",
  "system_info": {
    "os": "Linux-5.15.0-76-generic",
    "python_version": "3.10.12",
    "architecture": "x86_64",
    "cpu": {
      "model": "Intel(R) Core(TM) i7-10700K CPU @ 3.80GHz",
      "cores": 8,
      "threads": 16
    },
    "gpu": {
      "model": "NVIDIA GeForce RTX 3080",
      "vram_total_gb": 10.0,
      "cuda_version": "11.8"
    }
  },
  "benchmarks": [
    {
      "model": "yolov8n",
      "format": "pytorch",
      "fps": 120.5,
      "latency_p50_ms": 8.3,
      "latency_p95_ms": 9.1,
      "latency_p99_ms": 10.2,
      "gpu_utilization_pct": 45.2,
      "vram_usage_peak_mb": 1200
    }
  ]
}
```

### CSV
```csv
model,format,fps,latency_p50_ms,latency_p95_ms,gpu_utilization_pct,vram_usage_peak_mb
yolov8n,pytorch,120.5,8.3,9.1,45.2,1200
yolov8n,onnx,135.2,7.4,8.0,42.1,1100
yolov8s,pytorch,85.3,11.7,12.5,52.3,1800
```

---

## 📝 Отчётность

### Еженедельный отчёт (пятница, 18:00)

Каждую пятницу вы пишете отчёт в Telegram-группу:

```markdown
# Отчёт за неделю [номер]

## ✅ Что сделано
- [задача 1]
- [задача 2]

## 📊 Результаты
- [метрика 1]: [значение]
- [метрика 2]: [значение]

## 🎯 План на следующую неделю
- [задача 1]
- [задача 2]

## ⚠️ Проблемы/вопросы
- [если есть]

## 📎 Ссылки
- [ссылка на коммит]
- [ссылка на результаты]
```

### Финальный отчёт для УрФУ

В конце практики вы готовите отчёт по форме УрФУ:
- Введение
- Описание работы
- Результат практики
- Заключение
- Список использованных источников

---

## 🔐 Конфиденциальность

Вы подписали NDA. Напоминаем:
- **Не выкладывать код** в личные репозитории
- **Не публиковать** в соцсетях, на Habr, VC.ru
- **Не передавать** третьим лицам
- Весь код — только в этом репозитории

---

## 📚 Ресурсы

### Документация
- [Ultralytics YOLOv8](https://docs.ultralytics.com/)
- [ONNX Runtime](https://onnxruntime.ai/)
- [TensorRT](https://developer.nvidia.com/tensorrt)
- [OpenVINO](https://docs.openvino.ai/)

### Библиотеки
- [psutil](https://psutil.readthedocs.io/) — системные метрики
- [pynvml](https://pypi.org/project/pynvml/) — NVIDIA GPU метрики
- [cpuinfo](https://pypi.org/project/py-cpuinfo/) — информация о CPU

### Примеры
- [YOLOv8 Benchmark](https://docs.ultralytics.com/modes/benchmark/)
- [TensorRT Quick Start](https://developer.nvidia.com/blog/tensorrt-8-x-feature-highlights/)

---

## 👥 Команда

### Роли

**ML Engineer** (Студент 1 — Team Lead)
- Конвертация моделей, оптимизация, квантование
- Загрузчики моделей (PyTorch, ONNX, TensorRT, OpenVINO)

**Backend Engineer** (Студент 2)
- Модуль инференса, предобработка, постобработка
- CLI-интерфейс, конфигурация

**MLOps Engineer** (Студент 3)
- Бенчмарк, Docker, документация, CI/CD
- Сбор метрик, reporters

---

## ✅ Критерии приёмки

Ваша работа будет принята, если:

### Функциональные критерии
- [ ] Фреймворк запускается на x86_64 + NVIDIA GPU
- [ ] Фреймворк запускается на Jetson Orin (или эмуляция)
- [ ] Фреймворк запускается на Raspberry Pi 5
- [ ] Протестировано не менее 5 моделей
- [ ] Протестировано не менее 3 форматов
- [ ] Собраны все метрики (FPS, latency, VRAM, power, temperature)
- [ ] Собраны все характеристики системы
- [ ] Результаты экспортированы в JSON, CSV, Markdown

### Технические критерии
- [ ] Код соответствует PEP 8
- [ ] Все функции имеют type hints и docstrings
- [ ] Тесты проходят успешно
- [ ] Docker-контейнер собирается и запускается
- [ ] README.md содержит все разделы
- [ ] Код загружен в репозиторий

### Критерии качества
- [ ] Фреймворк работает стабильно (без крашей)
- [ ] Метрики воспроизводимы (разброс FPS < 1%)
- [ ] Код читаем и понятен
- [ ] Документация полна и корректна

---

## 💡 Советы

1. **Начинайте с простого.** Сначала запустите базовый бенчмарк на одной модели, потом добавляйте функционал.
2. **Тестируйте на каждом этапе.** Не накапливайте баги. Запускайте тесты после каждого коммита.
3. **Документируйте сразу.** Не откладывайте написание README и docstrings на конец.
4. **Задавайте вопросы.** Лучше спросить сразу, чем делать неправильно.
5. **Работайте в команде.** Помогайте друг другу, ревьюите код, обсуждайте решения.

---

## 🎓 Что вы получите

- **Реальный кейс в портфолио** — не учебный проект, а инструмент для бизнеса
- **Опыт Edge AI** — работа с Jetson, Raspberry Pi, оптимизация моделей
- **Навыки MLOps** — Docker, бенчмаркинг, метрики, документация
- **Рекомендацию** — при успешной сдаче практики
- **Возможный оффер** — если покажете хорошие результаты

---


