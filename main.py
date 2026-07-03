from fastapi import FastAPI
# 하위 폴더 및 파일에서 라우터(router)들을 임포트합니다.
from alarm_ment.alarm_ment import router as alarm_router
from recommender.diary_recommender_service import router as recommender_router
from title_ment.title_ment import router as title_router

# Render가 인식할 메인 오리진 앱을 생성합니다.
app = FastAPI(title="SKHUTHON AI 통합 서버")

# 조립식 라우터들을 메인 앱에 등록(Include)합니다.
app.include_router(alarm_router)
app.include_router(recommender_router)
app.include_router(title_router)

# 서버가 잘 켜졌는지 확인하기 위한 기본 루트 엔드포인트
@app.get("/")
def read_root():
    return {"status": "healthy", "message": "통합 AI 서버가 정상 구동 중입니다."}