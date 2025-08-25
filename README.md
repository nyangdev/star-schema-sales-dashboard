#### 설명 줄글
https://velog.io/@nyangdev/%EC%8A%A4%ED%83%80%EC%8A%A4%ED%82%A4%EB%A7%88%EC%99%80-%EC%8A%A4%EB%85%B8%EC%9A%B0%ED%94%8C%EB%A0%88%EC%9D%B4%ED%81%AC-%EC%8A%A4%ED%82%A4%EB%A7%88-%EC%9E%84%EC%9D%98%EB%A1%9C-%EC%83%9D%EC%84%B1%ED%95%9C-%EC%83%98%ED%94%8C-%EB%8D%B0%EC%9D%B4%ED%84%B0-%EC%8B%9C%EA%B0%81%ED%99%94#%EC%BD%94%EB%93%9C-%ED%9D%90%EB%A6%84%EB%8F%84

``` mermaid
flowchart TD
  %% ---------- Start / Setup ----------
  A([앱 시작]) --> B[페이지 설정/타이틀/캡션]
  B --> C["get_db_config() ← st.secrets['mariadb']"]
  C -->|있음| D["@st.cache_resource get_engine() → SQLAlchemy Engine"]
  C -->|없음| C1[경고 표시: secrets.toml 누락] --> D

  %% ---------- Cached loads ----------
  D --> E["@st.cache_data load_dimensions() → dim_date, dim_customer, dim_product"]
  D --> F["@st.cache_data load_date_range() → (min_d, max_d)"]
  D --> G["@st.cache_data load_filter_options() → categories[], payments[], cust_df"]

  %% ---------- Sidebar / Filters ----------
  F --> H["기본 날짜 설정 (default_from/to)"]
  G --> I[사이드바 멀티선택: 고객/카테고리/결제수단]
  H --> J["필터 딕셔너리 구성 {date_from, date_to, ...}"]
  I --> J

  %% ---------- Dynamic WHERE + IN ----------
  J --> K{고객 선택 있음?}
  K -- 예 --> K1[IN 절 추가: c.customer_id]
  K -- 아니오 --> K2[조건 생략]

  J --> L{카테고리 선택 있음?}
  L -- 예 --> L1[IN 절 추가: p.category]
  L -- 아니오 --> L2[조건 생략]

  J --> M{결제수단 선택 있음?}
  M -- 예 --> M1[IN 절 추가: s.payment_method]
  M -- 아니오 --> M2[조건 생략]

  K1 --> N
  K2 --> N
  L1 --> N
  L2 --> N
  M1 --> N
  M2 --> N
  N["WHERE 조립 + 바인드 파라미터(make_in_clause)"] --> O["@st.cache_data load_fact_joined(filters)\nJOIN fact_sales + dim_* → data(DataFrame)"]

  %% ---------- KPIs & Tabs ----------
  O --> P{data.empty?}
  P -- 예 --> Q["KPIs 0 세팅\nst.info('조건 데이터 없음')"]
  P -- 아니오 --> R["KPIs 계산: sum(amount), sum(qty), nunique(txn), AOV"]
  R --> S[탭1: 일자별 매출 line_chart]
  R --> T[탭2: 카테고리별 매출 bar_chart]
  R --> U["탭3: 원본 데이터 표시 + CSV 다운로드(utf-8-sig)"]
  E --> V["탭3: 디멘션 미리보기(dim_date/customer/product)"]
  V --> U

  %% ---------- Styles (dark-ish boxes like screenshot) ----------
  classDef step fill:#2f2f2f,stroke:#7a7a7a,color:#fff,rx:6,ry:6;
  classDef decision fill:#2f2f2f,stroke:#7a7a7a,color:#fff,rx:4,ry:4;
  class A,B,C,C1,D,E,F,G,H,I,J,K1,K2,L1,L2,M1,M2,N,O,Q,R,S,T,U,V step;
  class K,L,M,P decision;

```

