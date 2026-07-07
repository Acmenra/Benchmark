# Пример для реализации некоторых файлов в этой папке.
# в конце Удалить


import os
import platform
import sys
import subprocess
import shutil
import psutil


def get_cpu_frequency():
    try:
        freq = psutil.cpu_freq()
        if freq:
            return f"{freq.max:.2f} MHz" if freq.max else f"{freq.current:.2f} MHz"
    except Exception:
        pass
    return "Unknown"


def get_cpu_model():
    system = platform.system()
    if system == "Windows":
        return platform.processor()
    elif system == "Linux":
        # Чтение /proc/cpuinfo для Linux (включая Raspberry Pi и Jetson)
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line or "Hardware" in line:
                        return line.split(":")[1].strip()
        except Exception:
            pass
        # Альтернативный вариант через lscpu, если файл не дал результатов
        try:
            res = subprocess.check_output("lscpu", shell=True).decode().strip()
            for line in res.split("\n"):
                if "Model name:" in line:
                    return line.split(":")[1].strip()
        except Exception:
            pass
    return platform.machine()


def get_cuda_version():
    # Попытка определить версию CUDA через nvcc (универсально для десктопов и Jetson)
    if shutil.which("nvcc"):
        try:
            res = subprocess.check_output("nvcc --version", shell=True).decode()
            for line in res.split("\n"):
                if "release" in line:
                    return line.split("release")[-1].strip()
        except Exception:
            pass

    # Альтернативная проверка пути по умолчанию на Linux/Jetson
    cuda_version_path = "/usr/local/cuda/version.json"
    if os.path.exists(cuda_version_path):
        try:
            import json
            with open(cuda_version_path, "r") as f:
                data = json.load(f)
                return data.get("cuda", {}).get("version", "Unknown")
        except Exception:
            pass

    return "Not Available / Not Found"


def get_gpu_info():
    system = platform.system()
    gpu_list = []

    # 1. Попытка через GPUtil (для NVIDIA на Windows/Linux)
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        for gpu in gpus:
            gpu_list.append({
                "model": gpu.name,
                "vram_total": f"{gpu.memoryTotal} MB",
                "driver": gpu.driver
            })
    except Exception:
        pass

    # 2. Если GPUtil не нашел карт (или это AMD/Intel, или специфичный ARM Linux)
    if not gpu_list:
        if system == "Windows":
            try:
                ps_cmd = (
                    'powershell -NoProfile -ExecutionPolicy Bypass -Command "'
                    'Get-CimInstance Win32_VideoController | '
                    'Select-Object Name, AdapterRAM, DriverVersion | '
                    'ConvertTo-Json"'
                )
                res = subprocess.check_output(ps_cmd, shell=True).decode(errors='ignore').strip()
                if res:
                    import json
                    data = json.loads(res)
                    devices = data if isinstance(data, list) else [data]
                    for dev in devices:
                        model = dev.get("Name", "Unknown Graphics")
                        raw_ram = dev.get("AdapterRAM")
                        driver = dev.get("DriverVersion", "Unknown")
                        if raw_ram:
                            vram_bytes = abs(int(raw_ram))
                            vram = f"{vram_bytes / (1024 ** 2):.0f} MB" if vram_bytes > 0 else "Dynamic (Shared)"
                        else:
                            vram = "Dynamic (Shared)"
                        gpu_list.append({"model": model, "vram_total": vram, "driver": driver})
            except Exception:
                gpu_list.append(
                    {"model": "AMD/Intel Integrated Graphics", "vram_total": "Dynamic", "driver": "Unknown"})

        elif system == "Linux":
            # Проверка 2.1: NVIDIA Jetson
            if os.path.exists("/etc/nv_tegra_release"):
                try:
                    with open("/etc/nv_tegra_release", "r") as f:
                        info = f.readline().strip()
                    gpu_list.append({
                        "model": f"NVIDIA Jetson Tegra ({info.split(',')[0]})",
                        "vram_total": "Shared with RAM",
                        "driver": "NVIDIA Tegra Driver"
                    })
                except Exception:
                    gpu_list.append({"model": "NVIDIA Jetson GPU", "vram_total": "Shared with RAM", "driver": "L4T"})

            # Проверка 2.2: Raspberry Pi
            elif os.path.exists("/boot/config.txt") or shutil.which("vcgencmd"):
                try:
                    gpu_mem = subprocess.check_output("vcgencmd get_mem gpu", shell=True).decode().strip()
                    vram = gpu_mem.split("=")[1] if "=" in gpu_mem else "Unknown"
                    gpu_list.append({
                        "model": "Broadcom VideoCore (Raspberry Pi)",
                        "vram_total": vram,
                        "driver": "Mesa / VC4/V3D"
                    })
                except Exception:
                    gpu_list.append({"model": "Broadcom VideoCore", "vram_total": "Shared", "driver": "Unknown"})

            # Проверка 2.3: ОБЫЧНЫЙ LINUX (PC/Server с AMD, Intel или open-source драйверами)
            elif shutil.which("lspci"):
                try:
                    # Ищем строки с VGA или 3D контроллерами
                    res = subprocess.check_output("lspci | grep -E 'VGA|3D'", shell=True).decode().strip()
                    for line in res.split("\n"):
                        if line:
                            # Пример строки: 00:02.0 VGA compatible controller: Intel Corporation Alder Lake-S GT1 [UHD Graphics 710] (rev 0c)
                            # Забираем всё, что идет после названия контроллера
                            parts = line.split("controller:")
                            model = parts[1].strip() if len(parts) > 1 else line

                            # Для обычного Linux вытащить точный размер VRAM встроенной графики AMD/Intel без sudo сложно.
                            # Напишем базовое определение или Dynamic.
                            gpu_list.append({
                                "model": model,
                                "vram_total": "Dynamic / System Managed",
                                "driver": "Kernel Driver (i915/amdgpu/radeon)"
                            })
                except Exception:
                    pass

            # Фоллбек для Linux, если lspci почему-то нет
            if not gpu_list:
                gpu_list.append({"model": "Generic Linux Display Device", "vram_total": "Unknown", "driver": "Unknown"})

    # Добавляем CUDA версию ко всем GPU NVIDIA
    cuda_ver = get_cuda_version()

    if not gpu_list:
        return [{"model": "Unknown / Integrated", "vram_total": "Unknown", "driver": "Unknown", "cuda": cuda_ver}]

    for gpu in gpu_list:
        if "nvidia" in gpu["model"].lower() or "tegra" in gpu["model"].lower():
            gpu["cuda"] = cuda_ver
        else:
            gpu["cuda"] = "Not Supported"

    return gpu_list


def collect_system_info():
    # Системная информация
    info = {
        "OS": f"{platform.system()} {platform.release()} ({platform.version()})",
        "Python Version": sys.version.split()[0],
        "Architecture": platform.machine(),

        # CPU
        "CPU Model": get_cpu_model(),
        "CPU Cores (Physical)": psutil.cpu_count(logical=False) or "Unknown",
        "CPU Cores (Logical)": psutil.cpu_count(logical=True) or "Unknown",
        "CPU Frequency": get_cpu_frequency(),

        # RAM
        "RAM Total": f"{psutil.virtual_memory().total / (1024 ** 3):.2f} GB",
        "RAM Available": f"{psutil.virtual_memory().available / (1024 ** 3):.2f} GB",
    }

    # GPU
    gpus = get_gpu_info()

    # Вывод результатов в консоль
    print("=== SYSTEM INFO ===")
    for k, v in info.items():
        print(f"{k}: {v}")

    print("\n=== GPU INFO ===")
    for i, gpu in enumerate(gpus, 1):
        print(f"GPU #{i}:")
        print(f"  Model: {gpu['model']}")
        print(f"  VRAM: {gpu['vram_total']}")
        print(f"  Driver Version: {gpu['driver']}")
        print(f"  CUDA Version: {gpu['cuda']}")


if __name__ == "__main__":
    collect_system_info()