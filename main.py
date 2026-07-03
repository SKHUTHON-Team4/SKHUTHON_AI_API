from fastapi import FastAPI

from alarm_ment.alarm_ment import router as alarm_router
from recommender.diary_recommender_service import router as recommender_router
from title_ment.title_ment import router as title_router

app = FastAPI(title="SKHUTHON AI 통합 서버")


app.include_router(alarm_router)
app.include_router(recommender_router)
app.include_router(title_router)

@app.get("/")
def read_root():
    return {"status": "healthy", "message": "통합 AI 서버가 정상 구동 중입니다."}