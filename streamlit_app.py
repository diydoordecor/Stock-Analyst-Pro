import streamlit as st
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

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
    key_ratios = get_alpha_vantage_data(ticker, "KEY_RATIOS")
    stock_prices = get_alpha_vantage_data(ticker, "TIME_SERIES_MONTHLY_ADJUSTED")
    
    if not earnings or not stock_prices:
        st.warning("Some financial data could not be retrieved. Please verify the ticker and API availability.")
    
    return overview, income_statement, balance_sheet, cash_flow, earnings, key_ratios, stock_prices

def calculate_fair_value(earnings, key_ratios):
    if not earnings or "annualEarnings" not in earnings:
        return [], []
    
    historical_eps = []
    pe_ratios = []
    years = []
    
    for record in earnings.get("annualEarnings", []):
        year = record["fiscalDateEnding"][:4]
        eps = float(record.get("reportedEPS", 0))
        pe_ratio = float(key_ratios.get("annualReports", [{}])[0].get("PERatio", 15))
        
        if eps > 0 and pe_ratio > 0:
            historical_eps.append(eps)
            pe_ratios.append(pe_ratio)
            years.append(year)
    
    if not historical_eps:
        return [], []
    
    fair_values = np.array(historical_eps) * np.array(pe_ratios)
    return list(reversed(years)), list(reversed(fair_values))

def get_annual_stock_prices(stock_prices):
    if not stock_prices or "Monthly Adjusted Time Series" not in stock_prices:
        return [], []
    
    historical_prices = {}
    for date, data in stock_prices["Monthly Adjusted Time Series"].items():
        year = date[:4]
        month = date[5:7]
        if month == "12":
            historical_prices[year] = float(data.get("4. close", 0))
    
    sorted_years = sorted(historical_prices.keys())
    sorted_prices = [historical_prices[year] for year in sorted_years]
    return sorted_years, sorted_prices

def discounted_cash_flow(earnings, wacc=0.10, terminal_growth=0.03, projection_years=5):
    if not earnings or "annualEarnings" not in earnings:
        return 0, [], [], 0
    
    latest_eps = float(earnings["annualEarnings"][0].get("reportedEPS", 0))
    if latest_eps == 0:
        return 0, [], [], 0
    
    eps_growth = 0.05
    discount_factors = [(1 / (1 + wacc)) ** i for i in range(1, projection_years + 1)]
    projected_eps = [latest_eps * (1 + eps_growth) ** i for i in range(1, projection_years + 1)]
    discounted_values = np.array(projected_eps) * discount_factors
    terminal_value = (projected_eps[-1] * (1 + terminal_growth)) / (wacc - terminal_growth)
    discounted_terminal = terminal_value * discount_factors[-1]
    intrinsic_value = sum(discounted_values) + discounted_terminal
    return intrinsic_value, projected_eps, discount_factors, terminal_value

st.title("Stock Valuation App")

stock_ticker = st.text_input("Enter Stock Ticker:")
if stock_ticker:
    overview, income_statement, balance_sheet, cash_flow, earnings, key_ratios, stock_prices = fetch_financials(stock_ticker)
    
    years, fair_values = calculate_fair_value(earnings, key_ratios)
    stock_years, stock_prices = get_annual_stock_prices(stock_prices)
    intrinsic_value, projected_eps, discount_factors, terminal_value = discounted_cash_flow(earnings)
    
    st.subheader("Stock Price vs Fair Value Estimate")
    if stock_years and stock_prices and years and fair_values:
        fig, ax = plt.subplots()
        ax.plot(stock_years, stock_prices, label="Stock Price", marker="o", linestyle="-")
        ax.plot(years, fair_values, label="Fair Value Estimate", marker="s", linestyle="--")
        ax.set_xlabel("Year")
        ax.set_ylabel("Price")
        ax.legend()
        plt.xticks(rotation=45)
        st.pyplot(fig)
    else:
        st.write("Insufficient stock price or fair value data to generate chart.")
    
    st.subheader("Discounted Cash Flow Valuation")
    if intrinsic_value:
        st.write(f"Estimated Intrinsic Value per Share: ${intrinsic_value:.2f}")
    else:
        st.write("Insufficient data available for DCF valuation.")
    
    with st.expander("View API Responses for Debugging"):
        st.write("### Earnings Data")
        st.json(earnings)
        st.write("### Stock Price Data")
        st.json(stock_prices)
    
    with st.expander("View Company Overview"):
        st.write(overview)
    
    with st.expander("View Financial Statements"):
        st.write("### Income Statement")
        st.write(income_statement)
        
        st.write("### Balance Sheet")
        st.write(balance_sheet)
        
        st.write("### Cash Flow Statement")
        st.write(cash_flow)
    
    with st.expander("View Key Ratios and Valuations"):
        st.write(key_ratios)
