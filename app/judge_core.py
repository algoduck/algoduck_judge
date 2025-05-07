from fastapi import HTTPException
import os
from pathlib import Path
import resource
import shutil
import subprocess
import uuid
import logging
from app.models import SubmissionRequest, SubmissionResponse

def judge_submission(req : SubmissionRequest) -> SubmissionResponse:
    logger = logging.getLogger(__name__)

    logger.info(f"Start judging: problemId={req.problemId}, memberId={req.memberId}")

    if req.language != 1:  # Java만 지원
        logger.exception("Java 언어만 채점 지원")
        raise HTTPException(status_code=400, detail="Only Java (language=1) is supported")

    # 환경변수에서 경로를 불러와 Path 객체로 사용
    TESTCASE_BASE_PATH = Path(os.getenv("TESTCASE_BASE_PATH", "/default/path"))
    problem_dir = TESTCASE_BASE_PATH / f"prob_{req.problemId:05d}"
    input_files = sorted(problem_dir.glob("input*"), key=sort_key)
    output_files = sorted(problem_dir.glob("output*"), key=sort_key)

    logger.info(f"Number of inputs: {len(input_files)}, outputs: {len(output_files)}")
    logger.info(f"input_files: {input_files}")
    logger.info(f"output_files: {output_files}")

    if not input_files or not output_files or len(input_files) != len(output_files):
        raise HTTPException(status_code=500, detail="Invalid or missing testcases")

    temp_dir = Path(f"/tmp/judge_{uuid.uuid4().hex[:8]}")
    os.makedirs(temp_dir, exist_ok=True)

    try:
        # 1. 코드 저장

        logger.info(f"코드 저장")
        java_file = temp_dir / "Main.java"
        with open(java_file, "w") as f:
            f.write(req.sourceCode)

        # 2. 컴파일
        logger.info(f"Compiling Java file at {java_file}")
        compile_cmd = ["javac", str(java_file)]
        compile_proc = subprocess.run(compile_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if compile_proc.returncode != 0:
            return SubmissionResponse(
                result="CE",
                message="Compilation failed",
                stdout=compile_proc.stdout.decode(),
                stderr=compile_proc.stderr.decode()
            )

        # 3. 테스트케이스별 실행
        for input_path, output_path in zip(input_files, output_files):
            logger.info(f"Running test case {input_path.name}")
            with open(input_path, "r") as fin, open(output_path, "r") as fout:
                input_data = fin.read()
                expected_output = fout.read().strip()

            try:
                run_proc = subprocess.run(
                    ["java", "-cp", str(temp_dir), "Main"],
                    input=input_data.encode(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=req.timeLimitation / 1000,  # ms -> s
                    preexec_fn=lambda: resource.setrlimit(
                        resource.RLIMIT_AS,
                        (req.memoryLimitation * 1024 * 1024, req.memoryLimitation * 1024 * 1024)
                    )
                )
            except subprocess.TimeoutExpired:
                return SubmissionResponse(result="TLE", message="Time limit exceeded", stdout="", stderr="")
            except MemoryError:
                return SubmissionResponse(result="MLE", message="Memory limit exceeded", stdout="", stderr="")

            if run_proc.returncode != 0:
                return SubmissionResponse(
                    result="RE",
                    message="Runtime error",
                    stdout=run_proc.stdout.decode(),
                    stderr=run_proc.stderr.decode()
                )

            actual_output = run_proc.stdout.decode().strip()
            if actual_output != expected_output:
                return SubmissionResponse(
                    result="WA",
                    message="Wrong answer",
                    stdout=actual_output,
                    stderr=""
                )

        # 4. 모든 테스트케이스 통과
        logger.info("All test cases passed successfully")
        return SubmissionResponse(result="AC", message="Accepted", stdout="", stderr="")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def sort_key(path):
    return int(path.stem.lstrip('input').lstrip('output'))