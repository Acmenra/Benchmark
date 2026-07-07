from hardware.entities import CPUInfo

# # CPU
# "CPU Model": get_cpu_model(),
# "CPU Cores (Physical)": psutil.cpu_count(logical=False) or "Unknown",
# "CPU Cores (Logical)": psutil.cpu_count(logical=True) or "Unknown",
# "CPU Frequency": get_cpu_frequency(),

def collect_cpu() -> CPUInfo:
    ...
    # смотреть system_info.py 