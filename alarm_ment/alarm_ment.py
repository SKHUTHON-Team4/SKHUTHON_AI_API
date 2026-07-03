import os
import sys
import json
import time
import requests
from dotenv import load_dotenv
from openai import OpenAI
from fastapi import APIRouter

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

load_dotenv()


GPT_API_KEY = os.getenv("GPT_API_KEY")
BACKEND_GET_DIARIES_URL = os.getenv("BACKEND_GET_URL")
BACKEND_POST_COMMENTS_URL = os.getenv("BACKEND_POST_URL")

if not GPT_API_KEY:
    raise ValueError("❌ GPT_API_KEY가 없습니다. .env 파일을 확인해 주세요.")

client = OpenAI(api_key=GPT_API_KEY)


AGE_TRAITS = {
    "고등학생": "학업 스트레스, 진로에 대한 고민, 친구 관계, 풋풋한 일상",
    "20대 초반": "대학 생활, 아르바이트, 새로운 만남, 진로 탐색, 자유로움",
    "20대 중반": "취업 준비의 압박, 사회 초년생의 낯섦, 연애, 독립",
    "20대 후반~30대 초반": "직장 생활의 고충, 커리어 발전 고민, 결혼 및 미래에 대한 불안감",
    "30대 중반 이상": "삶의 안정과 번아웃, 가족/육아, 건강, 인생의 방향성 재점검"
}

def categorize_age(age):
    """나이를 입력받아 5가지 그룹으로 분류합니다."""
    if age <= 19:
        return "고등학생"
    elif 20 <= age <= 23:
        return "20대 초반"
    elif 24 <= age <= 26:
        return "20대 중반"
    elif 27 <= age <= 33:
        return "20대 후반~30대 초반"
    else:
        return "30대 중반 이상"

def run_daily_ai_analysis():
    print("🚀 일일 AI 맞춤형 분석 및 멘트 매핑 작업을 시작합니다...")
    
    
    try:
        response = requests.get(BACKEND_GET_DIARIES_URL)
        response.raise_for_status()
        
        diaries_data = response.json().get("data", [])
    except Exception as e:
        print(f"❌ 데이터 수신 실패: {e}")
        return

    if not diaries_data:
        print("📭 오늘 분석할 일기 데이터가 없습니다.")
        return

    
    grouped_data = {} 
    
    for diary in diaries_data:
        
        if diary.get('isPublic') == False:
            continue
            
        
        age = diary.get('age')
        
        
        if age is None:
            diary_id = diary.get('id', '알수없음')
            print(f"⚠️ 경고: 일기 ID {diary_id}에 'age' 데이터가 없어 분석에서 제외합니다.")
            continue 
            
        
        age_group = categorize_age(age)
        
        
        if age_group not in grouped_data:
            grouped_data[age_group] = []
            
        grouped_data[age_group].append(diary)

    
    final_payload = []

    
    for age_group, diaries_list in grouped_data.items():
        print(f"🧠 [{age_group}] 감정 분류 및 맞춤형 멘트 생성 중...")
        
        
        print("⏳ OpenAI API 속도 제한 방지를 위해 15초 대기 중...")
        time.sleep(15)
        
        
        diaries_for_prompt = [
            {"id": d.get("id"), "content": d.get("content")} 
            for d in diaries_list 
            if d.get("id") is not None and d.get("content") is not None
        ][:5] 
        
        
        if not diaries_for_prompt:
            continue
            
        
        current_group_traits = AGE_TRAITS.get(age_group, "다양한 일상과 고민")
        
        
        prompt = f"""
        당신은 따뜻하고 공감 능력이 뛰어난 다이어리 앱의 AI 멘토입니다.
        아래는 '{age_group}' 사용자들이 작성한 일기(ID와 내용) 모음입니다.

        [연령대별 특성 가이드: {age_group}]
        - 핵심 키워드: {current_group_traits}

        [일기 데이터]
        {json.dumps(diaries_for_prompt, ensure_ascii=False)}

        다음 두 가지 작업을 수행해 주세요:
        1. 감정 판별: 각 일기(id)의 텍스트에서 추출한 감정을 'positive'(긍정) 또는 'negative'(부정) 두 케이스 중 하나로만 판별하세요.
        2. 추천 멘트 작성: 위에서 제시한 '{age_group}'의 특성과 일기 내용들의 전반적인 분위기를 자연스럽게 연결하여, 이 그룹 전체를 아우르는 추천 멘트를 작성하세요.
           - positive_comment: 일기에서 느껴지는 활기찬 에너지나 성취감을 더욱 북돋아 주고, 연령대에 맞게 진심으로 응원하고 칭찬하는 멘트.
           - negative_comment: 현재 연령대에서 겪을 수 있는 힘듦과 고민을 다독이고, 따뜻한 위로와 가벼운 휴식을 제안하는 멘트.
           - 분량 제한: 2~3문장으로 짧고 다정하게 작성할 것.
           - 🚨[주의사항]: 메일로 늦게 발송되는 점을 고려하여 멘트 작성 시 '어제', '오늘', '내일', '금일' 등 특정 시점이나 날짜를 지칭하는 단어는 절대 사용하지 말 것.

        반드시 지정된 JSON 형식으로만 응답해 주세요.
        """

        try:
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "diary_analysis",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "classifications": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "sentiment": {"type": "string", "enum": ["positive", "negative"]}
                                        },
                                        "required": ["id", "sentiment"],
                                        "additionalProperties": False
                                    }
                                },
                                "positive_comment": {"type": "string"},
                                "negative_comment": {"type": "string"}
                            },
                            "required": ["classifications", "positive_comment", "negative_comment"],
                            "additionalProperties": False
                        }
                    }
                }
            )

            
            ai_result = json.loads(response.choices[0].message.content)
            pos_comment = ai_result["positive_comment"]
            neg_comment = ai_result["negative_comment"]
            
            
            for item in ai_result["classifications"]:
                diary_id = item["id"]
                sentiment = item["sentiment"]
                
                
                matched_comment = pos_comment if sentiment == "positive" else neg_comment
                
                
                final_payload.append({
                    "id": diary_id, 
                    "aiComment": matched_comment
                })
            
        except Exception as e:
            print(f"❌ [{age_group}] AI 분석 중 오류 발생: {e}")
            continue

    
    success_count = 0
    for item in final_payload:
        diary_id = item["id"]
        post_url = BACKEND_POST_COMMENTS_URL.replace("{diaryId}", str(diary_id))
        try:
            post_response = requests.patch(post_url, json={"aiComment": item["aiComment"]})
            post_response.raise_for_status()
            success_count += 1
        except Exception as e:
            print(f"❌ 일기 ID {diary_id} 백엔드 전송 실패: {e}")

    if final_payload:
        print(f"✅ 총 {success_count}/{len(final_payload)}개의 일기에 맞춤형 AI 추천 멘트 매핑 완료 및 백엔드 전송 성공!")


router = APIRouter(prefix="/alarm", tags=["Alarm"])


@router.get("/")
def health_check():
    return {"message": "AI Server is running perfectly!"}

@router.get("/run-ai")
def trigger_ai_analysis():
    run_daily_ai_analysis()
    return {"message": "AI analysis triggered and completed."}