import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import plotly.express as px
from catboost import CatBoostRegressor
from streamlit_option_menu import option_menu
import folium
from streamlit_folium import st_folium
import random
import time
from streamlit_autorefresh import st_autorefresh

# --- 1. LOGIN SYSTEM ---
def login():
    if 'auth' not in st.session_state: st.session_state.auth = False
    if not st.session_state.auth:
        st.title("🛡️ CampusEats Enterprise Portal")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Unlock System"):
            if u == "admin" and p == "nust123":
                st.session_state.auth = True
                st.rerun()
            else: st.error("Invalid Credentials")
        return False
    return True

# --- 2. DATABASE & AI ENGINE ---

DB_URL = f"postgresql://{st.secrets['db_user']}:{st.secrets['db_password']}@{st.secrets['db_host']}:{st.secrets['db_port']}/{st.secrets['db_name']}"
engine = create_engine(DB_URL)

@st.cache_resource
def get_everything():
    query = """
    SELECT o.orderid, o.totalvalue, c.categoryname as category, u.name as campus, 
           EXTRACT(HOUR FROM o.ordertime) as hour, o.ordertime
    FROM orders o 
    JOIN stalls s ON o.stallid = s.stallid 
    JOIN categories c ON s.categoryid = c.categoryid 
    JOIN universities u ON s.universityid = u.universityid
    ORDER BY o.ordertime DESC
    """
    df = pd.read_sql(query, engine)
    model = CatBoostRegressor(iterations=100, depth=6, verbose=False)
    model.fit(df[['category', 'campus', 'hour']], df['totalvalue'], cat_features=['category', 'campus'])
    return df, model

# --- 3. MAIN APP INTERFACE ---
if login():
    df, model = get_everything()

    with st.sidebar:
        selected = option_menu("Command Center", 
            ["Dashboard", "Live Operations", "Campus Tycoon (GAME)", "Security Audit", "Market Analysis", "Strategic Map", "AI Concierge", "What-If Simulator", "Predictor", "System Health"],
            icons=["bar-chart", "plus-circle", "controller", "shield-lock", "cart4", "map", "robot", "calculator", "magic", "cpu"], 
            menu_icon="pci-card", default_index=0)

    # --- FEATURE: CAFE TYCOON GAME (WITH AUTO-TIMER & CELEBRATION) ---
    if selected == "Campus Tycoon (GAME)":
        st.title("🎮 Cafe Tycoon: Pro Manager")
        
        # This makes the clock tick every 1 second
        st_autorefresh(interval=1000, key="gametimer")

        if 'game_score' not in st.session_state: st.session_state.game_score = 0
        if 'target_order' not in st.session_state: st.session_state.target_order = random.choice(["🍔 Burger", "🍕 Pizza", "☕ Coffee", "🍟 Fries"])
        if 'start_time' not in st.session_state: st.session_state.start_time = time.time()

        # Win Logic
        if st.session_state.game_score >= 50:
            st.balloons()
            st.success("🏆 MASTER MANAGER! Use Code: **CAFEPRO** for 50% off!")
            if st.button("Reset & Play Again"):
                st.session_state.game_score = 0
                st.session_state.start_time = time.time()
                st.rerun()
            st.stop()

        # Timer Calculation
        elapsed = time.time() - st.session_state.start_time
        remaining = max(0, int(10 - elapsed))

        c1, c2 = st.columns(2)
        c1.metric("Score", st.session_state.game_score)
        timer_class = "normal" if remaining > 3 else "bold"
        c2.subheader(f"Time: {remaining}s")

        if remaining == 0:
            st.session_state.game_score -= 5
            st.session_state.start_time = time.time()
            st.rerun()

        st.info(f"### Serve a {st.session_state.target_order}!")
        cols = st.columns(4)
        opts = ["🍔 Burger", "🍕 Pizza", "☕ Coffee", "🍟 Fries"]
        for i, o in enumerate(opts):
            if cols[i].button(o, use_container_width=True):
                if o == st.session_state.target_order:
                    st.session_state.game_score += 10
                    st.session_state.target_order = random.choice(opts)
                    st.session_state.start_time = time.time()
                else:
                    st.session_state.game_score -= 5
                st.rerun()

    # --- FEATURE: DASHBOARD ---
    elif selected == "Dashboard":
        st.title("📊 Consumption Analytics")
        k1, k2, k3 = st.columns(3)
        k1.metric("Revenue", f"{df['totalvalue'].sum():,.0f} PKR")
        k2.metric("Orders", len(df))
        k3.metric("Avg Spend", f"{df['totalvalue'].mean():.1f} PKR")
        st.plotly_chart(px.sunburst(df, path=['campus', 'category'], values='totalvalue'))

    # --- FEATURE: LIVE OPERATIONS (CRUD) ---
    elif selected == "Live Operations":
        st.title("⚙️ Data Entry & Logs")
        with st.form("add"):
            sid = st.number_input("Stall ID", 1, 20)
            amt = st.number_input("Amount", 10, 5000)
            if st.form_submit_button("Submit"):
                with engine.connect() as conn:
                    conn.execute(text(f"INSERT INTO orders (stallid, totalvalue, ordertime) VALUES ({sid}, {amt}, NOW())"))
                    conn.commit()
                st.cache_resource.clear()
                st.rerun()
        st.write("### Recent DB Transactions")
        st.dataframe(df.head(10))

    # --- FEATURE: SECURITY AUDIT ---
    elif selected == "Security Audit":
        st.title("🛡️ Fraud Detection")
        mean_val = df['totalvalue'].mean()
        anomalies = df[df['totalvalue'] > (mean_val * 4)]
        if not anomalies.empty:
            st.warning(f"Found {len(anomalies)} suspicious transactions!")
            st.dataframe(anomalies)
        else:
            st.success("Data Integrity Verified.")

    # --- FEATURE: MARKET ANALYSIS ---
    elif selected == "Market Analysis":
        st.title("🛒 Market Trends")
        fig = px.bar(df.groupby(['campus', 'category']).size().reset_index(name='count'), 
                     x="category", y="count", color="campus", barmode="group")
        st.plotly_chart(fig)

    # --- FEATURE: STRATEGIC MAP ---
    elif selected == "Strategic Map":
        st.title("📍 Hub Locations")
        m = folium.Map(location=[30.3753, 69.3451], zoom_start=5)
        st_folium(m, width=1000)

    # --- FEATURE: AI CONCIERGE ---
    elif selected == "AI Concierge":
        st.title("🤖 AI Assistant")
        if "msgs" not in st.session_state: st.session_state.msgs = []
        for m in st.session_state.msgs: st.chat_message(m["role"]).write(m["content"])
        if p := st.chat_input("Ask..."):
            st.session_state.msgs.append({"role": "user", "content": p})
            ans = f"Analyzing... Busy campus is {df['campus'].iloc[0]}."
            st.session_state.msgs.append({"role": "assistant", "content": ans})
            st.rerun()

    # --- FEATURE: WHAT-IF SIMULATOR ---
    elif selected == "What-If Simulator":
        st.title("🧮 Revenue Simulator")
        adj = st.slider("Price Increase %", -10, 50, 0)
        st.metric("Predicted Revenue", f"{df['totalvalue'].sum() * (1 + adj/100):,.0f} PKR")

    # --- FEATURE: PREDICTOR ---
    elif selected == "Predictor":
        st.title("🔮 AI Prediction")
        p_camp = st.selectbox("Campus", df['campus'].unique())
        p_cat = st.selectbox("Category", df['category'].unique())
        p_hr = st.slider("Hour", 8, 22, 12)
        if st.button("Predict"):
            pred = model.predict(pd.DataFrame({'category': [p_cat], 'campus': [p_camp], 'hour': [p_hr]}))[0]
            st.success(f"Expected Spend: {pred:.2f} PKR")

    # --- FEATURE: SYSTEM HEALTH ---
    elif selected == "System Health":
        st.title("🛡️ DB Health")
        st.metric("PostgreSQL", "Connected")
        st.table(pd.DataFrame({"Table": ["Orders", "Campus"], "Rows": [len(df), 3]}))
