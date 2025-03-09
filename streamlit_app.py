import streamlit as st
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
from datetime import datetime

st.set_page_config(layout="wide")  # Make the app full-width

def get_alpha_vantage_data(ticker, function):
    api_key = st.secrets["alpha_vantage"]["api_key"]
    url = f"https://www.alphavantage.co/query?function={function}&symbol={ticker}&apikey={api_key}"
    response = requests.get(url)
    data = response.json()
    
    if "Note" in data:
        st.error("API limit reached. Please try again later.")
        return {}
    if "Error Message" in data:
        st.error(f"Invalid API request: {data['Error Message']}")
        return {}
    
    return data

def fetch_financials(ticker):
    st.write("Fetching data from Alpha Vantage...")
    
    overview = get_alpha_vantage_data(ticker, "OVERVIEW")
    income_statement = get_alpha_vantage_data(ticker, "INCOME_STATEMENT")
    balance_sheet = get_alpha_vantage_data(ticker, "BALANCE_SHEET")
    cash_flow = get_alpha_vantage_data(ticker, "CASH_FLOW")
    earnings = get_alpha_vantage_data(ticker, "EARNINGS")
    stock_prices = get_alpha_vantage_data(ticker, "TIME_SERIES_MONTHLY_ADJUSTED")
    
    if not earnings or not stock_prices:
        st.warning("Some financial data could not be retrieved. Please verify the ticker and API availability.")
    
    return overview, income_statement, balance_sheet, cash_flow, earnings, stock_prices

def transform_financial_data(data):
    if "annualReports" not in data:
        return pd.DataFrame()
    
    df = pd.DataFrame(data["annualReports"])
    df.set_index("fiscalDateEnding", inplace=True)
    df = df.transpose()
    df.columns = [col[:4] for col in df.columns]  # Convert column names to just years
    df = df.apply(pd.to_numeric, errors='coerce') / 1e6  # Convert to millions
    return df

def plot_financial_chart(df, title):
    if df.empty:
        st.write(f"No data available for {title}.")
        return
    
    selected_items = st.multiselect(f"Select line items to display for {title}", df.index, default=df.index[:3])
    if selected_items:
        fig = px.line(df.loc[selected_items].T, markers=True, title=title)
        st.plotly_chart(fig)
    
st.title("Stock Valuation App")

stock_ticker = st.text_input("Enter Stock Ticker:")
if stock_ticker:
    overview, income_statement, balance_sheet, cash_flow, earnings, stock_prices = fetch_financials(stock_ticker)
    
    st.subheader("Stock Price vs Fair Value Estimate")
    st.write("(Chart placeholder – Implement fair value calculations here)")
    
    st.subheader("Discounted Cash Flow Valuation")
    st.write("(DCF Calculation placeholder)")
    
    with st.expander("View Company Overview"):
        st.write(overview)
    
    with st.expander("View Financial Statements"):
        st.write("### Income Statement (in Millions)")
        income_df = transform_financial_data(income_statement)
        st.dataframe(income_df)
        plot_financial_chart(income_df, "Income Statement")
        
        st.write("### Balance Sheet (in Millions)")
        balance_df = transform_financial_data(balance_sheet)
        st.dataframe(balance_df)
        plot_financial_chart(balance_df, "Balance Sheet")
        
        st.write("### Cash Flow Statement (in Millions)")
        cash_flow_df = transform_financial_data(cash_flow)
        st.dataframe(cash_flow_df)
        plot_financial_chart(cash_flow_df, "Cash Flow Statement")