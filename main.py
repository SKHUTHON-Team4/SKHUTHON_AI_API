import os
import json
import requests
import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BACKEND_GET_DIARIES_URL = os.getenv("BACKEND_GET_URL")
BACKEND_POST_COMMENTS_URL = os.getenv("BACKEND_POST_URL")

if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY가 없습니다. .env 파일을 확인해 주세요.")

client = genai.Client(api_key=GEMINI_API_KEY)

# ==========================================
# 연령대별 특성 가이드 사전
# ==========================================
AGE_TRAITS = {
    "고등학생": "학업 스트레스, 진로에 대한 고민, 친구 관계, 풋풋한 일상",
    "20대 초반": "대학 생활, 아르바이트, 새로운 만남, 진로 탐색, 자유로움",
    "20대 중반": "취업 준비의 압박, 사회 초년생의 낯섦, 연애, 독립",
    "20대 후반~30대 초반": "직장 생활의 고충, 커리어 발전 고민, 결혼 및 미래에 대한 불안감",
    "30대 중반~": "삶의 안정과 번아웃, 가족/육아, 건강, 인생의 방향성 재점검"
}

def categorize_age(age):
    if age <= 19: return "고등학생"
    elif 20 <= age <= 23: return "20대 초반"
    elif 24 <= age <= 26: return "20대 중반"
    elif 27 <= age <= 33: return "20대 후반~30대 초반"
    else: return "30대 중반~"

def run_daily_ai_analysis():
    print("🚀 일일 AI 맞춤형 분석 및 멘트 매핑 작업을 시작합니다...")
    
    try:
        response = requests.get(BACKEND_GET_DIARIES_URL)
        response.raise_for_status()
        diaries_data = response.json()
    except Exception as e:
        print(f"❌ 데이터 수신 실패: {e}")
        return

    if not diaries_data:
        return

    df = pd.DataFrame(diaries_data)
    if 'is_public' in df.columns:
        df = df[df['is_public'] == True]
        
    df['age_group'] = df['age'].apply(categorize_age)
    
    final_payload = []
    grouped = df.groupby('age_group')
    
    for age_group, group_df in grouped:
        print(f"🧠 [{age_group}] 감정 분류 및 맞춤형 멘트 생성 중...")
        
        diaries_for_prompt = group_df[['id', 'content']].to_dict(orient='records')
        
        # 현재 분석 중인 그룹의 특성을 사전에서 가져오기
        current_group_traits = AGE_TRAITS.get(age_group, "다양한 일상과 고민")
        
        # [3] 프롬프트
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
           - 분량 제한: 2~3문장으로 짧고 다정하게 작성할 것. (예시: "취업 준비로 마음이 많이 무거우셨군요. 좋아하는 음악을 들으며 스스로를 꼭 안아주는 시간을 가져보세요.")
           - 🚨[주의사항]: 메일로 늦게 발송되는 점을 고려하여 멘트 작성 시 '어제', '오늘', '내일', '금일' 등 특정 시점이나 날짜를 지칭하는 단어는 절대 사용하지 말 것.

        반드시 지정된 JSON 형식으로만 응답해 주세요.
        """

        try:
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={
                        "type": "object",
                        "properties": {
                            "classifications": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "integer"},
                                        "sentiment": {"type": "string", "enum": ["positive", "negative"]}
                                    }
                                }
                            },
                            "positive_comment": {"type": "string"},
                            "negative_comment": {"type": "string"}
                        },
                        "required": ["classifications", "positive_comment", "negative_comment"]
                    }
                )
            )
            
            ai_result = json.loads(response.text)
            
            pos_comment = ai_result["positive_comment"]
            neg_comment = ai_result["negative_comment"]
            
            for item in ai_result["classifications"]:
                diary_id = item["id"]
                sentiment = item["sentiment"]
                
                matched_comment = pos_comment if sentiment == "positive" else neg_comment
                
                final_payload.append({
                    "id": diary_id, 
                    "ai_comment": matched_comment
                })
            
        except Exception as e:
            print(f"❌ [{age_group}] AI 분석 중 오류 발생: {e}")
            continue

    if final_payload:
        try:
            post_response = requests.post(
                BACKEND_POST_COMMENTS_URL, 
                json={"recommendations": final_payload}
            )
            post_response.raise_for_status()
            print(f"✅ {len(final_payload)}개의 일기에 맞춤형 AI 추천 멘트 매핑 완료 및 전송 성공!")
        except Exception as e:
            print(f"❌ 백엔드 전송 실패: {e}")

if __name__ == "__main__":
    run_daily_ai_analysis()