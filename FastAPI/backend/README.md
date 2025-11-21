실행순서 

압축해제한 venv 폴더를 backend 안에 집어넣기

1. FAASTAPI 폴더 오픈
2. 터미널에 cmd오픈
3. cd backend 입력
4. venv\Scripts\activate 입력
5. python -m uvicorn app.main:app --reload 입력후 서버 실행확인



오류
1. fastapi 경로를 못불러올 경우 콘솔창에 C:\Users\cs3-32\Desktop\FastAPI\backend\venv\Scripts\python.exe
입력(경로 본인에 맞게 변경)

2. fastapi가 있는지 확인방법
콘솔창에 pip show fastapi