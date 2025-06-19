# app/judge/core/judge_core.py

from app.util.testcase_loader import ensure_testcases_cached
import os
import re
import time
import resource
from pathlib import Path
import shutil
import subprocess
import uuid
import logging
from app.judge.model.models import SubmissionRequest, SubmissionResponse

def sort_key(path):
    return int(re.sub(r"\D", "", path.stem))

def judge_submission(request_json: dict) -> dict:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    logger.info(f"Start judging: problemId={request_json.get('problemId')}")

    try:
        req = SubmissionRequest(**request_json)
    except Exception as e:
        logger.error("Invalid request format: %s", str(e))
        return SubmissionResponse(
            result="FAIL",
            message="Invalid request format",
            stdout="",
            stderr=str(e),
            executionTime=0,
            memoryUsage=0,
            percentage=0
        ).model_dump()

    if req.language.lower() != "java":
        logger.warning("Unsupported language requested: %s", req.language)
        return SubmissionResponse(
            result="CE",
            message="Only Java is supported",
            stdout="",
            stderr="Unsupported language",
            executionTime=0,
            memoryUsage=0,
            percentage=0
        ).model_dump()

    TESTCASE_BASE_PATH = Path(os.getenv("TESTCASE_BASE_PATH", "/default/path"))
    TESTCASE_S3_BUCKET_URL = os.getenv("TESTCASE_S3_BUCKET_URL")

    problem_dir = ensure_testcases_cached(
        problem_id=req.problemId,
        base_path=TESTCASE_BASE_PATH,
        bucket_name=TESTCASE_S3_BUCKET_URL
    )

    input_files = sorted(problem_dir.glob("input*"), key=sort_key)
    output_files = sorted(problem_dir.glob("output*"), key=sort_key)

    if not input_files or not output_files or len(input_files) != len(output_files):
        logger.error("Invalid or missing testcases.")
        return SubmissionResponse(
            result="FAIL",
            message="Invalid or missing testcases",
            stdout="",
            stderr="",
            executionTime=0,
            memoryUsage=0,
            percentage=0
        ).model_dump()

    total_cnt = len(input_files)
    temp_dir = Path(f"/tmp/judge_{uuid.uuid4().hex[:8]}")
    os.makedirs(temp_dir, exist_ok=True)

    try:
        java_file = temp_dir / "Main.java"
        with open(java_file, "w") as f:
            f.write(req.sourceCode)

        compile_cmd = ["javac", str(java_file)]
        compile_proc = subprocess.run(compile_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if compile_proc.returncode != 0:
            return SubmissionResponse(
                result="CE",
                message="Compilation failed",
                stdout=compile_proc.stdout.decode(),
                stderr=compile_proc.stderr.decode(),
                executionTime=0,
                memoryUsage=0,
                percentage=0
            ).model_dump()

        max_time_ms = 0
        max_memory_kb = 0

        for i, (input_path, output_path) in enumerate(zip(input_files, output_files)):
            with open(input_path, "r") as fin, open(output_path, "r") as fout:
                input_data = fin.read()
                expected_output = fout.read().strip()

            try:
                start_time = time.perf_counter()
                run_proc = subprocess.run(
                    ["java", f"-Xmx{req.memoryLimitation}m", "-cp", str(temp_dir), "Main"],
                    input=input_data.encode(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=max(1.0, req.timeLimitation / 1000)
                )
                end_time = time.perf_counter()
                usage = resource.getrusage(resource.RUSAGE_CHILDREN)

                time_taken_ms = int((end_time - start_time) * 1000)
                memory_used_kb = usage.ru_maxrss

                max_time_ms = max(max_time_ms, time_taken_ms)
                max_memory_kb = max(max_memory_kb, memory_used_kb)

            except subprocess.TimeoutExpired:
                return SubmissionResponse(
                    result="TLE",
                    message="Time limit exceeded",
                    stdout="",
                    stderr="",
                    executionTime=req.timeLimitation,
                    memoryUsage=0,
                    percentage=int(((i + 1) / total_cnt) * 100)
                ).model_dump()
            except MemoryError:
                return SubmissionResponse(
                    result="MLE",
                    message="Memory limit exceeded",
                    stdout="",
                    stderr="",
                    executionTime=0,
                    memoryUsage=0,
                    percentage=int(((i + 1) / total_cnt) * 100)
                ).model_dump()

            if run_proc.returncode != 0:
                if "OutOfMemoryError" in run_proc.stderr.decode():
                    return SubmissionResponse(
                        result="MLE",
                        message="Memory limit exceeded",
                        stdout=run_proc.stdout.decode(),
                        stderr=run_proc.stderr.decode(),
                        executionTime=time_taken_ms,
                        memoryUsage=memory_used_kb,
                        percentage=int(((i + 1) / total_cnt) * 100)
                    ).model_dump()

                return SubmissionResponse(
                    result="RE",
                    message="Runtime error",
                    stdout=run_proc.stdout.decode(),
                    stderr=run_proc.stderr.decode(),
                    executionTime=time_taken_ms,
                    memoryUsage=memory_used_kb,
                    percentage=int(((i + 1) / total_cnt) * 100)
                ).model_dump()

            actual_output = run_proc.stdout.decode().strip()
            if actual_output != expected_output:
                return SubmissionResponse(
                    result="WA",
                    message="Wrong answer",
                    stdout=actual_output,
                    stderr="",
                    executionTime=time_taken_ms,
                    memoryUsage=memory_used_kb,
                    percentage=int(((i + 1) / total_cnt) * 100)
                ).model_dump()

        return SubmissionResponse(
            result="AC",
            message="Accepted",
            stdout="",
            stderr="",
            executionTime=max_time_ms,
            memoryUsage=max_memory_kb,
            percentage=100
        ).model_dump()

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
