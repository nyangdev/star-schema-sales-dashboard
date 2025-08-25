#### 설명 줄글
https://velog.io/@nyangdev/%EC%8A%A4%ED%83%80%EC%8A%A4%ED%82%A4%EB%A7%88%EC%99%80-%EC%8A%A4%EB%85%B8%EC%9A%B0%ED%94%8C%EB%A0%88%EC%9D%B4%ED%81%AC-%EC%8A%A4%ED%82%A4%EB%A7%88-%EC%9E%84%EC%9D%98%EB%A1%9C-%EC%83%9D%EC%84%B1%ED%95%9C-%EC%83%98%ED%94%8C-%EB%8D%B0%EC%9D%B4%ED%84%B0-%EC%8B%9C%EA%B0%81%ED%99%94#%EC%BD%94%EB%93%9C-%ED%9D%90%EB%A6%84%EB%8F%84

``` mermaid
flowchart TD
  %% ---------- Start / Setup ----------
  A([앱 시작]) --> B[set_page_config / title / caption]
  B --> C["get_db_config() ← st.secrets['mariadb']"]
  C --> D{mariadb 설정 존재?}
  D -- 예 --> E["@st.cache_resource get_engine()\n→ SQLAlchemy Engine(pool_pre_ping)"]
  D -- 아니오 --> D1["st.error('secrets 누락 경고')"] --> D2("[st.stop() 종료]")

  %% ---------- Cached loads ----------
  E --> F["@st.cache_data load_dimensions()\n→ dim_date, dim_customer, dim_product"]
  E --> G["@st.cache_data load_date_range()\n→ (min_d, max_d)"]
  E --> H["@st.cache_data load_filter_options()\n→ categories[], payments[], cust_df"]

  %% ---------- Sidebar / Filters ----------
  G --> I["기본 날짜 결정\n(min_d/max_d 또는 오늘)"]
  H --> J[사이드바 멀티선택\n고객/카테고리/결제수단]
  I --> K["필터 dict 구성\n{date_from,date_to,customers,categories,payments}"]
  J --> K

  %% ---------- Dynamic WHERE + IN ----------
  K --> L[기본 WHERE: d.full_date BETWEEN :date_from AND :date_to]
  K --> M{고객 선택 있음?}
  M -- 예 --> M1["make_in_clause → c.customer_id IN (:c0,:c1,...)"]
  M -- 아니오 --> M2[생략]
  K --> N{카테고리 선택 있음?}
  N -- 예 --> N1["make_in_clause → p.category IN (:k0,:k1,...)"]
  N -- 아니오 --> N2[생략]
  K --> O{결제수단 선택 있음?}
  O -- 예 --> O1["make_in_clause → s.payment_method IN (:m0,:m1,...)"]
  O -- 아니오 --> O2[생략]

  M1 --> P
  M2 --> P
  N1 --> P
  N2 --> P
  O1 --> P
  O2 --> P
  P[WHERE 조합 + params] --> Q["@st.cache_data load_fact_joined(filters)\nJOIN fact_sales + dim_* → data(DataFrame)"]

  %% ---------- KPIs & Tabs ----------
  Q --> R{data.empty?}
  R -- 예 --> R1[KPIs 0 표시] --> R2[탭들에 '데이터 없음' 안내]
  R -- 아니오 --> S["지표 계산\nsum(amount), sum(quantity),\n nuniq(transaction_id), AOV"]
  S --> T["탭1: 일자별 groupby(full_date).sum(amount)\n→ st.line_chart"]
  S --> U["탭2: 카테고리별 groupby(category).sum(amount)\n→ st.bar_chart"]
  S --> V["탭3: 원본 데이터 표시\n+ CSV(utf-8-sig) 다운로드"]
  F --> W[탭3: dim_date/customer/product 미리보기]
  W --> V

  %% ---------- Styles (dark-ish) ----------
  classDef step fill:#2f2f2f,stroke:#7a7a7a,color:#fff,rx:6,ry:6;
  classDef decision fill:#2f2f2f,stroke:#7a7a7a,color:#fff,rx:4,ry:4;
  classDef stop fill:#5a2b2b,stroke:#aa6666,color:#fff,rx:10,ry:10;

  class A,B,C,E,F,G,H,I,J,K,L,M1,M2,N1,N2,O1,O2,P,Q,R1,R2,S,T,U,V,W step;
  class D,M,N,O,R decision;
  class D2 stop;


```

