def judge_submission(submission):
    return {
        "status": "OK",
        "message": f"채점 요청 완료 - 문제 ID: {submission.problemId}",
        "sourceCode" : submission.sourceCode
    }