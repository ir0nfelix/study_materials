"""
Ray Worker Pool (Broker) — тупой параллельный исполнитель очередей.
Без UI, без решений. Только: взять задачу → выполнить скрипт → переместить результат.
Запускается агентом через скилл /resume или /add (для плейлистов).
"""
import os
import sys
import time
import json
import logging
import threading
import subprocess
import ray

# ---------------------------------------------------------------------------
# Конфигурация
# ---------------------------------------------------------------------------
CACHE_DIR = os.environ.get("APP_CACHE_DIR", ".cache")
DIR_DOWNLOAD = os.path.join(CACHE_DIR, "00_pending_download")
DIR_TRIAGE = os.path.join(CACHE_DIR, "01_pending_triage")
DIR_EXPERT = os.path.join(CACHE_DIR, "02_pending_expert")
DIR_TESTING = os.path.join(CACHE_DIR, "02b_pending_testing")
DIR_FINAL = os.path.join(CACHE_DIR, "03_pending_final")
DIR_PUBLISH = os.path.join(CACHE_DIR, "04_pending_publish")
DIR_COMPLETED = os.path.join(CACHE_DIR, "99_completed")
DIR_REJECTED = os.path.join(CACHE_DIR, "99_rejected")
DIR_RAW = os.environ.get("APP_RAW_DIR", "raw_transcripts")
STATUS_FILE = os.path.join(CACHE_DIR, "broker_status.json")

ALL_DIRS = [
    DIR_DOWNLOAD, DIR_TRIAGE, DIR_EXPERT, DIR_TESTING,
    DIR_FINAL, DIR_PUBLISH, DIR_COMPLETED, DIR_REJECTED, DIR_RAW,
]

# ---------------------------------------------------------------------------
# Логирование
# ---------------------------------------------------------------------------
os.makedirs(CACHE_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(CACHE_DIR, "broker.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("broker")

# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------
def ensure_dirs():
    for d in ALL_DIRS:
        os.makedirs(d, exist_ok=True)

def write_status():
    """Записывает текущее состояние очередей в JSON для чтения агентом."""
    try:
        status = {}
        for d in ALL_DIRS:
            if os.path.exists(d):
                files = [f for f in os.listdir(d) if f.endswith(".json")]
                status[os.path.basename(d)] = len(files)
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(status, f, indent=2)
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Ray-задачи (воркеры)
# ---------------------------------------------------------------------------
@ray.remote
def run_download(video_id):
    subprocess.run(
        [sys.executable, "agents/01_ingestion/download.py", video_id],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

@ray.remote
def run_miner(txt_path):
    subprocess.run(
        [sys.executable, "agents/02_miner/mine.py", txt_path],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

@ray.remote
def run_expert(file_path):
    subprocess.run(
        [sys.executable, "agents/03_expert/solve.py", file_path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

@ray.remote
def run_facilitator(file_path):
    subprocess.run(
        [sys.executable, "agents/04_facilitator/test_runner.py", file_path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

@ray.remote
def run_publisher(file_path):
    subprocess.run(
        [sys.executable, "agents/05_publisher/publish.py", file_path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

# ---------------------------------------------------------------------------
# Диспетчеры (бесконечные циклы сканирования очередей)
# ---------------------------------------------------------------------------
def download_dispatcher():
    while True:
        try:
            if os.path.exists(DIR_DOWNLOAD):
                for f in os.listdir(DIR_DOWNLOAD):
                    if not f.endswith(".json"):
                        continue
                    orig = os.path.join(DIR_DOWNLOAD, f)
                    proc = orig + ".processing"
                    try:
                        os.rename(orig, proc)
                        with open(proc, "r", encoding="utf-8") as jf:
                            data = json.load(jf)
                        video_id = data.get("video_id")
                        log.info("Download: starting %s", video_id)
                        ray.get(run_download.remote(video_id))
                        os.rename(proc, os.path.join(DIR_COMPLETED, f))
                        log.info("Download: done %s", video_id)
                    except FileNotFoundError:
                        continue
                    except Exception as e:
                        log.warning("Download failed %s: %s", f, e)
                        try:
                            os.rename(proc, orig)
                        except Exception:
                            pass
        except Exception:
            pass
        write_status()
        time.sleep(10)


def miner_dispatcher():
    while True:
        try:
            if os.path.exists(DIR_RAW):
                for txt_file in os.listdir(DIR_RAW):
                    if not (txt_file.endswith(".txt") or txt_file.endswith(".vtt")):
                        continue
                    txt_path = os.path.join(DIR_RAW, txt_file)
                    marker = txt_path + ".processed"
                    if os.path.exists(marker):
                        continue
                    with open(marker, "w") as mf:
                        mf.write("")
                    log.info("Miner: starting %s", txt_file)
                    try:
                        ray.get(run_miner.remote(txt_path))
                        log.info("Miner: done %s", txt_file)
                    except Exception as e:
                        log.warning("Miner failed %s: %s", txt_file, e)
                        os.remove(marker)
        except Exception:
            pass
        write_status()
        time.sleep(5)


def expert_dispatcher():
    while True:
        try:
            for f in os.listdir(DIR_EXPERT):
                if not f.endswith(".json"):
                    continue
                orig = os.path.join(DIR_EXPERT, f)
                proc = orig + ".processing"
                try:
                    os.rename(orig, proc)
                    log.info("Expert: starting %s", f)
                    ray.get(run_expert.remote(proc))
                    log.info("Expert: done %s", f)
                except FileNotFoundError:
                    continue
                except Exception as e:
                    log.warning("Expert failed %s: %s", f, e)
        except Exception:
            pass
        write_status()
        time.sleep(3)


def facilitator_dispatcher():
    while True:
        try:
            for f in os.listdir(DIR_TESTING):
                if not f.endswith(".json"):
                    continue
                orig = os.path.join(DIR_TESTING, f)
                proc = orig + ".processing"
                try:
                    os.rename(orig, proc)
                    log.info("Facilitator: starting %s", f)
                    ray.get(run_facilitator.remote(proc))
                    log.info("Facilitator: done %s", f)
                except FileNotFoundError:
                    continue
                except Exception as e:
                    log.warning("Facilitator failed %s: %s", f, e)
        except Exception:
            pass
        write_status()
        time.sleep(3)


def publisher_dispatcher():
    while True:
        try:
            for f in os.listdir(DIR_PUBLISH):
                if not f.endswith(".json"):
                    continue
                orig = os.path.join(DIR_PUBLISH, f)
                proc = orig + ".processing"
                try:
                    os.rename(orig, proc)
                    log.info("Publisher: starting %s", f)
                    ray.get(run_publisher.remote(proc))
                    log.info("Publisher: done %s", f)
                except FileNotFoundError:
                    continue
                except Exception as e:
                    log.warning("Publisher failed %s: %s", f, e)
        except Exception:
            pass
        write_status()
        time.sleep(3)


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    ensure_dirs()
    ray.init(ignore_reinit_error=True)
    log.info("Ray Broker started. Scanning queues...")
    write_status()

    threads = [
        ("download", download_dispatcher),
        ("miner", miner_dispatcher),
        ("expert", expert_dispatcher),
        ("facilitator", facilitator_dispatcher),
        ("publisher", publisher_dispatcher),
    ]
    for name, fn in threads:
        t = threading.Thread(target=fn, daemon=True, name=name)
        t.start()
        log.info("Dispatcher '%s' started.", name)

    try:
        while True:
            time.sleep(60)
            write_status()
    except KeyboardInterrupt:
        log.info("Broker shutting down.")
        ray.shutdown()
