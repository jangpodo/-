from datetime import datetime, timedelta, timezone
import pandas as pd
import requests
import streamlit as st

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정 및 한국 시간 기준 어제 날짜 계산
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="어제 일자 박스오피스",
    page_icon="🎬",
    layout="wide",
)

# 배포 서버 시계와 무관하게 한국 표준시(KST: UTC+9)를 기준으로 어제 날짜를 계산합니다.
kst = timezone(timedelta(hours=9))
yesterday_dt = datetime.now(kst) - timedelta(days=1)

# API 요청에 쓰일 날짜 형식 (YYYYMMDD) 및 화면 표시용 날짜 형식
target_date = yesterday_dt.strftime("%Y%m%d")
display_date = yesterday_dt.strftime("%Y년 %m월 %d일")

st.title(f"🎬 어제({display_date})의 박스오피스")

# -----------------------------------------------------------------------------
# 2. 인증키 확인 및 API 요청
# -----------------------------------------------------------------------------
# Streamlit Secrets에서 인증키 존재 여부를 확인합니다.
if "KOBIS_KEY" not in st.secrets:
    st.error("🔑 인증키(KOBIS_KEY)가 설정되지 않았습니다.")
    st.info(
        "**[확인 방법]**\n"
        "Streamlit Cloud의 **Secrets** 설정에 아래와 같이 인증키를 추가해 주세요.\n\n"
        "```toml\n"
        'KOBIS_KEY = "발급받은_인증키_문자열"\n'
        "```"
    )
    st.stop()

api_key = st.secrets["KOBIS_KEY"]
url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
params = {"key": api_key, "targetDt": target_date}

# KOBIS API 호출 및 예외 처리
try:
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    # KOBIS API는 인증키 오류 시에도 HTTP Status 200을 반환하고 'faultInfo' 객체를 포함합니다.
    if "faultInfo" in data:
        fault_msg = data["faultInfo"].get("message", "알 수 없는 오류")
        st.error("⚠️ 영화진흥위원회 API 응답 오류가 발생했습니다.")
        st.warning(f"오류 메시지: {fault_msg}")
        st.info(
            "**[확인 필요 사항]**\n"
            "1. Streamlit Secrets에 입력한 `KOBIS_KEY` 값이 정확한지 확인하세요.\n"
            "2. 영화진흥위원회 오픈API 마이페이지에서 인증키 상태를 확인하세요."
        )
        st.stop()

    # 응답 구조에서 영화 목록 데이터 추출
    box_office_result = data.get("boxOfficeResult", {})
    daily_list = box_office_result.get("dailyBoxOfficeList", [])

    # 영화 목록이 비어 있는 경우 처리
    if not daily_list:
        st.warning("⚠️ 어제 일자의 박스오피스 데이터가 비어 있습니다.")
        st.info(
            "**[확인 필요 사항]**\n"
            "1. 영화진흥위원회의 일일 박스오피스 집계가 아직 완료되지 않았을 수 있습니다.\n"
            "2. 잠시 후 다시 접속하거나 공식 홈페이지의 서버 상태를 확인해 주세요."
        )
        st.stop()

except requests.exceptions.RequestException as e:
    st.error("📡 네트워크 통신 중 오류가 발생했습니다.")
    st.warning(f"상세 오류: {e}")
    st.info(
        "**[확인 필요 사항]**\n"
        "1. 인터넷 연결 상태를 확인하세요.\n"
        "2. 영화진흥위원회 API 서버(www.kobis.or.kr)가 정상 동작 중인지 확인하세요."
    )
    st.stop()

# -----------------------------------------------------------------------------
# 3. 데이터 가공 (문자열 -> 숫자 변환)
# -----------------------------------------------------------------------------
df = pd.DataFrame(daily_list)

# KOBIS API 응답 값은 모두 문자열이므로 계산 및 정렬을 위해 숫자로 변환합니다.
df["rank"] = df["rank"].astype(int)
df["audiCnt"] = df["audiCnt"].astype(int)
df["audiAcc"] = df["audiAcc"].astype(int)
df["scrnCnt"] = df["scrnCnt"].astype(int)

# -----------------------------------------------------------------------------
# 4. 화면 출력 (1위 지표 카드 / 상위 5개 막대그래프 / 전체 데이터 표)
# -----------------------------------------------------------------------------
# [1] 1위 영화 지표 카드 3장
top_1 = df.iloc[0]
st.subheader(f"🥇 1위 영화: {top_1['movieNm']}")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="일일 관객수", value=f"{top_1['audiCnt']:,} 명")
with col2:
    st.metric(label="누적 관객수", value=f"{top_1['audiAcc']:,} 명")
with col3:
    st.metric(label="스크린수", value=f"{top_1['scrnCnt']:,} 개")

st.divider()

# [2] 관객수 상위 5편 막대그래프
st.subheader("📊 관객수 상위 5개 영화")
top_5_df = df.head(5)[["movieNm", "audiCnt"]].set_index("movieNm")
top_5_df.columns = ["일일 관객수"]
st.bar_chart(top_5_df)

st.divider()

# [3] 순위·영화명·개봉일·관객수·누적관객·스크린수 표
st.subheader("📋 전체 박스오피스 순위")

# 원하는 컬럼 선택 및 한글 컬럼명 변경
table_df = df[
    ["rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]
].copy()
table_df.columns = ["순위", "영화명", "개봉일", "관객수", "누적관객", "스크린수"]

# 천 단위 쉼표 표기 적용
table_df["관객수"] = table_df["관객수"].map("{:,}명".format)
table_df["누적관객"] = table_df["누적관객"].map("{:,}명".format)
table_df["스크린수"] = table_df["스크린수"].map("{:,}개".format)

st.dataframe(table_df, use_container_width=True, hide_index=True)
