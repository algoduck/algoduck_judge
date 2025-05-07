from fastapi import HTTPException
import os
import re
from pathlib import Path
import resource
import shutil
import subprocess
import uuid
import logging
from app.models import SubmissionRequest, SubmissionResponse

def sort_key(path):
    # 숫자만 추출하여 정렬에 사용
    return int(re.sub(r"\D", "", path.stem))

def judge_submission(req: SubmissionRequest) -> SubmissionResponse:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    logger.info(f"Start judging: problemId={req.problemId}, memberId={req.memberId}")

    if req.language != 1:
        logger.warning("Unsupported language requested: %s", req.language)
        raise HTTPException(status_code=400, detail="Only Java (language=1) is supported")

    TESTCASE_BASE_PATH = Path(os.getenv("TESTCASE_BASE_PATH", "/default/path"))
    logger.info("TESTCASE_BASE_PATH loaded: %s", TESTCASE_BASE_PATH)

    problem_dir = TESTCASE_BASE_PATH / f"prob_{req.problemId:05d}"
    input_files = sorted(problem_dir.glob("input*"), key=sort_key)
    output_files = sorted(problem_dir.glob("output*"), key=sort_key)

    logger.info(f"Number of input_files: {len(input_files)}, output_files: {len(output_files)}")
    logger.debug(f"Input files: {input_files}")
    logger.debug(f"Output files: {output_files}")

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
                stderr=compile_proc.stderr.decode()
            )

        for input_path, output_path in zip(input_files, output_files):
            logger.info("Running test case: %s", input_path.name)
            with open(input_path, "r") as fin, open(output_path, "r") as fout:
                input_data = fin.read()
                expected_output = fout.read().strip()

            try:
                run_proc = subprocess.run(
                    ["java", "-cp", str(temp_dir), "Main"],
                    input=input_data.encode(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=max(1.0, req.timeLimitation / 1000),
                    preexec_fn=lambda: resource.setrlimit(
                        resource.RLIMIT_AS,
                        (req.memoryLimitation * 1024 * 1024, req.memoryLimitation * 1024 * 1024)
                    )
                )
            except subprocess.TimeoutExpired:
                logger.warning("Time limit exceeded for test case: %s", input_path.name)
                return SubmissionResponse(result="TLE", message="Time limit exceeded", stdout="", stderr="")
            except MemoryError:
                logger.warning("Memory limit exceeded for test case: %s", input_path.name)
                return SubmissionResponse(result="MLE", message="Memory limit exceeded", stdout="", stderr="")

            if run_proc.returncode != 0:
                logger.warning("Runtime error in test case: %s", input_path.name)
                return SubmissionResponse(
                    result="RE",
                    message="Runtime error",
                    stdout=run_proc.stdout.decode(),
                    stderr=run_proc.stderr.decode()
                )

            actual_output = run_proc.stdout.decode().strip()
            if actual_output != expected_output:
                logger.info("Wrong answer in test case: %s", input_path.name)
                return SubmissionResponse(
                    result="WA",
                    message="Wrong answer",
                    stdout=actual_output,
                    stderr=""
                )

        logger.info("All test cases passed successfully.")
        return SubmissionResponse(result="AC", message="Accepted", stdout="", stderr="")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.info("Temporary directory cleaned up.")
