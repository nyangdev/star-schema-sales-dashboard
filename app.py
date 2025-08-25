import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import date

st.set_page_config(page_title="Star Schema Sales Dashboard", layout="wide")
st.title("Star Schema 매출 대시보드")

st.caption("스키마: dim_date, dim_customer, dim_product, fact_sales")

# db 설정 불러오기
def get_db_config():
    cfg = st.secrets.get("mariadb", None) # mariadb 설정 찾고 없으면 None값 반환

    if cfg is None:
        st.warning("streamlit 비밀 설정 파일이 입력되지 않았습니다. 프로그램이 종료됩니다.")
        st.stop()

    return dict(
        host = cfg.get("host"),
        port = int(cfg.get("port")),
        db = cfg.get("database"),
        user = cfg.get("user"),
        password = cfg.get("password"),
        charset = cfg.get("charset")
    )

# db 연결
@st.cache_resource
def get_engine():
    cfg = get_db_config()
    url = (
        f"mysql+pymysql://{cfg['user']}:{cfg['password']}"
        f"@{cfg['host']}:{cfg['port']}/{cfg['db']}?charset={cfg['charset']}"
    )

    return create_engine(url, pool_pre_ping=True)

engine = get_engine()

# datetime 변환
def to_date_safe(v):
    if v is None:
        return None
    
    try:
        return pd.to_datetime(v).date()
    except Exception:
        return None
    
def make_in_clause(values, prefix, params):
    placeholders = []

    for i, val in enumerate(values):
        key = f"{prefix}{i}"
        placeholders.append(f":{key}")
        params[key] = val

    return ",".join(placeholders)

# dimension 에서 데이터 로드
@st.cache_data(ttl=300)
def load_dimensions():
    dim_date = pd.read_sql("SELECT date_id, full_date, weekday_name, is_weekend, quarter_no, year_no FROM dim_date", engine)
    dim_customer = pd.read_sql("SELECT customer_id, customer_name, email, address FROM dim_customer", engine)
    dim_product = pd.read_sql("SELECT product_id, product_name, category, current_price FROM dim_product", engine)
    return dim_date, dim_customer, dim_product

# fact 테이블
@st.cache_data(ttl=300)
def load_date_range():
    sql = """
    SELECT MIN(d.full_date) AS min_date, MAX(d.full_date) AS max_date
    FROM fact_sales s
    JOIN dim_date d ON d.date_id = s.date_id
    """
    df = pd.read_sql(sql, engine)
    min_d = to_date_safe(df.loc[0, "min_date"]) if not df.empty else None
    max_d = to_date_safe(df.loc[0, "max_date"]) if not df.empty else None
    return min_d, max_d

# 필터 옵션
@st.cache_data(ttl=300)
def load_filter_options():
    cat_df = pd.read_sql("SELECT DISTINCT category FROM dim_product ORDER BY category", engine)
    pay_df = pd.read_sql("SELECT DISTINCT payment_method FROM fact_sales ORDER BY payment_method", engine)
    cust_df = pd.read_sql("SELECT customer_id, customer_name FROM dim_customer ORDER BY customer_name", engine)

    # df를 리스트와 df로 반환
    return cat_df["category"].tolist(), pay_df["payment_method"].tolist(), cust_df


@st.cache_data(ttl=300)
def load_fact_joined(filters):
    where = ["d.full_date BETWEEN :date_from AND :date_to"]
    params = {
        "date_from": filters["date_from"],
        "date_to": filters["date_to"],
    }

    if filters["customers"]:
        placeholders = make_in_clause(filters["customers"], "c", params)
        where.append(f"c.customer_id IN ({placeholders})")

    if filters["categories"]:
        placeholders = make_in_clause(filters["categories"], "k", params)
        where.append(f"p.category IN ({placeholders})")

    if filters["payments"]:
        placeholders = make_in_clause(filters["payments"], "m", params)
        where.append(f"s.payment_method IN ({placeholders})")

    where_sql = " WHERE " + " AND ".join(where)

    sql = f"""
    SELECT
        s.transaction_id,
        d.full_date,
        c.customer_id, c.customer_name,
        p.product_id, p.product_name, p.category,
        s.quantity, s.unit_price_at_sale, s.amount,
        s.payment_method
    FROM fact_sales s
    JOIN dim_date     d ON d.date_id = s.date_id
    JOIN dim_customer c ON c.customer_id = s.customer_id
    JOIN dim_product  p ON p.product_id = s.product_id
    {where_sql}
    ORDER BY d.full_date, s.transaction_id
    """

    return pd.read_sql(text(sql), engine, params=params)

dim_date, dim_customer, dim_product = load_dimensions()
min_d, max_d = load_date_range()

# 기본값 설정
default_from = min_d or date.today()
default_to = max_d or date.today()

categories, payments, cust_df = load_filter_options()

st.sidebar.header("필터")
col1, col2 = st.sidebar.columns(2)
with col1:
    date_from = st.date_input("시작일", value=default_from)
with col2:
    date_to = st.date_input("종료일", value=default_to)

cust_opt = st.sidebar.multiselect(
    "고객 선택",
    options=cust_df["customer_id"].tolist(),
    format_func=lambda cid: f"{cid} - {cust_df.loc[cust_df['customer_id']==cid, 'customer_name'].values[0]}",
)

cat_opt = st.sidebar.multiselect("카테고리 선택", options=categories)
pay_opt = st.sidebar.multiselect("결제수단 선택", options=payments)

filters = {
    "date_from": pd.to_datetime(date_from).date(),
    "date_to": pd.to_datetime(date_to).date(),
    "customers": cust_opt,
    "categories": cat_opt,
    "payments": pay_opt,
}

data = load_fact_joined(filters)

st.subheader("📈 핵심 지표")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
if data.empty:
    kpi1.metric("매출 합계", "0")
    kpi2.metric("총 수량", "0")
    kpi3.metric("거래 건수", "0")
    kpi4.metric("평균 객단가", "0")
else:
    total_sales = float(data["amount"].sum())
    total_qty = int(data["quantity"].sum())
    txn_cnt = int(data["transaction_id"].nunique()) # 중복제거 카운트
    aov = total_sales / txn_cnt if txn_cnt else 0.0

    kpi1.metric("매출 합계", f"{total_sales:,.2f}")
    kpi2.metric("총 수량", f"{total_qty:,d}")
    kpi3.metric("거래 건수", f"{txn_cnt:,d}")
    kpi4.metric("평균 객단가(AOV)", f"{aov:,.2f}")

st.divider()

tab1, tab2, tab3 = st.tabs(["📅 일자별 추이", "🧃 카테고리별 매출", "📃 원본/디멘션"])

with tab1:
    st.subheader("일자별 매출 추이")
    if data.empty:
        st.info("조건에 해당하는 데이터가 없습니다.")
    else:
        daily = data.groupby("full_date", as_index=False)["amount"].sum()
        st.line_chart(daily, x="full_date", y="amount", height=300)

with tab2:
    st.subheader("카테고리별 매출")
    if data.empty:
        st.info("조건에 해당하는 데이터가 없습니다.")
    else:
        by_cat = (
            data.groupby("category", as_index=False)["amount"].sum()
            .sort_values("amount", ascending=False)
        )
        st.bar_chart(by_cat, x="category", y="amount", height=300)

with tab3:
    st.subheader("원본 데이터")
    st.dataframe(data, use_container_width=True)
    st.download_button(
        "CSV 다운로드",
        data=data.to_csv(index=False).encode("utf-8-sig"),
        file_name="sales_filtered.csv",
        mime="text/csv",
    )

    st.markdown("### 디멘션 미리보기")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.caption("dim_date")
        st.dataframe(dim_date.head(10), use_container_width=True, height=220)
    with c2:
        st.caption("dim_customer")
        st.dataframe(dim_customer.head(10), use_container_width=True, height=220)
    with c3:
        st.caption("dim_product")
        st.dataframe(dim_product.head(10), use_container_width=True, height=220)