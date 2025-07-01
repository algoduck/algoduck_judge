# Judge Server

FastAPI 기반의 온라인 채점 서버입니다.  
사용자의 Java 소스코드를 컴파일하고 테스트케이스로 채점하여 결과를 반환합니다.

---

## 전체 설치 및 실행 방법

### 0. Python 설치

- Python 3.10 이상이 설치되어 있어야 합니다.
- 아래 명령어로 버전 확인:

```bash
python --version
```

- 설치 안 되어 있다면 [https://www.python.org/downloads/](https://www.python.org/downloads/) 에서 설치 후, `python`, `pip` 명령어가 동작하는지 확인해주세요.

---

### 1. 프로젝트 클론

```bash
git clone https://github.com/jwelyl/algoduck_judge.git
cd algoduck_judge
```

---

### 2. 가상환경 생성 및 활성화

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

---

### 3. 필수 패키지 설치

```bash
pip install -r requirements.txt
```

---

### 4. Git Hook 및 코드 스타일 검사 설정

#### 4-1. pre-commit 설치

```bash
pip install pre-commit
```

#### 4-2. pre-commit 훅 설치

```bash
pre-commit install
```

> 커밋 전에 Python 코드 스타일을 자동으로 검사하며, [Black](https://black.readthedocs.io/en/stable/) 포매터가 적용됩니다.  
> 코드 스타일을 지키지 않으면 커밋이 차단됩니다.

#### 4-3. 커밋 메시지 자동 템플릿 적용

```bash
bash hooks/install-hooks.sh
```

---

### 5. FastAPI 서버 실행

```bash
uvicorn app.main:app --reload
```

> 접속 주소: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)  
> Swagger UI에서 API 테스트가 가능합니다.

---

## 프로젝트 구조

```
judge_server/
├── app
    ├──__init__.py
    ├── judge
    │   ├── core
    │   │   ├── judge_core.py
    │   │   └── judge_ws.py
    │   ├── model
    │   │   └── models.py
    │   └── queue
    │       └── judge_consumer.py
    ├── main.py
    └── util
        ├── cache_manager.py
        └── testcase_loader.py
```

---

## ✅ 브랜치 및 커밋 규칙

- 브랜치명 형식: `[type]/[team]/[desc]/[author]`
  - 예시: `f/be/fix-bug/pong`
- 커밋 시 자동으로 메시지 템플릿이 삽입됩니다.
- 사용 가능한 브랜치 타입: `feat`, `bugfix`, `docs`, `test`, `chore`, `refactor`

---

## 🙋‍♂️ 문의

> Author: Your Name  
> GitHub: [https://github.com/your-username](https://github.com/your-username)
