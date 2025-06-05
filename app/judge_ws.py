# app/ws_judge.py

from fastapi import WebSocket, WebSocketDisconnect
from app.models import SubmissionRequest, JudgeProgressResponse
from app.util.testcase_loader import ensure_testcases_cached
import os, uuid, re, shutil, subprocess, time, resource
from pathlib import Path
import logging

def sort_key(path):
    return int(re.sub(r"\D", "", path.stem))

async def judge_websocket_handler(websocket: WebSocket):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    await websocket.accept()

    try:
        req_json = await websocket.receive_json()
        req = SubmissionRequest(**req_json)

        if req.language.lower() != "java":
            await websocket.send_json(JudgeProgressResponse(
                result="CE",
                message="Only Java is supported",
                percentage=0
            ).model_dump())
            return

        TESTCASE_BASE_PATH = Path(os.getenv("TESTCASE_BASE_PATH", "/default/path"))
        TESTCASE_S3_BUCKET_URL = os.getenv("TESTCASE_S3_BUCKET_URL")

        problem_dir = ensure_testcases_cached(
            problem_id=req.problemId,
            base_path=TESTCASE_BASE_PATH,
            bucket_name=TESTCASE_S3_BUCKET_URL
        )

        input_files = sorted(problem_dir.glob("input*"), key=sort_key)
        output_files = sorted(problem_dir.glob("output*"), key=sort_key)

        if not input_files or len(input_files) != len(output_files):
            await websocket.send_json(JudgeProgressResponse(
                result="CE",
                message="Invalid or missing testcases",
                percentage=0
            ).model_dump())
            return

        total_cnt = len(input_files)
        temp_dir = Path(f"/tmp/judge_{uuid.uuid4().hex[:8]}")
        os.makedirs(temp_dir, exist_ok=True)

        java_file = temp_dir / "Main.java"
        with open(java_file, "w") as f:
            f.write(req.sourceCode)

        compile_cmd = ["javac", str(java_file)]
        compile_proc = subprocess.run(compile_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if compile_proc.returncode != 0:
            await websocket.send_json(JudgeProgressResponse(
                result="CE",
                message="Compilation failed",
                stdout=compile_proc.stdout.decode(),
                stderr=compile_proc.stderr.decode(),
                executionTime=0,
                memoryUsage=0,
                percentage=0
            ).model_dump())
            return

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

                time_taken_ms = int((end_time - start_time) * 1000)
                memory_used_kb = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss

                max_time_ms = max(max_time_ms, time_taken_ms)
                max_memory_kb = max(max_memory_kb, memory_used_kb)

            except subprocess.TimeoutExpired:
                await websocket.send_json(JudgeProgressResponse(
                    index=i,
                    result="TLE",
                    message="Time limit exceeded",
                    executionTime=req.timeLimitation,
                    memoryUsage=0,
                    percentage=int(((i + 1) / total_cnt) * 100)
                ).model_dump())
                break

            stderr_decoded = run_proc.stderr.decode()
            if run_proc.returncode != 0 or "OutOfMemoryError" in stderr_decoded:
                await websocket.send_json(JudgeProgressResponse(
                    index=i,
                    result="MLE" if "OutOfMemoryError" in stderr_decoded else "RE",
                    message="Memory limit exceeded" if "OutOfMemoryError" in stderr_decoded else "Runtime error",
                    stdout=run_proc.stdout.decode(),
                    stderr=stderr_decoded,
                    executionTime=time_taken_ms,
                    memoryUsage=memory_used_kb,
                    percentage=int(((i + 1) / total_cnt) * 100)
                ).model_dump())
                break

            actual_output = run_proc.stdout.decode().strip()
            if actual_output != expected_output:
                await websocket.send_json(JudgeProgressResponse(
                    index=i,
                    result="WA",
                    message="Wrong answer",
                    stdout=actual_output,
                    executionTime=time_taken_ms,
                    memoryUsage=memory_used_kb,
                    percentage=int(((i + 1) / total_cnt) * 100)
                ).model_dump())
                break

            await websocket.send_json(JudgeProgressResponse(
                index=i,
                result="PASS",
                message="Passed",
                stdout=actual_output,
                executionTime=time_taken_ms,
                memoryUsage=memory_used_kb,
                percentage=int(((i + 1) / total_cnt) * 100)
            ).model_dump())

        else:
            await websocket.send_json(JudgeProgressResponse(
                result="AC",
                message="All testcases passed",
                percentage=100,
                executionTime=max_time_ms,
                memoryUsage=max_memory_kb
            ).model_dump())

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        await websocket.close()
