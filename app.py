import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as obj
import os
import textwrap

# --- Page Configuration ---
st.set_page_config(page_title="서울시 자치구 데이터 통합 리포트", layout="wide")

# --- CSS for Professional Styling ---
st.markdown("""
    <style>
    .main { background-color: #f9f9f9; }
    .stMarkdown h3 { margin-top: 20px; margin-bottom: 10px; }
    code { font-size: 0.95rem !important; }
    </style>
    """, unsafe_allow_html=True)

DB_PATH = "경정처_과제2.db"

# --- Data Loading Logic ---
def load_data():
    if not os.path.exists(DB_PATH):
        st.error(f"❌ 데이터베이스 파일({DB_PATH})을 찾을 수 없습니다.")
        return None
    
    try:
        conn = sqlite3.connect(DB_PATH)
        
        # 1. Real Estate SQL
        sql_re = textwrap.dedent("""
            SELECT 자치구_명칭, AVG(`물건금액(만원)`) as 평균_거래금액 
            FROM 부동산 
            GROUP BY 자치구_명칭 
            ORDER BY 평균_거래금액 DESC
        """).strip()
        df_re = pd.read_sql(sql_re, conn)

        # 2. Public Transport SQL
        sql_tr = textwrap.dedent("""
            SELECT m.자치구_명칭, SUM(t.승객_수) as 총_승객수
            FROM 대중교통 t
            JOIN 행정동_마스터 m ON t.행정동_ID = m.행정동_ID
            GROUP BY m.자치구_명칭
        """).strip()
        df_tr = pd.read_sql(sql_tr, conn)

        # 3. Bike Stations SQL
        sql_bike = textwrap.dedent("""
            SELECT 자치구_명칭, COUNT(대여소_ID) as 대여소_수 
            FROM 따릉이 
            GROUP BY 자치구_명칭
        """).strip()
        df_bike = pd.read_sql(sql_bike, conn)

        # 4. Heatmap SQL (Grouped into 4 Time Slots + Top 10 Districts)
        # 아침(06-10), 점심(11-16), 저녁(17-21), 심야(22-05)
        sql_heatmap = textwrap.dedent("""
            SELECT 
                m.자치구_명칭,
                (SUM("06시") + SUM("07시") + SUM("08시") + SUM("09시") + SUM("10시")) as 아침,
                (SUM("11시") + SUM("12시") + SUM("13시") + SUM("14시") + SUM("15시") + SUM("16시")) as 점심,
                (SUM("17시") + SUM("18시") + SUM("19시") + SUM("20시") + SUM("21시")) as 저녁,
                (SUM(CAST("22시" AS INTEGER)) + SUM(CAST("23시" AS INTEGER)) + SUM("00시") + SUM("01시") + SUM("02시") + SUM("03시") + SUM("04시") + SUM("05시")) as 심야,
                SUM(t.승객_수) as 총_승객수
            FROM 대중교통 t
            JOIN 행정동_마스터 m ON t.행정동_ID = m.행정동_ID
            GROUP BY m.자치구_명칭
            ORDER BY 총_승객수 DESC
            LIMIT 10
        """).strip()
        df_heatmap = pd.read_sql(sql_heatmap, conn)

        # Basic Data Merging
        df = pd.merge(df_re, df_tr, on="자치구_명칭", how="inner")
        df = pd.merge(df, df_bike, on="자치구_명칭", how="inner")
        
        conn.close()
        return df, sql_re, sql_tr, sql_bike, df_heatmap, sql_heatmap
    except Exception as e:
        st.error(f"데이터 로딩 중 오류 발생: {e}")
        return None

# --- Main UI ---
st.title("🏙️ 서울시 자치구별 통합 데이터 분석 리포트")

result = load_data()

if result:
    df, sql_re, sql_tr, sql_bike, df_heatmap, sql_heatmap = result

    # --- Section 1: Real Estate ---
    st.divider()
    st.subheader("1. 자치구별 평균 부동산 거래금액 (Top 15)")
    col1_1, col1_2 = st.columns([1.5, 1])

    with col1_1:
        df_top15 = df.sort_values("평균_거래금액", ascending=True).tail(15)
        fig1 = px.bar(df_top15, x="평균_거래금액", y="자치구_명칭", orientation='h',
                      color="평균_거래금액", color_continuous_scale="Blues", text_auto=',.0f')
        st.plotly_chart(fig1, use_container_width=True)

    with col1_2:
        st.markdown("### 💾 SQL")
        st.code(sql_re, language='sql')
        
        max_gu = df.loc[df['평균_거래금액'].idxmax()]
        min_gu = df.loc[df['평균_거래금액'].idxmin()]
        diff_val = max_gu['평균_거래금액'] - min_gu['평균_거래금액']
        
        st.markdown("### 💡 분석 인사이트")
        st.markdown(f"""
        - **최상위 지역:** 부동산 평균가가 가장 높은 구는 **{max_gu['자치구_명칭']}**입니다.
        - **최하위 지역:** 반면, 거래가가 가장 낮은 지역은 **{min_gu['자치구_명칭']}**로 분석되었습니다.
        - **가격 양극화:** 두 지역 간의 평균 거래가 차이는 약 **{diff_val:,.0f}만원**에 달합니다.
        - **가독성 참고:** 전체 자치구 중 거래가 순위가 높은 **상위 15개 구**를 시각화하였습니다.
        """)

    # --- Section 2: Transport Correlation ---
    st.divider()
    st.subheader("2. 대중교통 이용량과 부동산 가격의 상관관계")
    col2_1, col2_2 = st.columns([1.5, 1])

    with col2_1:
        fig2 = px.scatter(df, x="총_승객수", y="평균_거래금액", text="자치구_명칭", size="총_승객수", color="총_승객수")
        fig2.update_traces(textposition='top center')
        st.plotly_chart(fig2, use_container_width=True)

    with col2_2:
        st.markdown("### 💾 SQL")
        st.code(sql_tr, language='sql')
        
        df['가성비'] = df['총_승객수'] / df['평균_거래금액']
        best_eff = df.loc[df['가성비'].idxmax()]
        
        st.markdown("### 💡 분석 인사이트")
        st.markdown(f"""
        - **가성비 구 선정:** 교통 유동 인구 대비 부동산 가격이 합리적인 지역은 **{best_eff['자치구_명칭']}**입니다.
        - **데이터 근거:** 해당 구는 총 **{best_eff['총_승객수']:,.0f}명**의 승객 이용량을 보이나, 평균가는 **{best_eff['평균_거래금액']:,.0f}만원** 수준입니다.
        - **전략적 시사점:** 교통 접근성이 우수함에도 가격이 상대적으로 낮은 지역은 향후 주거지로서 높은 가성비를 제공할 가능성이 큽니다.
        """)

    # --- Section 3: Bike Infrastructure ---
    st.divider()
    st.subheader("3. 따릉이 인프라 대비 평균 부동산 가격")
    col3_1, col3_2 = st.columns([1.5, 1])

    with col3_1:
        df_bike_plot = df.sort_values("평균_거래금액", ascending=False)
        fig3 = obj.Figure()
        fig3.add_trace(obj.Bar(x=df_bike_plot['자치구_명칭'], y=df_bike_plot['대여소_수'], name="따릉이 대여소 수", yaxis='y1', marker_color='#A2D9CE'))
        fig3.add_trace(obj.Scatter(x=df_bike_plot['자치구_명칭'], y=df_bike_plot['평균_거래금액'], name="평균 거래가", yaxis='y2', line=dict(color='#FFD700', width=4)))
        fig3.update_layout(height=550, yaxis=dict(title="대여소 개수", showgrid=False), yaxis2=dict(title="가격(만원)", overlaying="y", side="right"), xaxis=dict(tickangle=45))
        st.plotly_chart(fig3, use_container_width=True)

    with col3_2:
        st.markdown("### 💾 SQL")
        st.code(sql_bike, language='sql')
        
        best_bike = df.loc[df['대여소_수'].idxmax()]
        bike_price = best_bike['평균_거래금액']
        
        st.markdown("### 💡 분석 인사이트")
        st.markdown(f"""
        - **인프라 챔피언:** 따릉이 대여소가 가장 많이 설치된 구는 **{best_bike['자치구_명칭']}** ({best_bike['대여소_수']}개)입니다.
        - **인프라-가격 관계:** 이 지역의 평균 부동산 가격은 **{bike_price:,.0f}만원**으로 집계되었습니다.
        - **결론:** 따릉이 인프라 밀집도는 주거지 선정 시 중요한 편의 지표가 되지만, 부동산 가격을 결정하는 독립적인 요인보다는 주거 환경 보조 지표로 해석됩니다.
        """)

    # --- Section 4: Grouped Transport Heatmap (Top 10 Districts) ---
    st.divider()
    st.subheader("4. 주요 자치구별 시간대별 대중교통 이용 히트맵")
    col4_1, col4_2 = st.columns([1.5, 1])
    
    with col4_1:
        # Prepare Matrix Data (Top 10 only)
        df_heatmap_plot = df_heatmap.set_index('자치구_명칭')[['아침', '점심', '저녁', '심야']]
        fig4 = px.imshow(df_heatmap_plot, 
                         labels=dict(x="시간대", y="자치구", color="승객 수"),
                         color_continuous_scale="YlGnBu", aspect="auto", height=550)
        st.plotly_chart(fig4, use_container_width=True)
        
    with col4_2:
        st.markdown("### 💾 SQL")
        st.code(sql_heatmap, language='sql')
        
        # Dynamic Insight for Heatmap
        peak_period = df_heatmap_plot.sum().idxmax()
        night_active_gu = df_heatmap_plot['심야'].idxmax()
        
        st.markdown("### 💡 분석 인사이트")
        st.markdown(f"""
        - **전체 피크 시간:** 분석된 상위 10개 구에서 이용객이 가장 집중되는 구간은 **{peak_period}** 시간대입니다.
        - **심야 활성 지역:** 22시 이후 심야 유동인구가 가장 활발한 곳은 **{night_active_gu}**입니다.
        """)
