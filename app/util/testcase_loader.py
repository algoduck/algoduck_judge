from pathlib import Path
import os, logging
import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from app.util.cache_manager import update_usage

S3_CFG = Config(
    region_name="ap-northeast-2",   # 실제 리전으로
    connect_timeout=5,
    read_timeout=15,
    retries={"max_attempts": 3, "mode": "standard"},
)

def ensure_testcases_cached(problem_id: int, base_path: str, bucket_name: str):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    local_problem_dir = Path(base_path) / f"prob_{problem_id:05d}"
    logger.info("초기 local_problem_dir = %s", local_problem_dir)

    if local_problem_dir.exists() and any(local_problem_dir.iterdir()):
        return local_problem_dir

    os.makedirs(local_problem_dir, exist_ok=True)

    prefix = f"prob_{problem_id:05d}/"
    s3 = boto3.client("s3", config=S3_CFG)

    try:
        paginator = s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

        found = False
        for page in pages:
            contents = page.get("Contents", [])
            logger.info("S3 page keys=%d", len(contents))
            for obj in contents:
                key = obj["Key"]
                size = obj.get("Size", -1)

                # 1) 디렉터리 플레이스홀더/빈 파일명 스킵
                if key.endswith("/"):
                    logger.info("skip dir placeholder: %s", key)
                    continue
                filename = key.rsplit("/", 1)[-1]
                if not filename:
                    logger.info("skip empty filename key: %s", key)
                    continue

                # 2) 다운로드
                dst = local_problem_dir / filename
                logger.info("download: %s (size=%s) -> %s", key, size, dst)
                s3.download_file(bucket_name, key, str(dst))
                found = True

        if not found:
            logger.warning("No files under prefix=%s", prefix)

    except (ClientError, BotoCoreError) as e:
        logger.exception("S3 다운로드 실패: %s", e)
        raise

    logger.info("최종 local_problem_dir = %s", local_problem_dir)
    update_usage(problem_id)
    return local_problem_dir
