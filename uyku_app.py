import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# Oturum kontrol değişkenlerini başlat
if "user_logged_in" not in st.session_state:
    st.session_state.user_logged_in = False
    st.session_state.current_user = None

# Veritabanı bağlantısı
conn = sqlite3.connect("sleepwise.db", check_same_thread=False)
cursor = conn.cursor()

# Tablolar
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE,
    password TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS sleep_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_name TEXT,
    sleep_time TEXT,
    wake_time TEXT,
    date TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_name TEXT,
    suggestion_text TEXT,
    created_at TEXT
)
""")
conn.commit()

# 🔐 Giriş Paneli
st.sidebar.title("🔐 Giriş Paneli")
auth_mode = st.sidebar.radio("Seçim yap:", ["Giriş Yap", "Kayıt Ol"])
login_email = st.sidebar.text_input("E-posta")
login_pass = st.sidebar.text_input("Şifre", type="password")

if auth_mode == "Kayıt Ol":
    if st.sidebar.button("Kayıt Ol"):
        try:
            cursor.execute("INSERT INTO users (email, password) VALUES (?, ?)", (login_email, login_pass))
            conn.commit()
            st.sidebar.success("Kayıt başarılı! Giriş yapabilirsiniz.")
        except:
            st.sidebar.error("Bu e-posta zaten kayıtlı.")
elif auth_mode == "Giriş Yap":
    if st.sidebar.button("Giriş Yap"):
        cursor.execute("SELECT * FROM users WHERE email = ? AND password = ?", (login_email, login_pass))
        user = cursor.fetchone()
        if user:
            st.sidebar.success(f"Hoş geldin, {login_email}")
            st.session_state.user_logged_in = True
            st.session_state.current_user = login_email
        else:
            st.sidebar.error("E-posta veya şifre hatalı.")

# Eğer giriş yaptıysa uygulamayı göster
if st.session_state.user_logged_in:
    current_user = st.session_state.current_user
    st.title("🛌 SleepWise - Uyku Takip ve Öneri Sistemi")

    # Saat ve tarih giriş alanı
    sleep_time = st.time_input("Uykuya başlama saati:")
    wake_time = st.time_input("Uyanma saati:")
    today = st.date_input("Bugünün tarihi:")

    if st.button("Kaydet"):
        sleep_dt = datetime.combine(today, sleep_time)
        wake_dt = datetime.combine(today + timedelta(days=1), wake_time) if wake_time < sleep_time else datetime.combine(today, wake_time)
        duration = wake_dt - sleep_dt
        hours = duration.total_seconds() / 3600

        # Veritabanına kaydet
        cursor.execute("INSERT INTO sleep_records (user_name, sleep_time, wake_time, date) VALUES (?, ?, ?, ?)",
                       (current_user, str(sleep_time), str(wake_time), str(today)))
        conn.commit()

        # Öneri üret
        if hours < 6:
            suggestion = "Daha fazla uyumalısın! Ortalama uyku süren 6 saatin altında."
        elif hours > 9:
            suggestion = "Çok fazla uyuyorsun, bu da sağlıksız olabilir."
        else:
            suggestion = "Harika! Uyku süren ideal aralıkta."

        # Öneriyi kaydet
        cursor.execute("INSERT INTO suggestions (user_name, suggestion_text, created_at) VALUES (?, ?, ?)",
                       (current_user, suggestion, str(datetime.now())))
        conn.commit()

        st.success(f"✅ Uyku süresi: {round(hours, 2)} saat\n\n📢 Öneri: {suggestion}")

    # Geçmiş veriler
    st.subheader("📊 Uyku Geçmişin:")
    df = pd.read_sql_query("SELECT * FROM sleep_records WHERE user_name = ?", conn, params=(current_user,))
    st.dataframe(df)

    st.subheader("💡 Öneri Geçmişin:")
    df2 = pd.read_sql_query("SELECT * FROM suggestions WHERE user_name = ?", conn, params=(current_user,))
    st.dataframe(df2)

    # Haftalık grafik
    st.subheader("📈 Haftalık Uyku Süresi Grafiği")
    query = """
    SELECT date, sleep_time, wake_time FROM sleep_records 
    WHERE user_name = ? ORDER BY date DESC LIMIT 7
    """
    df_graph = pd.read_sql_query(query, conn, params=(current_user,))

    if not df_graph.empty:
        durations = []
        labels = []

        for _, row in df_graph.iterrows():
            date = row["date"]
            sleep_time = datetime.strptime(row["sleep_time"], "%H:%M:%S")
            wake_time = datetime.strptime(row["wake_time"], "%H:%M:%S")
            if wake_time < sleep_time:
                wake_time += timedelta(days=1)
            hours = (wake_time - sleep_time).total_seconds() / 3600
            durations.append(hours)
            labels.append(date)

        fig, ax = plt.subplots()
        ax.plot(labels[::-1], durations[::-1], marker='o')
        ax.set_ylabel("Uyku Süresi (saat)")
        ax.set_xlabel("Tarih")
        ax.set_title("Son 7 Günlük Uyku Süresi")
        ax.grid(True)
        st.pyplot(fig)

        # Ortalama
        ortalama = sum(durations) / len(durations)
        st.info(f"Son 7 gün ortalama uyku süren: {ortalama:.2f} saat.")
        if ortalama < 6:
            st.warning("Daha fazla uyumalısın! Uyku süren sağlıklı düzeyin altında.")
        elif ortalama > 9:
            st.warning("Çok fazla uyuyorsun, bu da sağlıksız olabilir.")
        else:
            st.success("Harika! Uyku süren ideal aralıkta.")
