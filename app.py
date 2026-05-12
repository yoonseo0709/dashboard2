import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as obj
import os

# --- Page Configuration ---
st.set_page_config(page_title="서울시 자치구별 부동산-인프라 분석", layout="wide")

# --- CSS for Professional Look ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

DB_PATH = "경정처_과제2.db"

# --- DB Connection & Data Loading ---
def load_data():
    if not os.path.exists(DB_PATH):
        st.error(f"❌ DB 파일을 찾을 수 없습니다: {DB_PATH}. 파일 경로를 확인해주세요.")
        return None

    try:
        conn = sqlite3.connect(DB_PATH)
        
        # 1. Real Estate Data (부동산)
        query_re = "SELECT 자치구_명칭, AVG(`물건금액(만원)`) as 평균_거래금액 FROM 부동산 GROUP BY 자치구_명칭"
        df_re = pd.read_sql(query_re, conn)

        # 2. Public Transport (대중교통 + 행정동_마스터 Join)
        query_tr = """
        SELECT m.자치구_명칭, SUM(t.승객_수) as 총_승객수
        FROM 대중교통 t
        JOIN 행정동_마스터 m ON t.행정동_ID = m.행정동_ID
        GROUP BY m.자치구_명칭
        """
        df_tr = pd.read_sql(query_tr, conn)

        # 3. Bike Stations (따릉이)
        query_bike = "SELECT 자치구_명칭, COUNT(대여소_ID) as 대여소_수 FROM 따릉이 GROUP BY 자치구_명칭"
        df_bike = pd.read_sql(query_bike, conn)

        # Merge all data on '자치구_명칭'
        df_final = pd.merge(df_re, df_tr, on="자치구_명칭", how="inner")
        df_final = pd.merge(df_final, df_bike, on="자치구_명칭", how="inner")
        
        conn.close()
        return df_final
    except Exception as e:
        st.error(f"데이터 로딩 중 오류 발생: {e}")
        return None

# --- Main App Execution ---
st.title("📊 서울시 자치구별 데이터 통합 분석 인사이트")
st.markdown("부동산 가격과 교통/인프라 데이터를 결합한 전문 분석 대시보드입니다.")

df = load_data()

if df is not None:
    # --- Chart 1: Average Real Estate Price ---
    st.divider()
    st.header("1. 자치구별 평균 부동산 거래금액")
    
    col1_1, col1_2 = st.columns([2, 1])
    
    with col1_1:
        # Sort and visualize
        df_sorted_re = df.sort_values("평균_거래금액", ascending=True)
        fig1 = px.bar(df_sorted_re, x="평균_거래금액", y="자치구_명칭", orientation='h',
                      title="자치구별 평균 부동산 거래금액 (만원)",
                      color="평균_거래금액", color_continuous_scale="Viridis")
        st.plotly_chart(fig1, use_container_width=True)
        
    with col1_2:
        st.subheader("📝 SQL Query")
        st.code("SELECT 자치구_명칭, AVG(`물건금액(만원)`) FROM 부동산 GROUP BY 자치구_명칭", language='sql')
        
        # Dynamic Insight Logic
        max_gu = df.loc[df['평균_거래금액'].idxmax()]
        min_gu = df.loc[df['평균_거래금액'].idxmin()]
        diff = max_gu['평균_거래금액'] - min_gu['평균_거래금액']
        
        st.subheader("💡 분석 인사이트")
        st.info(f"""
        분석 결과, 서울시에서 평균 부동산 거래가가 가장 높은 지역은 **{max_gu['자치구_명칭']}** (약 {max_gu['평균_거래금액']:,.0f}만원)이며, 
        가장 낮은 지역은 **{min_gu['자치구_명칭']}** (약 {min_gu['평균_거래금액']:,.0f}만원)입니다. 
        두 지역의 평균 거래가 차이는 **{diff:,.0f}만원**에 달하는 것으로 나타났습니다.
        """)

    # --- Chart 2: Correlation (Transport vs Price) ---
    st.divider()
    st.header("2. 대중교통 이용량과 부동산 가격의 상관관계")
    
    col2_1, col2_2 = st.columns([2, 1])
    
    with col2_1:
        fig2 = px.scatter(df, x="총_승객수", y="평균_거래금액", text="자치구_명칭",
                          size="평균_거래금액", color="총_승객수",
                          title="대중교통 이용량 대비 부동산 가격 산점도",
                          labels={"총_승객수": "총 승객 수", "평균_거래금액": "평균 거래금액(만원)"})
        fig2.update_traces(textposition='top center')
        st.plotly_chart(fig2, use_container_width=True)
        
    with col2_2:
        st.subheader("📝 SQL Query")
        st.code("""
SELECT m.자치구_명칭, SUM(t.승객_수) 
FROM 대중교통 t
JOIN 행정동_마스터 m ON t.행정동_ID = m.행정동_ID
GROUP BY m.자치구_명칭
        """, language='sql')
        
        # Dynamic Insight Logic: Cost-effectiveness (High Transport, Low Price)
        # Ratio of transport to price
        df['가성비_지표'] = df['총_승객수'] / df['평균_거래금액']
        efficient_gu = df.loc[df['가성비_지표'].idxmax()]
        
        st.subheader("💡 분석 인사이트")
        st.warning(f"""
        대중교통 이용량 대비 부동산 가격을 분석한 결과, **{efficient_gu['자치구_명칭']}** 지역이 
        가장 효율적인 '가성비 자치구'로 확인되었습니다. 
        해당 구는 유동 인구(승객 수: {efficient_gu['총_승객수']:,.0f}명)가 매우 활발함에도 불구하고, 
        평균 거래가는 {efficient_gu['평균_거래금액']:,.0f}만원으로 상대적으로 저평가되어 있어 주거 및 투자 매력도가 높을 것으로 판단됩니다.
        """)

    # --- Chart 3: Bike Infrastructure vs Price ---
    st.divider()
    st.header("3. 따릉이 인프라와 부동산 가격 비교")
    
    col3_1, col3_2 = st.columns([2, 1])
    
    with col3_1:
        # Mixed Chart
        fig3 = obj.Figure()
        fig3.add_trace(obj.Bar(x=df['자치구_명칭'], y=df['대여소_수'], name="따릉이 대여소 수", yaxis='y1', marker_color='skyblue'))
        fig3.add_trace(obj.Scatter(x=df['자치구_명칭'], y=df['평균_거래금액'], name="평균 부동산 가격", yaxis='y2', line=dict(color='red', width=3)))
        
        fig3.update_layout(
            title="자치구별 따릉이 인프라 vs 부동산 가격 (혼합)",
            yaxis=dict(title="따릉이 대여소 개수", side="left"),
            yaxis2=dict(title="평균 거래금액 (만원)", side="right", overlaying="y", showgrid=False),
            legend=dict(x=0.01, y=0.99)
        )
        st.plotly_chart(fig3, use_container_width=True)
        
    with col3_2:
        st.subheader("📝 SQL Query")
        st.code("SELECT 자치구_명칭, COUNT(대여소_ID) FROM 따릉이 GROUP BY 자치구_명칭", language='sql')
        
        # Dynamic Insight Logic
        best_bike_gu = df.loc[df['대여소_수'].idxmax()]
        rank_price = df['평균_거래금액'].rank(ascending=False).loc[df['대여소_수'].idxmax()]
        
        st.subheader("💡 분석 인사이트")
        st.success(f"""
        따릉이 인프라가 가장 우수한 자치구는 **{best_bike_gu['자치구_명칭']}** (대여소 {best_bike_gu['대여소_수']}개)입니다. 
        이 지역의 부동산 가격은 서울 내 전체 {len(df)}개 구 중 **{int(rank_price)}위** 수준을 기록하고 있습니다. 
        따릉이 인프라와 부동산 가격 사이의 시각적 패턴을 볼 때, 인프라가 많다고 무조건 가격이 높지는 않으나 주거 편의성 측면에서 긍정적인 지표로 작용하고 있습니다.
        """)