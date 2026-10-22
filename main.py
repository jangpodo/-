from datetime import datetime, timedelta, timezone
import altair as alt
import pandas as pd
import requests
import streamlit as st

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정 및 한국 시간 기준 어제 날짜 계산
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="KOBIS 영화 정보 & 일일 박스오피스",
    page_icon="🎬",
    layout="wide",
)

# 배포 서버 시계와 무관하게 한국 표준시(KST: UTC+9)를 기준으로 어제 날짜를 계산합니다.
kst = timezone(timedelta(hours=9))
yesterday_dt = datetime.now(kst) - timedelta(days=1)

target_date = yesterday_dt.strftime("%Y%m%d")
display_date = yesterday_dt.strftime("%Y년 %m월 %d일")

st.title("🎬 KOBIS 영화 정보 & 일일 박스오피스")

# -----------------------------------------------------------------------------
# 2. 이미지 스타일의 KOBIS 주요 서비스 카드 섹션 (2x2 그리드)
# -----------------------------------------------------------------------------
st.markdown("### 🍿 KOBIS 주요 서비스 바로가기")

card_col1, card_col2 = st.columns(2)

with card_col1:
    with st.container(border=True):
        st.markdown("#### 📅 박스오피스")
        st.caption(
            "일별, 주간/주말, 월별, 연도별, 역대, 기간별 조건으로 집계된 각 영화에 대한 매출액과 누적 관객수 등의 박스오피스 랭킹 정보를 조회할 수 있습니다."
        )
        st.link_button(
            "자세히보기 (새 창) ▶",
            "https://www.kobis.or.kr/kobis/business/stat/boxs/findDailyBoxOfficeList.do",
        )

    with st.container(border=True):
        st.markdown("#### 📋 좌석 점유율")
        st.caption(
            "해당 조회기간의 전국 좌석 점유율을 일별, 주간/주말, 기간별로 세분하여 제공합니다."
        )
        st.link_button(
            "자세히보기 (새 창) ▶",
            "https://www.kobis.or.kr/kobis/business/stat/seat/findSeatShareList.do",
        )

with card_col2:
    with st.container(border=True):
        st.markdown("#### 🎟️ 실시간 예매율")
        st.caption(
            "조회시간을 기준으로 상영 2시간 이후의 예매데이터를 실시간으로 집계한 국내 영화 예매율을 제공합니다."
        )
        st.link_button(
            "자세히보기 (새 창) ▶",
            "https://www.kobis.or.kr/kobis/business/stat/boxs/findRealTicketList.do",
        )

    with st.container(border=True):
        st.markdown("#### 🖥️ 스크린 점유율")
        st.caption(
            "각 영화별로 상영된 스크린수, 스크린 점유율, 상영횟수, 매출액 등을 일별, 주간/주말, 기간별로 제공합니다."
        )
        st.link_button(
            "자세히보기 (새 창) ▶",
            "https://www.kobis.or.kr/kobis/business/stat/boxs/findScreenShareList.do",
        )

st.divider()

# -----------------------------------------------------------------------------
# 3. 인증키 확인 및 API 요청
# -----------------------------------------------------------------------------
st.subheader(f"📌 어제({display_date})의 박스오피스 현황")

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
# 4. 데이터 가공 및 숫자로 타입 변환
# -----------------------------------------------------------------------------
df = pd.DataFrame(daily_list)
df["rank"] = df["rank"].astype(int)
df["audiCnt"] = df["audiCnt"].astype(int)
df["audiAcc"] = df["audiAcc"].astype(int)
df["scrnCnt"] = df["scrnCnt"].astype(int)

# -----------------------------------------------------------------------------
# 5. 화면 출력 (1위 지표 카드 / 디자인 개선된 막대그래프 / 전체 표)
# -----------------------------------------------------------------------------
# [1] 1위 영화 지표 카드 3장
top_1 = df.iloc[0]
st.markdown(f"#### 🥇 1위 영화: **{top_1['movieNm']}**")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="일일 관객수", value=f"{top_1['audiCnt']:,} 명")
with col2:
    st.metric(label="누적 관객수", value=f"{top_1['audiAcc']:,} 명")
with col3:
    st.metric(label="스크린수", value=f"{top_1['scrnCnt']:,} 개")

st.divider()

# [2] 관객수 상위 5편 막대그래프 (Altair를 사용한 슬림 및 모던 디자인)
st.subheader("📊 관객수 상위 5개 영화 순위")

top_5_df = df.head(5).copy()

# 슬림한 두께(size=28), 상단 둥근 모서리(cornerRadius), 세련된 주황색 컬러 테마 적용
chart = (
    alt.Chart(top_5_df)
    .mark_bar(
        size=28,
        cornerRadiusTopLeft=6,
        cornerRadiusTopRight=6,
        color="#F37021",  # KOBIS 포인트 컬러 (주황색)
    )
    .encode(
        x=alt.X(
            "movieNm:N",
            title="영화명",
            sort="-y",
            axis=alt.Axis(labelAngle=0, labelFontSize=12),
        ),
        y=alt.Y("audiCnt:Q", title="일일 관객수 (명)"),
        tooltip=[
            alt.Tooltip("movieNm:N", title="영화명"),
            alt.Tooltip("audiCnt:Q", title="일일 관객수", format=","),
            alt.Tooltip("audiAcc:Q", title="누적 관객수", format=","),
        ],
    )
    .properties(height=320)
)

st.altair_chart(chart, use_container_width=True)

st.divider()

# [3] 전체 박스오피스 데이터 표
st.subheader("📋 전체 박스오피스 순위")

table_df = df[
    ["rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]
].copy()
table_df.columns = ["순위", "영화명", "개봉일", "관객수", "누적관객", "스크린수"]

table_df["관객수"] = table_df["관객수"].map("{:,}명".format)
table_df["누적관객"] = table_df["누적관객"].map("{:,}명".format)
table_df["스크린수"] = table_df["스크린수"].map("{:,}개".format)

st.dataframe(table_df, use_container_width=True, hide_index=True)
