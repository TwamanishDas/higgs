import psutil
import platform
from datetime import datetime


def get_metrics() -> dict:
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\")
    net = psutil.net_io_counters()
    battery = psutil.sensors_battery()

    metrics = {
        "cpu_percent": cpu,
        "ram_percent": mem.percent,
        "ram_used_gb": round(mem.used / (1024 ** 3), 1),
        "ram_total_gb": round(mem.total / (1024 ** 3), 1),
        "disk_percent": disk.percent,
        "disk_free_gb": round(disk.free / (1024 ** 3), 1),
        "net_sent_mb": round(net.bytes_sent / (1024 ** 2), 1),
        "net_recv_mb": round(net.bytes_recv / (1024 ** 2), 1),
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "platform": platform.node(),
    }

    if battery:
        metrics["battery_percent"] = battery.percent
        metrics["battery_plugged"] = battery.power_plugged

    return metrics


def get_top_processes(n: int = 10) -> list[dict]:
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
        try:
            info = p.info
            if info["cpu_percent"] is not None:
                procs.append({
                    "pid": info["pid"],
                    "name": info["name"],
                    "cpu": round(info["cpu_percent"], 1),
                    "mem": round(info["memory_percent"] or 0, 1),
                    "status": info["status"],
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    procs.sort(key=lambda x: x["cpu"], reverse=True)
    return procs[:n]
