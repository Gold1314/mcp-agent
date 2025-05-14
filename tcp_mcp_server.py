import yfinance as yf
from fastmcp import FastMCP
import os
import openai
from dotenv import load_dotenv
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get port from environment variable or use default
port = int(os.environ.get('PORT', '5000'))
logger.info(f"Using port {port}")

# Initialize FastMCP
mcp = FastMCP("stocks")

@mcp.tool()
def fetch_stock_info(symbol: str) -> dict:
    """Get Company's general information."""
    try:
        logger.info(f"Fetching stock info for {symbol}")
        stock = yf.Ticker(symbol)
        info = stock.info
        if not info:
            logger.warning(f"No info found for {symbol}")
            return {}
        return info
    except Exception as e:
        logger.error(f"Error fetching stock info for {symbol}: {e}")
        return {}

@mcp.tool()
def fetch_price_history(symbol: str, period: str = "1y", interval: str = "1mo") -> dict:
    try:
        logger.info(f"Fetching price history for {symbol}")
        stock = yf.Ticker(symbol)
        hist = stock.history(period=period, interval=interval)
        if hist.empty:
            logger.warning(f"No price history found for {symbol}")
            return {}
        return hist.reset_index().to_dict(orient="list")
    except Exception as e:
        logger.error(f"Error fetching price history for {symbol}: {e}")
        return {}

@mcp.tool()
def fetch_quarterly_financials(symbol: str) -> dict:
    """Get stock quarterly financials."""
    try:
        logger.info(f"Fetching quarterly financials for {symbol}")
        stock = yf.Ticker(symbol)
        financials = stock.quarterly_financials
        if financials.empty:
            logger.warning(f"No quarterly financials found for {symbol}")
            return {}
        return financials.to_dict()
    except Exception as e:
        logger.error(f"Error fetching quarterly financials for {symbol}: {e}")
        return {}

@mcp.tool()
def fetch_annual_financials(symbol: str) -> dict:
    """Get stock annual financials."""
    try:
        logger.info(f"Fetching annual financials for {symbol}")
        stock = yf.Ticker(symbol)
        financials = stock.financials
        if financials.empty:
            logger.warning(f"No annual financials found for {symbol}")
            return {}
        return financials.T.to_dict()
    except Exception as e:
        logger.error(f"Error fetching annual financials for {symbol}: {e}")
        return {}

@mcp.tool()
def fetch_balance_sheet(symbol: str) -> dict:
    try:
        logger.info(f"Fetching balance sheet for {symbol}")
        stock = yf.Ticker(symbol)
        balance = stock.balance_sheet
        if balance.empty:
            logger.warning(f"No balance sheet found for {symbol}")
            return {}
        return balance.T.to_dict()
    except Exception as e:
        logger.error(f"Error fetching balance sheet for {symbol}: {e}")
        return {}

@mcp.tool()
def fetch_cash_flow(symbol: str) -> dict:
    try:
        logger.info(f"Fetching cash flow for {symbol}")
        stock = yf.Ticker(symbol)
        cashflow = stock.cashflow
        if cashflow.empty:
            logger.warning(f"No cash flow found for {symbol}")
            return {}
        return cashflow.T.to_dict()
    except Exception as e:
        logger.error(f"Error fetching cash flow for {symbol}: {e}")
        return {}

@mcp.tool()
def get_recommendation(symbol: str) -> dict:
    """Get Buy/Hold/Sell recommendation using LLM."""
    try:
        logger.info(f"Getting recommendation for {symbol}")
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
            logger.error("OPENAI_API_KEY not set in environment")
            return {"error": "OPENAI_API_KEY not set in environment."}
        
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
            logger.info(f"Successfully got recommendation for {symbol}")
            return parsed
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract recommendation and reason
            match = re.search(r'"(Buy|Hold|Sell)"\s*-\s*([^"]+)', result)
            if match:
                rec, reason = match.groups()
                icon = "🟢" if rec == "Buy" else "🟡" if rec == "Hold" else "🔴"
                logger.warning(f"JSON parsing failed for {symbol}, extracted recommendation manually")
                return {
                    "recommendation": rec,
                    "icon": icon,
                    "reason": reason.strip(),
                    "detailed_analysis": "Detailed analysis not available."
                }
            logger.error(f"Could not parse recommendation for {symbol}")
            return {"error": "Could not parse recommendation from response."}
    except Exception as e:
        logger.error(f"Error getting recommendation for {symbol}: {e}")
        return {"error": f"Error getting recommendation: {str(e)}"}

if __name__ == "__main__":
    try:
        logger.info("Starting MCP server...")
        mcp.run(host="0.0.0.0", port=port)
    except Exception as e:
        logger.error(f"Error running MCP server: {e}")
        sys.exit(1)