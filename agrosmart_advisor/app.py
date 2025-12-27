import os
import json
import requests
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, session
from functools import lru_cache
import time
market_cache = {
    "data": None,
    "timestamp": 0
}
CACHE_TTL = 1800  # 30 minutes

app = Flask(__name__)
with open("crops_data.json", "r", encoding="utf-8") as f:
    crops_data = json.load(f)
# Config
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
app.permanent_session_lifetime = timedelta(days=7)
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "").strip()

# ---------------- UTIL ---------------- #
def fetch_weather(city, country_code):
    """Fetch weather data from OpenWeather API"""
    if not OPENWEATHER_API_KEY:
        # Return safe defaults if API key is missing
        return {
            "temperature": 25,
            "humidity": 60,
            "soil": 50,
            "uv_index": 6,
            "description": "Weather data unavailable"
        }
    
    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": f"{city},{country_code}",
            "appid": OPENWEATHER_API_KEY,
            "units": "metric"
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return {
            "temperature": data.get("main", {}).get("temp", 25),
            "humidity": data.get("main", {}).get("humidity", 60),
            "soil": 50,  # Placeholder - would need separate API
            "uv_index": 6,  # Placeholder - would need separate API
            "description": data.get("weather", [{}])[0].get("description", "")
        }
    except Exception as e:
        print(f"❌ Weather API failed: {e}")
        return {
            "temperature": 25,
            "humidity": 60,
            "soil": 50,
            "uv_index": 6,
            "description": "Weather data unavailable"
        }

def recommend_crops(weather):
    """Recommend crops based on weather conditions"""
    temp = weather.get("temperature", 25)
    humidity = weather.get("humidity", 60)
    
    # Simple recommendation logic
    recommendations = []
    if temp > 20 and humidity > 50:
        recommendations.append("Tomato")
    if temp > 15 and humidity > 40:
        recommendations.append("Wheat")
    if temp > 25 and humidity > 60:
        recommendations.append("Rice")
    
    return recommendations if recommendations else ["Wheat", "Rice"]

def get_market_prices():
    API_KEY = os.getenv("AGMARKNET_API_KEY", "").strip()
    if not API_KEY:
        print("❌ Missing Agmarknet API key")
        return []

    url = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"

    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": 10,
        "offset": 0,
        "filters[commodity]": "Tomato"
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        records = data.get("records", [])
        if not records:
            print("⚠️ Agmarknet returned EMPTY records")
            return []

        prices = []
        for record in records:
            modal = record.get("modal_price")
            prices.append({
                "commodity": record.get("commodity", "N/A"),
                "market": record.get("market", "N/A"),
                "state": record.get("state", "N/A"),
                "price": f"₹{modal}/quintal" if modal else "N/A",
                "trend": "↗" if modal and int(modal) > 2000 else "→"
            })

        return prices

    except Exception as e:
        print("❌ Agmarknet API error:", e)
        return []


def cached_market_prices():
    """Fetch market prices with caching"""
    current_time = time.time()
    
    if market_cache["data"] and (current_time - market_cache["timestamp"]) < CACHE_TTL:
        return market_cache["data"]
    
    try:
        prices = get_market_prices()
        market_cache["data"] = prices
        market_cache["timestamp"] = current_time
        return prices
    except Exception as e:
        print(f"❌ Market API failed: {e}")
        return [{"commodity": "Tomato", "market": "Delhi", "state": "Delhi", "price": "₹2500/quintal", "trend": "→"}]


# ---------------- ROUTES ---------------- #
@app.route("/")
def language():
    return render_template("language.html")

@app.route("/set-language", methods=["POST"])
def set_language():
    lang = request.form.get("language", "en")
    session["language"] = lang
    return redirect(url_for("register"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        session["name"] = request.form.get("name", "Farmer")
        return redirect(url_for("permissions"))
    return render_template("register.html")

@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/permissions", methods=["GET", "POST"])
def permissions():
    if request.method == "POST":
        session["permissions_granted"] = True
        return redirect(url_for("home"))
    return render_template("permissions.html")

@app.route("/home", methods=["GET", "POST"])
def home():
    weather = fetch_weather("Delhi", "IN")

    # Ensure safe defaults
    weather.setdefault("temperature", 25)
    weather.setdefault("humidity", 60)
    weather.setdefault("soil", 50)
    weather.setdefault("uv_index", 6)

    crops = recommend_crops(weather)
    return render_template("home.html", weather=weather, crops=crops)

@app.route("/crops")
def crops():
    return render_template("crops.html",crops=crops_data)

@app.route("/save-crop", methods=["POST"])

def save_crop():
    crop_name = request.form.get("crop")
    # Logic to save crop (to DB or session)
    # Demo: just return success
    return {"status": "success", "crop": crop_name}
@app.route("/Sell")
def Sell():
    return render_template("Sell.html")

@app.route("/market")
def market():
    now = time.time()

    # Use cache if valid
    if (
        market_cache["data"]
        and now - market_cache["timestamp"] < CACHE_TTL
    ):
        prices = market_cache["data"]
    else:
        prices = get_market_prices()
        if prices:  # only cache VALID data
            market_cache["data"] = prices
            market_cache["timestamp"] = now
    print("Agmarknet API returned (first 3 records):")
    for rec in prices[:3]:
        print(rec)

    return render_template("market.html", prices=prices)

@app.route("/soil")
def soil():
    return render_template("soil.html")


@app.route("/help")
def help():
    return render_template("help.html")

@app.route("/buyhere")
def buyhere():
    return render_template("buyhere.html")

@app.route("/saved_crops")
def saved_crops():
    return render_template("saved_crops.html")
    
@app.route("/soil-detail/clay")
def soil_detail_clay():
    return render_template("soil-detail-clay.html")

@app.route("/soil-detail/sandy")
def soil_detail_sandy():
    return render_template("soil-detail-sandy.html")

@app.route("/soil-detail/loamy")
def soil_detail_loamy():
    return render_template("soil-detail-loamy.html")

@app.route("/soil-detail/silty")
def soil_detail_silty():
    return render_template("soil-detail-silty.html")

@app.route("/soil-detail/peaty")
def soil_detail_peaty():
    return render_template("soil-detail-peaty.html")

@app.route("/soil-detail/chalky")
def soil_detail_chalky():
    return render_template("soil-detail-chalky.html")

@app.route("/soil-detail/red")
def soil_detail_red():
    return render_template("soil-detail-red.html")
   
# Try to import OpenAI for AI-powered search
try:
    from openai import OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
    client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
except ImportError:
    client = None
    OPENAI_API_KEY = ""

@app.route("/search")
def search():
    query = request.args.get("q", "").strip().lower()
    results = []

    if query:
        if client:  # ✅ Case 1: OpenAI available
            try:
                response = client.responses.create(
                    model="gpt-4.1-mini",
                    input=f"You are an agriculture expert. Answer this:\n{query}"
                )
                results.append(response.output_text)
            except Exception as e:
                results.append(f"AI error: {str(e)}")

        else:  # ✅ Case 2: Fallback answers
            if "rice" in query:
                results.append("Rice grows best in clay soil with high water retention.")
                results.append("Current market price: ₹1900/quintal.")
            elif "wheat" in query:
                results.append("Wheat prefers loamy soil with moderate moisture.")
                results.append("Current market price: ₹2200/quintal.")
            elif "tomato" in query:
                results.append("Tomato grows well in sandy loam soil with good drainage.")
                results.append("Current market price: ₹2500/quintal.")
            else:
                results.append(f"Sorry, I don’t have data for '{query}' yet.")

    return render_template("search.html", query=query, results=results)

# ---------------- MAIN ---------------- #
if __name__ == "__main__":
    app.run(debug=True)