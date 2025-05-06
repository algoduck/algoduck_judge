def judge_submission(submissionRequest):
    return {
        "status": "OK",
        "message": f"채점 요청 완료 - 문제 ID: {submissionRequest.problemId}",
        "sourceCode" : submissionRequest.sourceCode
    }