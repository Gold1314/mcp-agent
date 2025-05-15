import streamlit as st
import asyncio
import os
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
import json
import yfinance as yf
import plotly.graph_objects as go
import re
import logging
import subprocess

from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession
from mcp.client.sse import sse_client

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Set page config
st.set_page_config(
    page_title="Financial Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Get API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("OPENAI_API_KEY not found in environment variables")
    st.stop()

# Initialize OpenAI model
model = ChatOpenAI(model="gpt-4", api_key=api_key)

# Server parameters
MCP_SERVER_HOST = os.getenv("MCP_SERVER_HOST", "localhost")
MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "8081"))
MCP_SERVER_URL = f"http://{MCP_SERVER_HOST}:{MCP_SERVER_PORT}"  # Use root path

async def get_dashboard_data(symbol):
    try:
        logger.info(f"Connecting to MCP server for {symbol}")
        async with sse_client(MCP_SERVER_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_list = await load_mcp_tools(session)
                tools = {tool.name: tool for tool in tools_list}
                
                # Fetch data with error handling
                try:
                    stock_info = await tools["fetch_stock_info"].ainvoke({"symbol": symbol})
                    logger.info(f"Successfully fetched stock info for {symbol}")
                except Exception as e:
                    logger.error(f"Error fetching stock info: {e}")
                    stock_info = {}
                
                try:
                    price_history = await tools["fetch_price_history"].ainvoke({"symbol": symbol, "period": "1y", "interval": "1mo"})
                    logger.info(f"Successfully fetched price history for {symbol}")
                except Exception as e:
                    logger.error(f"Error fetching price history: {e}")
                    price_history = {}
                
                try:
                    quarterly = await tools["fetch_quarterly_financials"].ainvoke({"symbol": symbol})
                    logger.info(f"Successfully fetched quarterly financials for {symbol}")
                except Exception as e:
                    logger.error(f"Error fetching quarterly financials: {e}")
                    quarterly = {}
                
                return stock_info, price_history, quarterly
    except Exception as e:
        logger.error(f"Error in get_dashboard_data: {e}")
        raise

async def get_financials(symbol):
    async with sse_client(MCP_SERVER_URL) as session:
        await session.initialize()
        tools_list = await load_mcp_tools(session)
        tools = {tool.name: tool for tool in tools_list}
        annual = await tools["fetch_annual_financials"].ainvoke({"symbol": symbol})
        balance = await tools["fetch_balance_sheet"].ainvoke({"symbol": symbol})
        cashflow = await tools["fetch_cash_flow"].ainvoke({"symbol": symbol})
        # Parse if needed
        def parse_if_str(d):
            if isinstance(d, str):
                try:
                    d = json.loads(d)
                except Exception:
                    d = {}
            return d
        annual = parse_if_str(annual)
        balance = parse_if_str(balance)
        cashflow = parse_if_str(cashflow)
        return annual, balance, cashflow

st.title("Financial Dashboard")
symbol = st.text_input("Stock Symbol (e.g., AAPL, MSFT)", "AAPL").upper()

if st.button("Analyze"):
    with st.spinner("Fetching data..."):
        stock_info, price_history, quarterly = asyncio.run(get_dashboard_data(symbol))

        # Ensure stock_info is a dict (parse if string)
        if isinstance(stock_info, str):
            try:
                stock_info = json.loads(stock_info)
            except Exception:
                st.error(f"Error: Could not parse stock info. Received: {stock_info}")
                st.stop()

        if not isinstance(stock_info, dict):
            st.error(f"Error: Could not fetch stock info. Received: {stock_info}")
        else:
            def human_format(num):
                if num is None or num == 'N/A':
                    return 'N/A'
                num = float(num)
                magnitude = 0
                while abs(num) >= 1000:
                    magnitude += 1
                    num /= 1000.0
                return '%.2f%s' % (num, ['', 'K', 'M', 'B', 'T', 'P'][magnitude])

            # --- MCP-based Recommendation ---
            # Call the MCP tool for recommendation
            async def fetch_recommendation(symbol):
                async with sse_client(MCP_SERVER_URL) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        tools_list = await load_mcp_tools(session)
                        tools = {tool.name: tool for tool in tools_list}
                        return await tools["get_recommendation"].ainvoke({"symbol": symbol})
            rec_result = asyncio.run(fetch_recommendation(symbol))
            if isinstance(rec_result, str):
                try:
                    rec_result = json.loads(rec_result)
                except Exception:
                    st.error(f"Error: Could not parse recommendation result. Received: {rec_result}")
                    st.stop()
            if rec_result and not rec_result.get("error"):
                rec = rec_result.get("recommendation", "N/A")
                icon = rec_result.get("icon", "ℹ️")
                reason = rec_result.get("reason", "")
                detailed_analysis = rec_result.get("detailed_analysis", "")
            else:
                rec = 'N/A'
                icon = 'ℹ️'
                reason = rec_result.get("error", "Could not get recommendation.") if rec_result else "Could not get recommendation."
                detailed_analysis = ""

            # --- Top KPIs ---
            col_rec, col1, col2, col3, col4 = st.columns(5)
            col_rec.metric("Recommendation", rec.upper(), icon)
            col1.metric(
                "Current Price",
                f"${stock_info.get('currentPrice', 'N/A')}",
                f"{stock_info.get('regularMarketChange', 0):+.2f} ({stock_info.get('regularMarketChangePercent', 0):+.2f}%)"
            )
            col2.metric("Market Cap", human_format(stock_info.get('marketCap', 'N/A')))
            col3.metric("P/E Ratio", f"{stock_info.get('trailingPE', 'N/A')}")
            col4.metric("Dividend Yield", f"{stock_info.get('dividendYield', 'N/A')}")
            st.caption(f"{reason}")

            # --- Detailed Analysis ---
            def clean_analysis(text):
                # Remove double asterisks with no matching pair
                text = re.sub(r'\*{2,}', '', text)
                # Add space after numbers and before 'billion' or 'million'
                text = re.sub(r'(\d)(billion|million)', r'\1 \2', text)
                # Add space after commas if missing
                text = re.sub(r',([^\s])', r', \1', text)
                # Add space after 'to' if missing (for year ranges)
                text = re.sub(r'(\d{4})to(\d{4})', r'\1 to \2', text)
                # Add space after periods if missing
                text = re.sub(r'\.([A-Za-z])', r'. \1', text)
                # Remove stray underscores
                text = text.replace('_', ' ')
                return text

            if detailed_analysis:
                st.subheader("Analysis")
                st.markdown(clean_analysis(detailed_analysis))

            # --- Company Info and Key Metrics Side by Side ---
            col_info, col_metrics = st.columns([2, 2])

            with col_info:
                st.markdown(
                    f"""
                    <style>
                    .company-card-dark {{
                        background-color: #222;
                        color: #fff;
                        border-radius: 12px;
                        padding: 24px;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.10);
                        margin-bottom: 1rem;
                    }}
                    .company-card-dark h4 {{
                        margin-bottom: 0.5rem;
                        color: #fff;
                    }}
                    .company-card-dark .company-detail {{
                        color: #b0b0b0;
                        margin-bottom: 1rem;
                    }}
                    .company-card-dark a {{
                        color: #8ab4f8;
                    }}
                    </style>
                    <div class='company-card-dark'>
                        <h4>Company Information</h4>
                        <div class='company-detail'>Key details about {stock_info.get('longName', symbol)}.</div>
                        <div style='display: flex; align-items: center; margin-bottom: 1rem;'>
                            <img src="https://logo.clearbit.com/{stock_info.get('website','').replace('https://','').replace('http://','')}" alt="logo" style="height: 40px; margin-right: 12px; background: #fff; border-radius: 8px;" onerror="this.style.display='none'"/>
                            <div>
                                <b>{stock_info.get('longName', symbol)}</b><br/>
                                <span class='company-detail'>{stock_info.get('sector', '')} - {stock_info.get('industry', '')}</span>
                            </div>
                        </div>
                        <div style='margin-bottom: 0.5rem;'><b>🌐 Website</b><br/><a href="{stock_info.get('website','')}" target="_blank">{stock_info.get('website','')}</a></div>
                        <div style='margin-bottom: 0.5rem;'><b>🏢 Headquarters</b><br/>{stock_info.get('city','')}, {stock_info.get('state','')}, {stock_info.get('country','')}</div>
                        <div style='margin-bottom: 0.5rem;'><b>👥 Employees</b><br/>{stock_info.get('fullTimeEmployees','N/A')}</div>
                        <div style='margin-bottom: 0.5rem;'><b>📅 Founded</b><br/>{stock_info.get('companyOfficers', [{}])[0].get('startDate','N/A') if stock_info.get('companyOfficers') else 'N/A'}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with col_metrics:
                st.subheader("Key Metrics")
                metrics = {
                    "EPS": stock_info.get("trailingEps", "N/A"),
                    "Beta": stock_info.get("beta", "N/A"),
                    "52W High": stock_info.get("fiftyTwoWeekHigh", "N/A"),
                    "52W Low": stock_info.get("fiftyTwoWeekLow", "N/A"),
                    "Dividend": stock_info.get("dividendRate", "N/A"),
                    "Avg Volume": stock_info.get("averageVolume", "N/A")
                }
                st.table(metrics)

            # --- Stock Price History ---
            st.subheader("Stock Price History")
            st.markdown("12-month price movement with volume")

            # Try to parse if it's a string
            if isinstance(price_history, str):
                try:
                    price_history = json.loads(price_history)
                except Exception:
                    price_history = {}

            # Now check if it's a dict with lists
            if isinstance(price_history, dict) and price_history:
                df_hist = pd.DataFrame(price_history)
            else:
                df_hist = pd.DataFrame()  # empty DataFrame

            if not df_hist.empty and 'Date' in df_hist:
                df_hist['Date'] = df_hist['Date'].astype(str)
                df_hist['Date'] = pd.to_datetime(df_hist['Date'], errors='coerce', utc=True)
                df_hist = df_hist.dropna(subset=['Date'])
                df_hist = df_hist.sort_values('Date')
                df_hist = df_hist.tail(12)
                try:
                    df_hist['Month'] = df_hist['Date'].dt.strftime('%b %Y')
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=df_hist['Month'], y=df_hist['Close'],
                        mode='lines+markers', name='Stock Price ($)', line=dict(color='royalblue')
                    ))
                    fig.add_trace(go.Scatter(
                        x=df_hist['Month'], y=df_hist['Volume'],
                        mode='lines+markers', name='Volume', yaxis='y2', line=dict(color='seagreen')
                    ))
                    fig.update_layout(
                        xaxis_title="Month",
                        yaxis=dict(title="Stock Price ($)"),
                        yaxis2=dict(title="Volume", overlaying='y', side='right'),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        margin=dict(l=20, r=20, t=40, b=20)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.info("Could not display price history graph.")
            else:
                st.info("No price history data available.")

            # --- Quarterly Revenue & Profit and Company Information (Side by Side) ---
            st.subheader("Quarterly Revenue & Profit")
            st.caption("Last 4 quarters financial performance")
            
            col_chart, col_news = st.columns([2, 2])

            # Prepare quarterly data
            if isinstance(quarterly, str):
                try:
                    quarterly = json.loads(quarterly)
                except Exception:
                    st.info(f"Could not parse quarterly financials. Received: {quarterly}")
                    quarterly = {}

            if isinstance(quarterly, dict) and quarterly:
                df_quarterly = pd.DataFrame(quarterly)
            else:
                df_quarterly = pd.DataFrame()

            with col_chart:
                if not df_quarterly.empty:
                    # Use the last 4 columns (quarters)
                    last_quarters = df_quarterly.columns[-4:]
                    # Try to get revenue and profit rows
                    revenue_row = None
                    for key in ['Total Revenue', 'Normalized EBITDA', 'Revenue']:
                        if key in df_quarterly.index:
                            revenue_row = key
                            break
                    profit_row = None
                    for key in ['Net Income', 'Net Income From Continuing Operation Net Minority Interest', 'Profit']:
                        if key in df_quarterly.index:
                            profit_row = key
                            break
                    if revenue_row and profit_row:
                        # Prepare data for plotting
                        quarters = [pd.to_datetime(q).strftime('%b %Y') for q in last_quarters]
                        revenue = [df_quarterly.loc[revenue_row, q] / 1e9 if pd.notna(df_quarterly.loc[revenue_row, q]) else None for q in last_quarters]
                        profit = [df_quarterly.loc[profit_row, q] / 1e9 if pd.notna(df_quarterly.loc[profit_row, q]) else None for q in last_quarters]
                        # Only keep quarters where both revenue and profit are not None
                        filtered = [(q, r, p) for q, r, p in zip(quarters, revenue, profit) if r is not None and p is not None]
                        if not filtered:
                            st.info("No valid revenue and profit data for the last four quarters.")
                        else:
                            fq, fr, fp = zip(*filtered)
                            fig = go.Figure(data=[
                                go.Bar(name='Revenue ($B)', x=fq, y=fr, marker_color='rgb(66,133,244)'),
                                go.Bar(name='Profit ($B)', x=fq, y=fp, marker_color='rgb(52,168,83)')
                            ])
                            fig.update_layout(
                                barmode='group',
                                yaxis_title=None,
                                xaxis_title=None,
                                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                margin=dict(l=20, r=20, t=40, b=20),
                                height=300
                            )
                            st.plotly_chart(fig, use_container_width=True)
                            # Warn if the latest quarter is missing data
                            if None in (revenue[-1], profit[-1]):
                                st.warning("Latest quarter data may be incomplete or missing.")
                    else:
                        st.info("Could not find revenue or profit data in quarterly financials.")
                else:
                    st.info("No quarterly financial data available.")

            with col_news:
                def fetch_yf_news(symbol):
                    try:
                        stock = yf.Ticker(symbol)
                        news = getattr(stock, 'news', None)
                        if news and isinstance(news, list):
                            return news[:15]
                        return []
                    except Exception as e:
                        logger.error(f"Error fetching news for {symbol}: {e}")
                        return []

                news_articles = fetch_yf_news(symbol)

                news_html = (
                    "<style>"
                    ".news-card-white {{"
                    "background-color: #fff; color: #222; border-radius: 12px; padding: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.10); margin-bottom: 1rem; max-height: 400px; min-height: 400px; overflow-y: auto; display: flex; flex-direction: column; }}"
                    ".news-header {{ font-size: 1.5rem; font-weight: bold; margin-bottom: 0.2rem; color: #222; }}"
                    ".news-caption {{ color: #888; font-size: 1rem; margin-bottom: 1.2rem; }}"
                    ".news-item-block {{ display: flex; align-items: flex-start; margin-bottom: 1.2rem; }}"
                    ".news-item-time {{ min-width: 60px; color: #888; font-size: 0.95em; margin-right: 12px; margin-top: 2px; }}"
                    ".news-item-content {{ flex: 1; }}"
                    ".news-item-title {{ font-weight: bold; color: #222; margin-bottom: 0.2rem; font-size: 1.08rem; line-height: 1.2; }}"
                    ".news-item-title a {{ color: #222; text-decoration: none; }}"
                    ".news-item-title a:hover {{ text-decoration: underline; }}"
                    ".news-item-meta {{ color: #888; font-size: 0.95em; margin-bottom: 0.2rem; display: flex; align-items: center; gap: 0.5em; }}"
                    ".news-item-summary {{ margin-bottom: 0.2rem; color: #222; font-size: 1em; }}"
                    "hr.news-hr {{ border: 0; border-top: 1px solid #eee; margin: 0.5rem 0; }}"
                    "</style>"
                    '<div class="news-card-white">'
                    '<div class="news-header">Latest News <span style="font-size:0.9rem; color:#888; font-weight:normal;">(Eastern Time Zone)</span></div>'
                    '<div class="news-caption">Recent news and updates about {}.</div>'
                ).format(stock_info.get('shortName', symbol))

                if news_articles:
                    for article in news_articles:
                        content = article.get('content', {})
                        title = content.get('title', 'No Title')
                        link = (
                            content.get('canonicalUrl', {}).get('url') or
                            content.get('clickThroughUrl', {}).get('url') or
                            '#'
                        )
                        pub_time = ''
                        if 'pubDate' in content:
                            try:
                                pub_time = pd.to_datetime(content['pubDate']).strftime('%I:%M %p')
                            except Exception:
                                pub_time = pd.to_datetime(content['pubDate']).strftime('%b %d, %Y')
                        publisher = content.get('provider', {}).get('displayName', '')
                        summary = content.get('summary', '') or content.get('description', '')
                        news_html += (
                            '<div class="news-item-block">'
                            f'<div class="news-item-time">{pub_time}</div>'
                            '<div class="news-item-content">'
                            f'<div class="news-item-title"><a href="{link}" target="_blank">{title}</a></div>'
                            f'<div class="news-item-meta">{publisher}</div>'
                            + (f'<div class="news-item-summary">{summary}</div>' if summary else '') +
                            '</div>'
                            '</div>'
                            '<hr class="news-hr"/>'
                        )
                else:
                    news_html += '<div class="news-item-summary">No recent news found.</div>'

                news_html += '</div>'

                st.markdown(news_html, unsafe_allow_html=True)

            # --- Financial Statements ---
            st.subheader("Financial Statements")
            tabs = st.tabs(["Income Statement", "Balance Sheet", "Cash Flow"])

            # Fetch all financials
            annual, balance, cashflow = asyncio.run(get_financials(symbol))

            def build_fin_table(data, metrics, display_names):
                years = []
                rows = []
                for i, key in enumerate(metrics):
                    if key in data:
                        values = data[key]
                        # Skip if values is not a dict (could be a string or None)
                        if not isinstance(values, dict):
                            continue
                        if not years:
                            years = list(values.keys())
                        row = [display_names[i]] + [values.get(year, None) for year in years]
                        rows.append(row)
                df = pd.DataFrame(rows, columns=["Metric"] + years)
                # Only keep the last 3 years (most recent)
                if len(years) > 3:
                    last_years = sorted(years, reverse=True)[:3]
                    last_years = sorted(last_years)  # ascending order
                    df = df[["Metric"] + last_years]
                else:
                    last_years = years
                # Format as billions
                def format_billions(x):
                    if pd.isna(x) or x is None:
                        return ""
                    return f"${x/1e9:.2f}"
                for year in last_years:
                    df[year] = df[year].apply(format_billions)
                # Rename columns: if column looks like a date, use only the year
                new_cols = ["Metric"] + [str(pd.to_datetime(col).year) if col != "Metric" else col for col in df.columns[1:]]
                df.columns = ["Metric"] + new_cols[1:]
                # Add YoY (%) column
                def calc_yoy(row):
                    try:
                        vals = [float(str(row[year]).replace('$','').replace(',','')) for year in new_cols[1:]]
                        if len(vals) >= 2 and vals[-2] != 0:
                            pct = (vals[-1] - vals[-2]) / abs(vals[-2]) * 100
                            return f"{pct:+.1f}%"
                    except Exception:
                        return ""
                    return ""
                df["YoY (%)"] = df.apply(calc_yoy, axis=1)
                return df

            # Income Statement
            income_metrics = [
                "Total Revenue", "Gross Profit", "Operating Income", "Net Income", "Diluted EPS"
            ]
            income_names = [
                "Revenue", "Gross Profit", "Operating Income", "Net Income", "EPS (Diluted)"
            ]
            with tabs[0]:
                df_income = build_fin_table(annual, income_metrics, income_names)
                st.dataframe(df_income, use_container_width=True, hide_index=True)

            # Balance Sheet
            balance_metrics = [
                "Total Assets", "Total Liab", "Total Stockholder Equity", "Cash And Cash Equivalents", "Short Term Investments"
            ]
            balance_names = [
                "Total Assets", "Total Liabilities", "Shareholder Equity", "Cash & Equivalents", "Short Term Investments"
            ]
            with tabs[1]:
                df_balance = build_fin_table(balance, balance_metrics, balance_names)
                st.dataframe(df_balance, use_container_width=True, hide_index=True)

            # Cash Flow
            cashflow_metrics = [
                "Total Cash From Operating Activities", "Capital Expenditures", "Free Cash Flow", "Total Cashflows From Investing Activities", "Total Cash From Financing Activities"
            ]
            cashflow_names = [
                "Operating Cash Flow", "Capital Expenditures", "Free Cash Flow", "Investing Cash Flow", "Financing Cash Flow"
            ]
            with tabs[2]:
                df_cash = build_fin_table(cashflow, cashflow_metrics, cashflow_names)
                st.dataframe(df_cash, use_container_width=True, hide_index=True)