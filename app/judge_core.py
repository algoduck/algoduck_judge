from app.util.testcase_loader import ensure_testcases_cached
from fastapi import HTTPException
import os
import re
import time
import resource
from pathlib import Path
import shutil
import subprocess
import uuid
import logging
from app.models import SubmissionRequest, SubmissionResponse

def sort_key(path):
    return int(re.sub(r"\D", "", path.stem))

def judge_submission(req: SubmissionRequest) -> SubmissionResponse:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    logger.info(f"Start judging: problemId={req.problemId}, memberId={req.memberId}")

    if req.language != 1:
        logger.warning("Unsupported language requested: %s", req.language)
        raise HTTPException(status_code=400, detail="Only Java (language=1) is supported")

    TESTCASE_BASE_PATH = Path(os.getenv("TESTCASE_BASE_PATH", "/default/path"))
    TESTCASE_S3_BUCKET_URL = os.getenv("TESTCASE_S3_BUCKET_NAME")
    logger.info("TESTCASE_BASE_PATH loaded: %s", TESTCASE_BASE_PATH)
    logger.info("TESTCASE_S3_BUCKET_URL loaded: %s", TESTCASE_S3_BUCKET_URL)

    # problem_dir = TESTCASE_BASE_PATH / f"prob_{req.problemId:05d}"

    problem_dir = ensure_testcases_cached(
        problem_id=req.problemId,
        base_path=TESTCASE_BASE_PATH,
        bucket_name=TESTCASE_S3_BUCKET_URL
    )

    logger.info(f"problem_dir : {problem_dir}")

    input_files = sorted(problem_dir.glob("input*"), key=sort_key)
    output_files = sorted(problem_dir.glob("output*"), key=sort_key)

    logger.info(f"Number of input_files: {len(input_files)}, output_files: {len(output_files)}")

    if not input_files or not output_files or len(input_files) != len(output_files):
        logger.error("Invalid or missing testcases. Path: %s, Inputs: %d, Outputs: %d",
                     problem_dir, len(input_files), len(output_files))
        raise HTTPException(status_code=500, detail="Invalid or missing testcases")

    temp_dir = Path(f"/tmp/judge_{uuid.uuid4().hex[:8]}")
    os.makedirs(temp_dir, exist_ok=True)
    logger.info("Temporary directory created: %s", temp_dir)

    try:
        java_file = temp_dir / "Main.java"
        with open(java_file, "w") as f:
            f.write(req.sourceCode)
        logger.info("Java source code written to %s", java_file)

        compile_cmd = ["javac", str(java_file)]
        logger.info("Compiling Java code...")
        compile_proc = subprocess.run(compile_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if compile_proc.returncode != 0:
            logger.warning("Compilation failed.")
            return SubmissionResponse(
                result="CE",
                message="Compilation failed",
                stdout=compile_proc.stdout.decode(),
                stderr=compile_proc.stderr.decode(),
                time_ms=0,
                memory_kb=0
            )

        for input_path, output_path in zip(input_files, output_files):
            logger.info("Running test case: %s", input_path.name)
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
                memory_used_kb = usage.ru_maxrss
                time_taken_ms = (end_time - start_time) * 1000

            except subprocess.TimeoutExpired:
                logger.warning("Time limit exceeded for test case: %s", input_path.name)
                return SubmissionResponse(result="TLE", message="Time limit exceeded", stdout="", stderr="", time_ms=req.timeLimitation, memory_kb=0)
            except MemoryError:
                logger.warning("Memory limit exceeded for test case: %s", input_path.name)
                return SubmissionResponse(result="MLE", message="Memory limit exceeded", stdout="", stderr="", time_ms=0, memory_kb=0)

            if run_proc.returncode != 0:
                logger.warning("Runtime error in test case: %s", input_path.name)
                logger.warning("stdout: %s", run_proc.stdout.decode())
                logger.warning("stderr: %s", run_proc.stderr.decode())

                if "OutOfMemoryError" in run_proc.stderr.decode():
                    return SubmissionResponse(
                        result="MLE",
                        message="Memory limit exceeded",
                        stdout=run_proc.stdout.decode(),
                        stderr=run_proc.stderr.decode(),
                        time_ms=time_taken_ms,
                        memory_kb=memory_used_kb
                    )

                return SubmissionResponse(
                    result="RE",
                    message="Runtime error",
                    stdout=run_proc.stdout.decode(),
                    stderr=run_proc.stderr.decode(),
                    time_ms=time_taken_ms,
                    memory_kb=memory_used_kb
                )

            actual_output = run_proc.stdout.decode().strip()
            if actual_output != expected_output:
                logger.info("Wrong answer in test case: %s", input_path.name)
                return SubmissionResponse(
                    result="WA",
                    message="Wrong answer",
                    stdout=actual_output,
                    stderr="",
                    time_ms=time_taken_ms,
                    memory_kb=memory_used_kb
                )

        logger.info("All test cases passed successfully.")
        return SubmissionResponse(result="AC", message="Accepted", stdout="", stderr="", time_ms=time_taken_ms, memory_kb=memory_used_kb)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.info("Temporary directory cleaned up.")
