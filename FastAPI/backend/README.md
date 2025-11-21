실행순서 

압축해제한 venv 폴더를 backend 안에 집어넣기


1. FASTAPI 폴더 오픈
2. 터미널에 cmd오픈
3. cd backend 입력
4. cmd콘솔에 pip install -r requirements.txt 입력
5. FastAPI 폴더에서 venv\Scripts\activate 입력해 venv 환경 진입
6. cd backend로 backend 재진입
7. python -m uvicorn app.main:app --reload 입력후 서버 실행확인



오류
1. fastapi 경로를 못불러올 경우 ctrl + Shift + P C:\Users\cs3-32\Desktop\FastAPI\backend\venv\Scripts\python.exe
입력(경로 본인에 맞게 변경)
venv 환경변수가 있을시 해당 환경변수로 설정

2. fastapi가 있는지 확인방법
콘솔창에 pip show fastapi
