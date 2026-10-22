from datetime import datetime, timedelta, timezone
import pandas as pd
import requests
import streamlit as st

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정 및 날짜 선택 (한국 시간 기준)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="일일 박스오피스 조회",
    page_icon="🎬",
    layout="wide",
)

st.title("🎬 일일 박스오피스 조회")

# 배포 서버 시계와 무관하게 한국 표준시(KST: UTC+9) 기준 날짜를 계산합니다.
kst = timezone(timedelta(hours=9))
today_kst = datetime.now(kst).date()
yesterday_kst = today_kst - timedelta(days=1)

# 달력에서 날짜를 선택할 수 있도록 설정 (최대 선택 가능 날짜: 어제)
selected_date = st.date_input(
    "📅 조회할 날짜를 선택하세요 (오늘 날짜는 집계 전이므로 어제까지만 선택 가능합니다)",
    value=yesterday_kst,
    max_value=yesterday_kst,
    min_value=datetime(2004, 1, 1).date(),  # KOBIS API 연동 시작일 기준
)

# API 요청용 날짜(YYYYMMDD) 및 화면 출력용 날짜 형식 생성
target_date = selected_date.strftime("%Y%m%d")
display_date = selected_date.strftime("%Y년 %m월 %d일")

st.subheader(f"📌 {display_date} 박스오피스")

# -----------------------------------------------------------------------------
# 2. 인증키 확인 및 API 요청
# -----------------------------------------------------------------------------
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

try:
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    # KOBIS API 오류 상자(faultInfo) 예외 처리
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

    box_office_result = data.get("boxOfficeResult", {})
    daily_list = box_office_result.get("dailyBoxOfficeList", [])

    # 선택한 날짜에 영화 목록이 비어 있는 경우 예외 처리
    if not daily_list:
        st.warning("⚠️ 그날은 아직 집계 전입니다.")
        st.info(
            "선택하신 날짜의 박스오피스 데이터가 아직 등록되지 않았거나 집계 중일 수 있습니다. 다른 날짜를 선택해 주세요."
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
# 3. 데이터 가공 (숫자 변환, 순위 증감 화살표, 100만 관객 트로피)
# -----------------------------------------------------------------------------
df = pd.DataFrame(daily_list)

# API 응답값(문자열)을 정수형(int)으로 변환
df["rank"] = df["rank"].astype(int)
df["rankInten"] = df["rankInten"].astype(int)
df["audiCnt"] = df["audiCnt"].astype(int)
df["audiAcc"] = df["audiAcc"].astype(int)
df["scrnCnt"] = df["scrnCnt"].astype(int)

# [기능 추가] 전날 대비 순위 증감(rankInten) 화살표 처리
# 양수: 🔺 (빨간 위 화살표), 음수: 🔻 (파란 아래 화살표), 0: -
def format_rank_inten(val):
    if val > 0:
        return f"🔺 +{val}"
    elif val < 0:
        return f"🔻 {val}"
    else:
        return "-"

df["rank_change"] = df["rankInten"].apply(format_rank_inten)

# [기능 추가] 누적 관객수 100만 명 이상 영화명 옆에 🏆 이모지 붙이기
def format_movie_title(row):
    title = row["movieNm"]
    if row["audiAcc"] >= 1_000_000:
        return f"🏆 {title}"
    return title

df["display_movieNm"] = df.apply(format_movie_title, axis=1)

# -----------------------------------------------------------------------------
# 4. 화면 출력 (1위 지표 카드 / 상위 5개 막대그래프 / 전체 데이터 표)
# -----------------------------------------------------------------------------
# [1] 1위 영화 지표 카드 3장
top_1 = df.iloc[0]
st.subheader(f"🥇 1위 영화: {top_1['display_movieNm']}")

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
top_5_df = df.head(5)[["display_movieNm", "audiCnt"]].set_index("display_movieNm")
top_5_df.columns = ["일일 관객수"]
st.bar_chart(top_5_df)

st.divider()

# [3] 순위·순위 변동·영화명·개봉일·관객수·누적관객·스크린수 표
st.subheader("📋 전체 박스오피스 순위")

table_df = df[
    [
        "rank",
        "rank_change",
        "display_movieNm",
        "openDt",
        "audiCnt",
        "audiAcc",
        "scrnCnt",
    ]
].copy()

table_df.columns = [
    "순위",
    "순위 변동",
    "영화명",
    "개봉일",
    "관객수",
    "누적관객",
    "스크린수",
]

# 천 단위 쉼표 표기 적용
table_df["관객수"] = table_df["관객수"].map("{:,}명".format)
table_df["누적관객"] = table_df["누적관객"].map("{:,}명".format)
table_df["스크린수"] = table_df["스크린수"].map("{:,}개".format)

st.dataframe(table_df, use_container_width=True, hide_index=True)
