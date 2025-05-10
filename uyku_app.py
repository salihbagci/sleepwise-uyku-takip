import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# Veritabanı bağlantısı
conn = sqlite3.connect("sleepwise.db", check_same_thread=False)
cursor = conn.cursor()

# Tabloları oluştur
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

# Başlık
st.title("🛌 SleepWise - Uyku Takip ve Öneri Sistemi")

# Giriş alanı
user_name = st.text_input("Adınızı girin:")

# Tarih ve saat girişi
sleep_time = st.time_input("Uykuya başlama saati:")
wake_time = st.time_input("Uyanma saati:")
today = st.date_input("Bugünün tarihi:")

if st.button("Kaydet"):
    if user_name:
        # Saat farkı
        sleep_dt = datetime.combine(today, sleep_time)
        wake_dt = datetime.combine(today + timedelta(days=1), wake_time) if wake_time < sleep_time else datetime.combine(today, wake_time)
        duration = wake_dt - sleep_dt
        hours = duration.total_seconds() / 3600

        # Veritabanına kaydet
        cursor.execute("INSERT INTO sleep_records (user_name, sleep_time, wake_time, date) VALUES (?, ?, ?, ?)", 
                       (user_name, str(sleep_time), str(wake_time), str(today)))
        conn.commit()

        # Öneri sistemi
        if hours < 6:
            suggestion = "Daha fazla uyumalısın! Ortalama uyku süren 6 saatin altında."
        elif hours > 9:
            suggestion = "Çok fazla uyuyorsun, bu da sağlıksız olabilir."
        else:
            suggestion = "Harika! Uyku süren ideal aralıkta."

        # Öneriyi kaydet
        cursor.execute("INSERT INTO suggestions (user_name, suggestion_text, created_at) VALUES (?, ?, ?)", 
                       (user_name, suggestion, str(datetime.now())))
        conn.commit()

        st.success(f"✅ Uyku süresi: {round(hours, 2)} saat\n\n📢 Öneri: {suggestion}")
    else:
        st.warning("Lütfen adınızı girin.")

# Geçmiş kayıtları göster
if user_name:
    st.subheader("📊 Uyku Geçmişin:")
    df = pd.read_sql_query("SELECT * FROM sleep_records WHERE user_name = ?", conn, params=(user_name,))
    st.dataframe(df)

    st.subheader("💡 Öneri Geçmişin:")
    df2 = pd.read_sql_query("SELECT * FROM suggestions WHERE user_name = ?", conn, params=(user_name,))
    st.dataframe(df2)
import matplotlib.pyplot as plt

# Son 7 günü al
if user_name:
    st.subheader("📊 Haftalık Uyku Süresi Grafiği")

    query = """
    SELECT date, sleep_time, wake_time FROM sleep_records 
    WHERE user_name = ? ORDER BY date DESC LIMIT 7
    """
    df_graph = pd.read_sql_query(query, conn, params=(user_name,))

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

        # Çizgi grafik
        fig, ax = plt.subplots()
        ax.plot(labels[::-1], durations[::-1], marker='o')
        ax.set_ylabel("Uyku Süresi (saat)")
        ax.set_xlabel("Tarih")
        ax.set_title("Son 7 Günlük Uyku Süresi")
        ax.grid(True)
        st.pyplot(fig)

