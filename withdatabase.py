import streamlit as st
import sqlite3
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# === Initialize SQLite Database ===
DB_FILE = "users.db"

def initialize_database():
    """Creates the 'users' table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    conn.commit()
    conn.close()

initialize_database()

# === Database Functions ===
def register_user(username, password):
    """Adds a new user to the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def authenticate_user(username, password):
    """Checks user credentials in the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = cursor.fetchone()
    conn.close()
    return user is not None

# === Login and Registration Functions ===
def login():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if authenticate_user(username, password):
            st.session_state["authenticated"] = True
            st.success("Login successful!")
        else:
            st.error("Invalid username or password.")

def register():
    st.title("Register")
    username = st.text_input("Create a Username")
    password = st.text_input("Create a Password", type="password")
    if st.button("Register"):
        if register_user(username, password):
            st.success("Registration successful! Please log in.")
        else:
            st.error("Username already exists. Please choose another username.")

def logout():
    st.session_state["authenticated"] = False
    st.info("You have logged out.")

# === Main Application ===
def main_app():
    st.title("Interactive Stock Candlestick App")

    # User inputs for stock data
    ticker = st.text_input("Enter Stock Ticker (e.g., AAPL)", "AAPL").upper()
    start_date = st.date_input("Start Date", value=pd.to_datetime("2020-01-01"))
    end_date = st.date_input("End Date", value=pd.to_datetime("today"))

    if start_date > end_date:
        st.error("Start date must be before end date.")
        st.stop()

    try:
        # Fetch stock data from yfinance
        data = yf.download(ticker, start=start_date, end=end_date)

        if data.empty:
            st.warning(f"No data found for ticker {ticker} in the selected date range.")
        else:
            # Interactive tabs
            tab1, tab2, tab3, tab4 = st.tabs(["Candlestick Chart", "RSI", "MACD", "Data"])

           with tab1:  # Grafik Utama
                fig = go.Figure(data=[go.Candlestick(x=data.index,
                                                      open=data['Open'],
                                                      high=data['High'],
                                                      low=data['Low'],
                                                      close=data['Close'])])

                fig.update_layout(title=f"Harga Saham {ticker}",
                                  xaxis_title="Tanggal",
                                  yaxis_title="Harga",
                                  xaxis_rangeslider_visible=False,
                                  template="plotly_dark")

                # Rata-rata Bergerak (MA)
                ma_days = st.slider("Periode Rata-Rata Bergerak", 5, 200, 20)
                data[f'MA{ma_days}'] = data['Close'].rolling(window=ma_days).mean()
                fig.add_trace(go.Scatter(x=data.index, y=data[f'MA{ma_days}'], mode='lines', name=f'MA {ma_days}'))

                # Bollinger Bands
                bb_window = st.slider("Periode Bollinger Bands", 5, 200, 20)
                data['MA'] = data['Close'].rolling(window=bb_window).mean()
                data['Std'] = data['Close'].rolling(window=bb_window).std()
                data['Upper Band'] = data['MA'] + (data['Std'] * 2)
                data['Lower Band'] = data['MA'] - (data['Std'] * 2)
                fig.add_trace(go.Scatter(x=data.index, y=data['Upper Band'], mode='lines', name='Upper Band', line=dict(color='red', width=1)))
                fig.add_trace(go.Scatter(x=data.index, y=data['Lower Band'], mode='lines', name='Lower Band', line=dict(color='red', width=1)))

                st.plotly_chart(fig)
               
            with tab2:  # Relative Strength Index (RSI)
                rsi_period = st.slider("RSI Period", 2, 20, 14)
                delta = data['Close'].diff()
                up = delta.clip(lower=0)
                down = -1 * delta.clip(upper=0)
                avg_up = up.rolling(window=rsi_period).mean()
                avg_down = down.rolling(window=rsi_period).mean()
                rs = avg_up / avg_down.replace(0, np.nan)
                data['RSI'] = 100 - (100 / (1 + rs))
                fig_rsi = go.Figure(data=[go.Scatter(x=data.index, y=data['RSI'], mode='lines', name='RSI')])
                fig_rsi.update_layout(title=f"RSI {ticker}", yaxis_title="RSI", template="plotly_dark", yaxis_range=[0, 100])
                st.plotly_chart(fig_rsi)

           with tab3:  # MACD
                exp1 = data['Close'].ewm(span=12, adjust=False).mean()
                exp2 = data['Close'].ewm(span=26, adjust=False).mean()
                macd = exp1 - exp2
                signal = macd.ewm(span=9, adjust=False).mean()
                data['MACD'] = macd
                data['Signal Line'] = signal

                fig_macd = go.Figure()
                fig_macd.add_trace(go.Scatter(x=data.index, y=data['MACD'], mode='lines', name='MACD'))
                fig_macd.add_trace(go.Scatter(x=data.index, y=data['Signal Line'], mode='lines', name='Signal Line'))
                fig_macd.update_layout(title=f"MACD {ticker}", template="plotly_dark")
                st.plotly_chart(fig_macd)

            with tab4:  # Data Table
                if st.checkbox("Show Data Table"):
                    st.dataframe(data)

    except Exception as e:
        st.error(f"An error occurred: {e}. Please check the ticker symbol and date range.")

# === Main Program ===
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    menu = st.sidebar.radio("Menu", ["Login", "Register"])
    if menu == "Login":
        login()
    elif menu == "Register":
        register()
else:
    if st.sidebar.button("Logout"):
        logout()
    else:
        main_app()
