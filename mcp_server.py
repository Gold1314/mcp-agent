import yfinance as yf
from fastmcp import FastMCP
import os
import openai
from dotenv import load_dotenv
load_dotenv()

mcp = FastMCP("stocks")

@mcp.tool()
def fetch_stock_info(symbol: str) -> dict:
    """Get Company's general information."""
    stock = yf.Ticker(symbol)
    return stock.info

@mcp.tool()
def fetch_price_history(symbol: str, period: str = "1y", interval: str = "1mo") -> dict:
    stock = yf.Ticker(symbol)
    hist = stock.history(period=period, interval=interval)
    return hist.reset_index().to_dict(orient="list")

@mcp.tool()
def fetch_quarterly_financials(symbol: str) -> dict:
    """Get stock quarterly financials."""
    stock = yf.Ticker(symbol)
    return stock.quarterly_financials.to_dict()

@mcp.tool()
def fetch_annual_financials(symbol: str) -> dict:
    """Get stock annual financials."""
    stock = yf.Ticker(symbol)
    return stock.financials.T.to_dict()

@mcp.tool()
def fetch_balance_sheet(symbol: str) -> dict:
    stock = yf.Ticker(symbol)
    return stock.balance_sheet.T.to_dict()

@mcp.tool()
def fetch_cash_flow(symbol: str) -> dict:
    stock = yf.Ticker(symbol)
    return stock.cashflow.T.to_dict()

@mcp.tool()
def get_recommendation(symbol: str) -> dict:
    """Get Buy/Hold/Sell recommendation using LLM."""
    import json
    import re
    # Fetch stock info and annual financials
    stock = yf.Ticker(symbol)
    info = stock.info
    annual = stock.financials.T.to_dict()
    # Select only key fields for the prompt
    key_info = {
        "symbol": info.get("symbol"),
        "longName": info.get("longName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "currentPrice": info.get("currentPrice"),
        "marketCap": info.get("marketCap"),
        "trailingPE": info.get("trailingPE"),
        "revenueGrowth": info.get("revenueGrowth"),
        "dividendYield": info.get("dividendYield"),
        "beta": info.get("beta"),
        "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh"),
        "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow"),
    }
    # For annual, just send a few key metrics for the last 3 years
    annual_summary = {}
    for metric in ["Total Revenue", "Net Income"]:
        if metric in annual:
            years = list(annual[metric].keys())[-3:]
            # Convert keys to strings to avoid serialization errors
            annual_summary[metric] = {str(k): annual[metric][k] for k in years}
    prompt = f"""
    You are a financial analyst. Given the following key stock information and annual financials, provide:
    1. A one-word recommendation (Buy, Hold, or Sell)
    2. A detailed analysis explaining your reasoning, including:
       - Key financial metrics and their implications
       - Growth trends and market position
       - Risk factors and market conditions
       - Competitive advantages or disadvantages
    
    Stock Info: {json.dumps(key_info)}
    Annual Financials (last 3 years): {json.dumps(annual_summary)}
    
    Format your response as a JSON object with these fields:
    {{
        "recommendation": "Buy/Hold/Sell",
        "icon": "🟢/🟡/🔴",
        "reason": "One sentence summary",
        "detailed_analysis": "A Markdown-formatted bullet list, with each key point on a new line. Use bold for key numbers and italics for highlights."
    }}
    Respond with only the JSON object, and nothing else.
    """
    # Call OpenAI (new API)
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        return {"error": "OPENAI_API_KEY not set in environment."}
    
    try:
        client = openai.OpenAI(api_key=openai_api_key)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        result = response.choices[0].message.content
        # Parse the JSON response
        try:
            parsed = json.loads(result)
            return parsed
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract recommendation and reason
            match = re.search(r'"(Buy|Hold|Sell)"\s*-\s*([^"]+)', result)
            if match:
                rec, reason = match.groups()
                icon = "🟢" if rec == "Buy" else "🟡" if rec == "Hold" else "🔴"
                return {
                    "recommendation": rec,
                    "icon": icon,
                    "reason": reason.strip(),
                    "detailed_analysis": "Detailed analysis not available."
                }
            return {"error": "Could not parse recommendation from response."}
    except Exception as e:
        return {"error": f"Error getting recommendation: {str(e)}"}

if __name__ == "__main__":
    mcp.run(transport="stdio")