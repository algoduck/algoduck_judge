from pathlib import Path
import os
import boto3
import logging

def ensure_testcases_cached(problem_id: int, base_path: str, bucket_name: str):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    """
    문제 ID에 해당하는 테스트케이스 디렉토리가 base_path에 없다면 S3에서 가져온다.
    """
    local_problem_dir = Path(base_path) / f"prob_{problem_id:05d}"
    logger.info(f"초기 local_problem_dir ={local_problem_dir}")
    
    # 1. 캐시 존재 및 비어 있지 않으면 바로 사용
    if local_problem_dir.exists() and any(local_problem_dir.iterdir()):
        return local_problem_dir

    # 2. 없으면 디렉토리 생성
    os.makedirs(local_problem_dir, exist_ok=True)

    # 3. S3에서 파일 목록 가져오기 및 다운로드
    s3_prefix = f"prob_{problem_id:05d}/"
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket_name, Prefix=s3_prefix)

    for page in pages:
        for obj in page.get("Contents", []):
            key = obj["Key"]
            filename = key.split("/")[-1]
            local_path = local_problem_dir / filename
            s3.download_file(bucket_name, key, str(local_path))

    logger.info(f"최종 local_problem_dir ={local_problem_dir}")
    return local_problem_dir
