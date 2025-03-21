import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
from openai import OpenAI

st.set_page_config(layout="wide")

# -------- Alpha Vantage API Call for EPS and Stock Prices -------- #
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

def fetch_eps_and_prices(ticker):
    st.write("Fetching EPS and Stock Price Data...")

    earnings = get_alpha_vantage_data(ticker, "EARNINGS")
    stock_prices = get_alpha_vantage_data(ticker, "TIME_SERIES_MONTHLY_ADJUSTED")

    if not earnings or not stock_prices:
        st.warning("Some data could not be retrieved. Please verify the ticker or API status.")
    
    return earnings, stock_prices

# --------- Transform and Fair Value Calculation --------- #
def prepare_fair_value_data(earnings, stock_prices):
    if "annualEarnings" not in earnings or "Monthly Adjusted Time Series" not in stock_prices:
        return pd.DataFrame()

    # EPS Data
    eps_df = pd.DataFrame(earnings['annualEarnings'])
    eps_df['Year'] = pd.to_datetime(eps_df['fiscalDateEnding']).dt.year
    eps_df['reportedEPS'] = pd.to_numeric(eps_df['reportedEPS'], errors='coerce')
    eps_df = eps_df.dropna().sort_values('Year')

    # Stock Price Data (end of year close)
    price_df = pd.DataFrame(stock_prices['Monthly Adjusted Time Series']).T
    price_df.index = pd.to_datetime(price_df.index)
    price_df['adjusted_close'] = pd.to_numeric(price_df['5. adjusted close'], errors='coerce')
    price_df['Year'] = price_df.index.year
    price_df = price_df.groupby('Year').last().reset_index()[['Year', 'adjusted_close']]

    # Merge on Year
    merged_df = pd.merge(eps_df, price_df, on='Year', how='inner')

    # Calculate P/E
    merged_df['pe_ratio'] = merged_df['adjusted_close'] / merged_df['reportedEPS']

    return merged_df

# --------- OpenAI GPT-4o Summary Function -------- #
def get_company_growth_initiatives_openai(ticker):
    client = OpenAI(api_key=st.secrets["openai"]["api_key"])
    prompt = f"Research and summarize the stated growth initiatives and timeline for the company associated with the stock ticker {ticker}. Keep it concise and in bullet points if possible."

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful financial analyst."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Failed to fetch growth initiatives: {e}")
        return "Could not fetch growth initiatives."


# --------- Streamlit App Layout --------- #
st.title("Stock Valuation App (EPS & Price Focused)")

stock_ticker = st.text_input("Enter Stock Ticker (e.g., AAPL, MSFT):")

if stock_ticker:
    earnings, stock_prices = fetch_eps_and_prices(stock_ticker)
    fair_value_df = prepare_fair_value_data(earnings, stock_prices)

    if not fair_value_df.empty:
        st.subheader("Fair Value Estimation Settings")

        # --------- P/E Multiple Options --------- #
        pe_option = st.selectbox(
            "Choose P/E Multiple Option:",
            ["Average of All Years", "Average of Last 3 Years", "Average of Last 5 Years", "Average of Last 10 Years", "Custom P/E Multiple"]
        )

        # Default Average
        default_avg_pe = fair_value_df['pe_ratio'].mean()

        # Last X years average
        if pe_option == "Average of Last 3 Years":
            avg_pe = fair_value_df.tail(3)['pe_ratio'].mean()
        elif pe_option == "Average of Last 5 Years":
            avg_pe = fair_value_df.tail(5)['pe_ratio'].mean()
        elif pe_option == "Average of Last 10 Years":
            avg_pe = fair_value_df.tail(10)['pe_ratio'].mean()
        elif pe_option == "Custom P/E Multiple":
            avg_pe = st.number_input("Enter Custom P/E Multiple:", min_value=0.0, value=default_avg_pe, step=1.0)
        else:  # Average of All Years
            avg_pe = default_avg_pe

        # --------- Y-Axis Scale Option --------- #
        y_axis_type = st.radio("Select Y-Axis Scale:", ["Linear", "Logarithmic"], index=0)

        # Calculate Fair Value
        fair_value_df['fair_value'] = fair_value_df['reportedEPS'] * avg_pe

        # --------- Plot --------- #
        st.subheader("Stock Price vs EPS-based Fair Value Estimate")
        st.write(f"**P/E Multiple Used:** {avg_pe:.2f}")

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(fair_value_df['Year'], fair_value_df['adjusted_close'], label='Actual Stock Price', marker='o')
        ax.plot(fair_value_df['Year'], fair_value_df['fair_value'], label='EPS-based Fair Value', marker='o')
        ax.set_xlabel('Year')
        ax.set_ylabel('Price (USD)')
        ax.set_title(f'{stock_ticker} Stock Price vs EPS-derived Fair Value')
        ax.legend()
        ax.grid(True)
        if y_axis_type == "Logarithmic":
            ax.set_yscale('log')
        st.pyplot(fig)

        # --------- Data Table --------- #
        st.subheader("EPS, Stock Price, P/E Ratio, and Fair Value Table")
        st.dataframe(fair_value_df[['Year', 'reportedEPS', 'adjusted_close', 'pe_ratio', 'fair_value']].rename(
            columns={
                'reportedEPS': 'EPS',
                'adjusted_close': 'Stock Price',
                'pe_ratio': 'P/E Ratio',
                'fair_value': 'Fair Value'
            }
        ).reset_index(drop=True))

    else:
        st.warning("Not enough data to calculate fair value.")

    # --------- Company Growth Initiatives --------- #
    st.subheader("Company Growth Initiatives and Timeline")
    with st.spinner("Fetching company growth initiatives using GPT-4o..."):
        growth_initiatives = get_company_growth_initiatives_openai(stock_ticker)
        st.write(growth_initiatives)