import json, time, os, atexit, signal
from pathlib import Path

CACHE_DIR = Path(os.getenv("TESTCASE_BASE_PATH", "/default/path"))
METADATA_PATH = CACHE_DIR / "cache_meta.json"
MAX_CACHED_PROBLEMS = 5
UPDATE_THRESHOLD = 10

cache_meta = {}
update_count = 0

def load_metadata():
    global cache_meta
    if METADATA_PATH.exists():
        with open(METADATA_PATH) as f:
            cache_meta = json.load(f)

def save_metadata():
    with open(METADATA_PATH, "W") as f:
        json.dump(cache_meta, f)

def update_usage(problem_id: int):
    global update_count
    cache_meta[str(problem_id)] = int(time.time())
    update_count += 1

    # 캐시 개수 초과 시 가장 오래된 캐시 제거 (LRU)
    enforce_cache_limit()

    if update_count >= UPDATE_THRESHOLD:
        save_metadata()
        update_count = 0

def enforce_cache_limit():
    if len(cache_meta) <= MAX_CACHED_PROBLEMS:
        return
    oldest = sorted(cache_meta.items(), key=lambda x: x[1])[0][0]
    target_path = CACHE_DIR / f"prob_{int(oldest):05d}"
    if target_path.exists():
        import shutil
        shutil.rmtree(target_path)
    del cache_meta[oldest]

# graceful exit hooks
def graceful_exit():
    save_metadata()

atexit.register(graceful_exit)
signal.signal(signal.SIGTERM, lambda s, f: graceful_exit())
signal.signal(signal.SIGINT, lambda s, f: graceful_exit())