from datetime import datetime, timedelta, timezone
import re
import altair as alt
import pandas as pd
import requests
import streamlit as st

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정 및 커스텀 CSS (메인 영역 강조 & 상/하단 축소 스타일)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="KOBIS 박스오피스 비교 분석",
    page_icon="🎬",
    layout="wide",
)

# 커스텀 CSS: 스크롤 시 메인 콘텐츠(1~3위 비교, 그래프, 표)에 시선이 집중되도록
# 상단 서비스 및 하단 정보를 콤팩트 사이즈로 축소 디자인합니다.
st.markdown(
    """
    <style>
    /* [상/하단 서브 영역] 콤팩트 미니 사이즈 스타일 */
    .sub-compact-box {
        background-color: #f8f9fa;
        padding: 8px 12px;
        border-radius: 8px;
        border: 1px solid #e9ecef;
        font-size: 0.8rem;
        color: #6c757d;
        margin-bottom: 8px;
    }
    .sub-compact-box h5 {
        font-size: 0.9rem;
        margin-bottom: 3px;
        color: #343a40;
    }
    .sub-compact-box p {
        font-size: 0.78rem;
        line-height: 1.25;
        margin-bottom: 4px;
    }
    
    /* [메인 영역 - TOP 1~3위] 강조 카드 및 메달 타이틀 스타일 */
    .top-rank-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border: 2px solid #e2e8f0;
        border-radius: 12px;
        padding: 12px 16px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.05);
        margin-bottom: 12px;
        text-align: center;
    }
    .top-1-card { border-top: 5px solid #FFD700; } /* 1위 금메달 컬러 */
    .top-2-card { border-top: 5px solid #C0C0C0; } /* 2위 은메달 컬러 */
    .top-3-card { border-top: 5px solid #CD7F32; } /* 3위 동메달 컬러 */
    
    .movie-title-header {
        font-size: 1.15rem;
        font-weight: 800;
        margin-top: 4px;
        color: #1a202c;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    </style>
""",
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# 2. 영화 포스터 검색 함수 (KMDB API 또는 웹 검색 스크래핑)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=86400)
def get_movie_poster(movie_name):
    """영화 제목을 기반으로 포스터 이미지 URL을 검색하여 가져옵니다."""
    # 1. Streamlit Secrets에 KMDB 키가 등록되어 있는 경우 우선 사용
    kmdb_key = st.secrets.get("KMDB_KEY", "")
    if kmdb_key:
        try:
            url = f"http://api.koreafilm.or.kr/openapi-data2/wserv/searchService1.jsp?collection=kmdb&ServiceKey={kmdb_key}&title={movie_name}"
            res = requests.get(url, timeout=3).json()
            posters = res["Data"][0]["Result"][0]["posters"]
            if posters:
                return posters.split("|")[0]
        except Exception:
            pass

    # 2. 다음(Daum) 검색 결과에서 포스터 이미지 스크래핑
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        search_url = f"https://search.daum.net/search?w=tot&q=영화%20{movie_name}%20포스터"
        res = requests.get(search_url, headers=headers, timeout=3)
        match = re.search(
            r'https?://[^\s"\']*?\.(?:jpg|png|jpeg)', res.text, re.IGNORECASE
        )
        if match:
            return match.group(0)
    except Exception:
        pass

    # 3. 검색 실패 시 기본 이미지 대치
    return "https://via.placeholder.com/300x420.png?text=Poster+Not+Found"


# -----------------------------------------------------------------------------
# 3. 한국 시간(KST) 기준 날짜 계산 및 날짜 선택기
# -----------------------------------------------------------------------------
kst = timezone(timedelta(hours=9))
today_kst = datetime.now(kst).date()
yesterday_kst = today_kst - timedelta(days=1)

st.title("🎬 일일 박스오피스 비교·분석")

# 날짜 선택 (최대 선택 가능 날짜: 어제)
selected_date = st.date_input(
    "📅 조회할 날짜를 선택하세요 (오늘 날짜는 집계 전이므로 어제까지만 선택 가능)",
    value=yesterday_kst,
    max_value=yesterday_kst,
    min_value=datetime(2004, 1, 1).date(),
)

target_date = selected_date.strftime("%Y%m%d")
display_date = selected_date.strftime("%Y년 %m월 %d일")

# -----------------------------------------------------------------------------
# 4. 상단 KOBIS 주요 서비스 (스크롤 시 본문에 집중되도록 콤팩트 접기 배치)
# -----------------------------------------------------------------------------
with st.expander("🍿 KOBIS 주요 서비스 바로가기 (클릭하여 열기/접기)", expanded=False):
    card_col1, card_col2 = st.columns(2)

    with card_col1:
        st.markdown(
            """
            <div class="sub-compact-box">
                <h5>📅 박스오피스</h5>
                <p>일별, 주간, 월별, 연도별 매출액 및 누적 관객수 랭킹 정보를 제공합니다.</p>
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
            <div class="sub-compact-box" style="margin-top:8px;">
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
            <div class="sub-compact-box">
                <h5>🎟️ 실시간 예매율</h5>
                <p>상영 2시간 이후의 예매 데이터를 실시간으로 집계한 예매율을 제공합니다.</p>
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
            <div class="sub-compact-box" style="margin-top:8px;">
                <h5>🖥️ 스크린 점유율</h5>
                <p>영화별 스크린수, 스크린 점유율, 상영횟수 등의 통계를 제공합니다.</p>
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
# 5. KOBIS API 데이터 호출 및 예외 처리
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
# 6. 데이터 가공 (수치 변환, 순위 증감 화살표, 100만 관객 트로피)
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


# 100만 관객 돌파 🏆 표기 함수
def format_movie_title(row):
    title = row["movieNm"]
    if row["audiAcc"] >= 1_000_000:
        return f"🏆 {title}"
    return title


df["display_movieNm"] = df.apply(format_movie_title, axis=1)

# -----------------------------------------------------------------------------
# 7. 메인 강조 영역: TOP 1, 2, 3위 독립 제목 + 포스터 나란히 비교
# -----------------------------------------------------------------------------
st.subheader(f"🔥 {display_date} 박스오피스 TOP 3 포스터 및 비교 분석")

top_3_df = df.head(3)
cols = st.columns(3)

badges = ["🥇 1위", "🥈 2위", "🥉 3위"]
card_classes = ["top-1-card", "top-2-card", "top-3-card"]

for i in range(min(3, len(top_3_df))):
    movie = top_3_df.iloc[i]
    with cols[i]:
        # [독립 제목 돋보임 헤더]
        st.markdown(
            f"""
            <div class="top-rank-card {card_classes[i]}">
                <span style="font-size:0.9rem; font-weight:bold; color:#4a5568;">{badges[i]}</span>
                <div class="movie-title-header">{movie['display_movieNm']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # [영화 포스터 이미지 출력]
        poster_url = get_movie_poster(movie["movieNm"])
        st.image(
            poster_url,
            use_column_width=True,
            caption=f"{movie['movieNm']} 포스터",
        )

        # [나란히 비교하기 편한 핵심 지표 카드]
        st.metric(
            label="일일 관객수",
            value=f"{movie['audiCnt']:,} 명",
            delta=f"순위변동 {movie['rank_change']}",
        )
        st.metric(label="누적 관객수", value=f"{movie['audiAcc']:,} 명")
        st.metric(label="스크린수", value=f"{movie['scrnCnt']:,} 개")

st.divider()

# -----------------------------------------------------------------------------
# 8. 메인 콘텐츠: 상위 영화 슬림 막대그래프 시각화
# -----------------------------------------------------------------------------
st.subheader("📊 관객수 vs 스크린수 상위 영화 비교")

chart_metric = st.radio(
    "비교할 지표 선택:",
    ["일일 관객수 (명)", "스크린수 (개)"],
    horizontal=True,
)

top_5_df = df.head(5).copy()

if chart_metric == "일일 관객수 (명)":
    y_col = "audiCnt"
    y_title = "일일 관객수 (명)"
    bar_color = "#E53E3E"
else:
    y_col = "scrnCnt"
    y_title = "스크린수 (개)"
    bar_color = "#3182CE"

# Altair 기반 슬림 막대그래프 (두께 size=26, 둥근 모서리)
chart = (
    alt.Chart(top_5_df)
    .mark_bar(
        size=26,
        cornerRadiusTopLeft=6,
        cornerRadiusTopRight=6,
        color=bar_color,
    )
    .encode(
        x=alt.X(
            "display_movieNm:N",
            title="영화명",
            sort="-y",
            axis=alt.Axis(labelAngle=0, labelFontSize=11),
        ),
        y=alt.Y(f"{y_col}:Q", title=y_title),
        tooltip=[
            alt.Tooltip("rank:Q", title="순위"),
            alt.Tooltip("movieNm:N", title="영화명"),
            alt.Tooltip("audiCnt:Q", title="일일 관객수", format=","),
            alt.Tooltip("audiAcc:Q", title="누적 관객수", format=","),
            alt.Tooltip("scrnCnt:Q", title="스크린수", format=","),
        ],
    )
    .properties(height=280)
)

st.altair_chart(chart, use_container_width=True)

st.divider()

# -----------------------------------------------------------------------------
# 9. 메인 콘텐츠: 전체 순위 표
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
# 10. 하단 서브 안내 (콤팩트 미니 사이즈)
# -----------------------------------------------------------------------------
st.markdown(
    """
    <div class="sub-compact-box" style="text-align: center; margin-top: 25px;">
        <small>💡 본 데이터는 영화진흥위원회(KOBIS) API를 통해 조회됩니다. (100만 관객 돌파 영화에는 🏆 표기가 부여됩니다.)</small>
    </div>
""",
    unsafe_allow_html=True,
)
