from datetime import datetime, timedelta, timezone
import altair as alt
import pandas as pd
import requests
import streamlit as st

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정 및 다크 시네마 테마(CSS) 적용
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="KOBIS 박스오피스 비교 분석",
    page_icon="🎬",
    layout="wide",
)

# 배경 색상 및 요소별 시네마틱 다크 스타일링
st.markdown(
    """
    <style>
    /* 1. 전체 기본 배경 (깊은 다크 블루/슬레이트) */
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
    }
    
    /* 2. 상단/하단 안내 카드 스타일 */
    .compact-container {
        background-color: #1e293b;
        padding: 12px 16px;
        border-radius: 10px;
        border: 1px solid #334155;
        font-size: 0.85rem;
        color: #cbd5e1;
        margin-bottom: 8px;
    }
    .compact-container h5 {
        font-size: 0.95rem;
        margin-bottom: 4px;
        color: #f8fafc;
    }
    
    /* 3. TOP 1~3 메인 강조 카드 스타일 */
    .top-rank-card {
        background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4);
    }
    .top-1-card { border-top: 4px solid #f59e0b; } /* 🥇 금메달 골드 */
    .top-2-card { border-top: 4px solid #94a3b8; } /* 🥈 은메달 실버 */
    .top-3-card { border-top: 4px solid #d97706; } /* 🥉 동메달 브론즈 */
    
    .movie-title-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #ffffff;
        margin-top: 4px;
        margin-bottom: 8px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    /* 4. Streamlit Metric 지표 글자색 가독성 보장 */
    [data-testid="stMetricValue"] {
        color: #f8fafc !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 2. 한국 시간(KST) 기준 날짜 계산 및 선택기
# -----------------------------------------------------------------------------
kst = timezone(timedelta(hours=9))
today_kst = datetime.now(kst).date()
yesterday_kst = today_kst - timedelta(days=1)

st.title("🎬 일일 박스오피스 비교·분석")

selected_date = st.date_input(
    "📅 조회할 날짜를 선택하세요 (오늘 날짜는 집계 전이므로 어제까지만 선택 가능)",
    value=yesterday_kst,
    max_value=yesterday_kst,
    min_value=datetime(2004, 1, 1).date(),
)

target_date = selected_date.strftime("%Y%m%d")
display_date = selected_date.strftime("%Y년 %m월 %d일")

# -----------------------------------------------------------------------------
# 3. 상단 KOBIS 주요 서비스 안내 (접이식 콤팩트 배치)
# -----------------------------------------------------------------------------
with st.expander("🍿 KOBIS 주요 서비스 바로가기 (클릭하여 열기/접기)", expanded=False):
    card_col1, card_col2 = st.columns(2)

    with card_col1:
        st.markdown(
            """
            <div class="compact-container">
                <h5>📅 박스오피스</h5>
                <p>일별, 주간, 월별, 연도별 매출액 및 관객수 랭킹 정보를 조회합니다.</p>
            </div>
        """,
            unsafe_allow_html=True,
        )
        st.link_button(
            "박스오피스 바로가기 ▶",
            "https://www.kobis.or.kr/kobis/business/stat/boxs/findDailyBoxOfficeList.do",
        )

        st.markdown(
            """
            <div class="compact-container" style="margin-top:10px;">
                <h5>📋 좌석 점유율</h5>
                <p>전국 좌석 점유율을 일별, 주간, 기간별로 세분화하여 제공합니다.</p>
            </div>
        """,
            unsafe_allow_html=True,
        )
        st.link_button(
            "좌석 점유율 바로가기 ▶",
            "https://www.kobis.or.kr/kobis/business/stat/seat/findSeatShareList.do",
        )

    with card_col2:
        st.markdown(
            """
            <div class="compact-container">
                <h5>🎟️ 실시간 예매율</h5>
                <p>상영 2시간 이후의 예매 데이터를 실시간 집계하여 제공합니다.</p>
            </div>
        """,
            unsafe_allow_html=True,
        )
        st.link_button(
            "실시간 예매율 바로가기 ▶",
            "https://www.kobis.or.kr/kobis/business/stat/boxs/findRealTicketList.do",
        )

        st.markdown(
            """
            <div class="compact-container" style="margin-top:10px;">
                <h5>🖥️ 스크린 점유율</h5>
                <p>영화별 스크린수, 스크린 점유율, 상영횟수 통계를 제공합니다.</p>
            </div>
        """,
            unsafe_allow_html=True,
        )
        st.link_button(
            "스크린 점유율 바로가기 ▶",
            "https://www.kobis.or.kr/kobis/business/stat/boxs/findScreenShareList.do",
        )

st.divider()

# -----------------------------------------------------------------------------
# 4. 인증키 확인 및 KOBIS API 호출
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
        st.warning("⚠️ 그날은 아직 집계 전입니다.")
        st.info(
            "선택하신 날짜의 박스오피스 데이터가 아직 등록되지 않았거나 집계 중입니다. 다른 날짜를 선택해 주세요."
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
# 5. 데이터 가공 (수치 변환, 순위 증감 화살표, 100만 관객 트로피)
# -----------------------------------------------------------------------------
df = pd.DataFrame(daily_list)

df["rank"] = df["rank"].astype(int)
df["rankInten"] = df["rankInten"].astype(int)
df["audiCnt"] = df["audiCnt"].astype(int)
df["audiAcc"] = df["audiAcc"].astype(int)
df["scrnCnt"] = df["scrnCnt"].astype(int)


# 순위 증감 화살표 함수
def format_rank_change(val):
    if val > 0:
        return f"🔺 +{val}"
    elif val < 0:
        return f"🔻 {val}"
    else:
        return "-"


df["rank_change"] = df["rankInten"].apply(format_rank_change)


# 100만 이상 관객 트로피(🏆) 표기 함수
def format_movie_title(row):
    title = row["movieNm"]
    if row["audiAcc"] >= 1_000_000:
        return f"🏆 {title}"
    return title


df["display_movieNm"] = df.apply(format_movie_title, axis=1)

# -----------------------------------------------------------------------------
# 6. 메인 1: TOP 1, 2, 3 독립 하이라이트 카드
# -----------------------------------------------------------------------------
st.subheader(f"🔥 {display_date} 박스오피스 TOP 3 영화")

top_3_df = df.head(3)
cols = st.columns(3)

badges = ["🥇 1위", "🥈 2위", "🥉 3위"]
card_classes = ["top-1-card", "top-2-card", "top-3-card"]

for i in range(min(3, len(top_3_df))):
    movie = top_3_df.iloc[i]
    with cols[i]:
        st.markdown(
            f"""
            <div class="top-rank-card {card_classes[i]}">
                <span style="font-size:0.85rem; font-weight:bold; color:#94a3b8;">{badges[i]}</span>
                <div class="movie-title-header">{movie['display_movieNm']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.metric(
            label="일일 관객수",
            value=f"{movie['audiCnt']:,} 명",
            delta=f"순위변동 {movie['rank_change']}",
        )
        st.metric(label="누적 관객수", value=f"{movie['audiAcc']:,} 명")
        st.metric(label="스크린수", value=f"{movie['scrnCnt']:,} 개")

st.divider()

# -----------------------------------------------------------------------------
# 7. 메인 2: 그래프 나란히 배치 (관객수 vs 스크린수 비교)
# -----------------------------------------------------------------------------
st.subheader("📊 TOP 5 영화: 관객수 vs 스크린수 한눈에 비교")

chart_col1, chart_col2 = st.columns(2)
top_5_df = df.head(5).copy()

# 공통 차트 축 설정 (다크 테마용 가독성 폰트 색상)
axis_style = alt.Axis(
    labelAngle=-20,
    labelFontSize=11,
    labelColor="#cbd5e1",
    titleColor="#94a3b8",
)

# 1) 좌측: 일일 관객수 그래프 (오렌지 포인트)
chart_audi = (
    alt.Chart(top_5_df)
    .mark_bar(
        size=22,
        cornerRadiusTopLeft=5,
        cornerRadiusTopRight=5,
        color="#f97316",
    )
    .encode(
        x=alt.X("display_movieNm:N", title="영화명", sort="-y", axis=axis_style),
        y=alt.Y(
            "audiCnt:Q",
            title="일일 관객수 (명)",
            axis=alt.Axis(labelColor="#cbd5e1", titleColor="#94a3b8"),
        ),
        tooltip=[
            alt.Tooltip("rank:Q", title="순위"),
            alt.Tooltip("movieNm:N", title="영화명"),
            alt.Tooltip("audiCnt:Q", title="일일 관객수", format=","),
        ],
    )
    .properties(height=280)
)

# 2) 우측: 스크린수 그래프 (블루 포인트)
chart_scrn = (
    alt.Chart(top_5_df)
    .mark_bar(
        size=22,
        cornerRadiusTopLeft=5,
        cornerRadiusTopRight=5,
        color="#3b82f6",
    )
    .encode(
        x=alt.X("display_movieNm:N", title="영화명", sort="-y", axis=axis_style),
        y=alt.Y(
            "scrnCnt:Q",
            title="스크린수 (개)",
            axis=alt.Axis(labelColor="#cbd5e1", titleColor="#94a3b8"),
        ),
        tooltip=[
            alt.Tooltip("rank:Q", title="순위"),
            alt.Tooltip("movieNm:N", title="영화명"),
            alt.Tooltip("scrnCnt:Q", title="스크린수", format=","),
        ],
    )
    .properties(height=280)
)

with chart_col1:
    st.markdown("##### 🎟️ 일일 관객수 TOP 5")
    st.altair_chart(chart_audi, use_container_width=True)

with chart_col2:
    st.markdown("##### 🖥️ 스크린수 TOP 5")
    st.altair_chart(chart_scrn, use_container_width=True)

st.divider()

# -----------------------------------------------------------------------------
# 8. 메인 3: 전체 순위 목록 표
# -----------------------------------------------------------------------------
st.subheader("📋 전체 박스오피스 순위 목록")

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

table_df["관객수"] = table_df["관객수"].map("{:,}명".format)
table_df["누적관객"] = table_df["누적관객"].map("{:,}명".format)
table_df["스크린수"] = table_df["스크린수"].map("{:,}개".format)

st.dataframe(table_df, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# 9. 하단 서브 안내
# -----------------------------------------------------------------------------
st.markdown(
    """
    <div class="compact-container" style="text-align: center; margin-top: 20px;">
        <small>💡 본 데이터는 영화진흥위원회(KOBIS) 오픈 API를 통해 제공됩니다. (누적 관객 100만 돌파 영화에는 🏆 표시가 부여됩니다.)</small>
    </div>
""",
    unsafe_allow_html=True,
)
