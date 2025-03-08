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
    return response.json()

def fetch_financials(ticker):
    overview = get_alpha_vantage_data(ticker, "OVERVIEW")
    income_statement = get_alpha_vantage_data(ticker, "INCOME_STATEMENT")
    balance_sheet = get_alpha_vantage_data(ticker, "BALANCE_SHEET")
    cash_flow = get_alpha_vantage_data(ticker, "CASH_FLOW")
    earnings = get_alpha_vantage_data(ticker, "EARNINGS")
    return overview, income_statement, balance_sheet, cash_flow, earnings

def calculate_fair_value(earnings):
    historical_eps = []
    pe_ratios = []
    years = []
    
    for record in earnings.get("annualEarnings", []):
        year = record["fiscalDateEnding"][:4]
        eps = float(record["reportedEPS"])
        
        if eps > 0:  # Avoid division errors
            historical_eps.append(eps)
            years.append(year)
    
    # Dummy P/E ratios for now; would be replaced with actual fetched P/E values
    avg_pe_ratios = np.random.uniform(10, 20, len(historical_eps))
    fair_values = np.array(historical_eps) * avg_pe_ratios
    
    return years, fair_values, historical_eps

def discounted_cash_flow(earnings, wacc=0.10, terminal_growth=0.03, projection_years=5):
    latest_eps = float(earnings["annualEarnings"][0]["reportedEPS"])
    eps_growth = 0.05  # Assuming 5% annual EPS growth
    discount_factors = [(1 / (1 + wacc)) ** i for i in range(1, projection_years + 1)]
    projected_eps = [latest_eps * (1 + eps_growth) ** i for i in range(1, projection_years + 1)]
    discounted_values = np.array(projected_eps) * discount_factors
    terminal_value = (projected_eps[-1] * (1 + terminal_growth)) / (wacc - terminal_growth)
    discounted_terminal = terminal_value * discount_factors[-1]
    intrinsic_value = sum(discounted_values) + discounted_terminal
    return intrinsic_value

st.title("Stock Valuation App")

stock_ticker = st.text_input("Enter Stock Ticker:")
if stock_ticker:
    overview, income_statement, balance_sheet, cash_flow, earnings = fetch_financials(stock_ticker)
    
    st.subheader("Company Overview")
    st.write(overview)
    
    st.subheader("Financial Statements")
    st.write("Income Statement:", income_statement)
    st.write("Balance Sheet:", balance_sheet)
    st.write("Cash Flow Statement:", cash_flow)
    
    years, fair_values, historical_eps = calculate_fair_value(earnings)
    intrinsic_value = discounted_cash_flow(earnings)
    
    st.subheader("Stock Price vs Fair Value")
    fig, ax = plt.subplots()
    ax.plot(years, historical_eps, label="EPS", marker="o")
    ax.plot(years, fair_values, label="Fair Value Estimate", marker="s")
    ax.set_xlabel("Year")
    ax.set_ylabel("Price")
    ax.legend()
    st.pyplot(fig)
    
    st.subheader("Discounted Cash Flow Valuation")
    st.write(f"Estimated Intrinsic Value per Share: ${intrinsic_value:.2f}")