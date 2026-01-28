import os
import json
import requests
from langdetect import detect
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from functools import lru_cache
import time
market_cache = {
    "data": None,
    "timestamp": 0
}
CACHE_TTL = 1800  # 30 minutes

app = Flask(__name__)
def check_api_keys():
    # OpenWeather API check
    url_weather = f"https://api.openweathermap.org/data/2.5/weather?q=Delhi,IN&appid={OPENWEATHER_API_KEY}"
    try:
        resp = requests.get(url_weather)
        if resp.status_code == 200:
            print("✅ OpenWeather API key is active")
        else:
            print("⚠️ OpenWeather API key may be invalid:", resp.status_code)
    except Exception as e:
        print("❌ OpenWeather API check error:", e)
    
    # Data.gov.in API check
    url_market = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
    params = {"api-key": "579b464db66ec23bdd000001fa339be4d4ad4e6e58121ff0b90f90b5", "format": "json", "limit": 1}
    try:
        resp = requests.get(url_market, params=params)
        if resp.status_code == 200:
            print("✅ Data.gov.in API key is active")
        else:
            print("⚠️ Data.gov.in API key may be invalid:", resp.status_code)
    except Exception as e:
        print("❌ Data.gov.in API check error:", e)

with open("crops_data.json", "r", encoding="utf-8") as f:
    crops_data = json.load(f)

@app.before_request
def run_api_checks():
    check_api_keys()

# Config
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
app.permanent_session_lifetime = timedelta(days=7)
OPENWEATHER_API_KEY = "37971beaff2dab9d027dc668d31e42be"

# ---------------- UTIL ---------------- #
import requests

API_KEY = "37971beaff2dab9d027dc668d31e42be"

def fetch_weather(city, country):
    print("Fetching weather for:", city, country)

    try:
        url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={city},{country}&appid={API_KEY}&units=metric"

        )

        response = requests.get(url)
        data = response.json()

        if data.get("cod") != 200:
            print("Weather API error:", data)
            return None

        return {
            "temperature": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "description": data["weather"][0]["description"],
            "city": data["name"]
        }

    except Exception as e:
        print("Weather fetch failed:", e)
        return None



def recommend_crops(weather):
    temp = weather.get("temperature", 25)

    crops = []

    if temp > 30:
        crops = ["Rice", "Sugarcane", "Banana"]
    elif temp > 20:
        crops = ["Wheat", "Tomato"]
    else:
        crops = ["Potato", "Peas"]

    return crops

def get_market_prices():
    API_KEY = os.getenv("AGMARK_API_KEY", "579b464db66ec23bdd000001fa339be4d4ad4e6e58121ff0b90f90b5").strip()
    if not API_KEY:
        print("❌ Missing Agmarknet API key")
        return []

    url = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"

    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": 20,
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
    
@app.route("/api/market")
def market_api():
    return jsonify(get_market_prices())


# ---------------- LANGUAGE NLP ---------------- #

def detect_language_from_text(text):
    try:
       from openai import OpenAI
       OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
       client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
    
    except ImportError:
        return "en"

    
 

def translate_text(text, target_lang):
    if not client or target_lang == "en":
        return text  # fallback safely

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=f"Translate this to {target_lang}:\n{text}"
        )
        return response.output_text.strip()
    except Exception as e:
        print("❌ Translation error:", e)
        return text



# ---------------- ROUTES ---------------- #

@app.route("/")
def splash():
    return render_template("splash.html")


@app.before_request
def auto_detect_language():
    if "language" not in session:
        browser_lang = request.accept_languages.best_match(
            ["en", "hi", "te", "ta", "mr", "kn"]
        )
        session["language"] = browser_lang or "en"

@app.route("/language")
def language():
    return render_template("language.html")

@app.route("/set-language", methods=["POST"])
def set_language():
    user_text = request.form.get("sample_text", "")
    
    if user_text.strip():
        detected_lang = detect_language_from_text(user_text)
        session["language"] = detected_lang
    else:
        session["language"] = request.form.get("language", "en")

    return redirect(url_for("register"))

@app.context_processor
def inject_language():
    return dict(lang=session.get("language", "en"))

@app.context_processor
def inject_helpers():
    return dict(
        translate=lambda text: translate_text(
            text,
            session.get("language", "en")
        )
    )

#--------------- ROUTES ---------------- #

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        session["name"] = request.form.get("name")
        session["city"] = request.form.get("city")
        session["country"] = request.form.get("country", "IN")

        print("✅ Registered:", session["city"], session["country"])

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
    if request.method == "POST":
        session["city"] = request.form.get("city")
        session["country"] = request.form.get("country")

    city = session.get("city", "Delhi")
    country = session.get("country", "IN")

    weather = fetch_weather(city, country)

    # 🚨 SAFETY DEFAULTS
    if weather is None:
        weather = {
            "temperature": 25,
            "humidity": 60,
            "description": "clear sky",
            "city": city
        }

    crops = recommend_crops(weather)

    return render_template("home.html", weather=weather, crops=crops)

@app.route("/saved_crops")
def saved_crops():
    return render_template("saved_crops.html")


@app.route("/crops")
def crops():
    return render_template("crops.html",crops=crops_data)

@app.route("/Sell")
def Sell():
    return render_template("Sell.html")


@app.route("/market")
def market():
    return render_template("market.html")

def get_market_prices():
    now = time.time()

    # ✅ 1. Return cached data (NO API HIT)
    if market_cache["data"] and now - market_cache["timestamp"] < CACHE_TTL:
        print("Using cached market data")
        return market_cache["data"]

    API_KEY = "579b464db66ec23bdd000001fa339be4d4ad4e6e58121ff0b90f90b5"

    url = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": 20
    }

    try:
        response = requests.get(url, params=params, timeout=10)

        # ✅ Handle rate limit safely
        if response.status_code == 429:
            print("Rate limit hit, using cached data")
            return market_cache["data"] or []

        response.raise_for_status()
        data = response.json()

        records = data.get("records", [])
        prices = []

        for r in records:
            prices.append({
                "commodity": r.get("commodity"),
                "market": r.get("market"),
                "state": r.get("state"),
                "price": f"₹{r.get('modal_price')} / quintal"
            })

        # ✅ Save in cache
        market_cache["data"] = prices
        market_cache["timestamp"] = now

        return prices

    except Exception as e:
        print("Market API Error:", e)
        return market_cache["data"] or []

       

@app.route("/soil")
def soil():
    return render_template("soil.html")


@app.route("/help")
def help():
    return render_template("help.html")

@app.route("/buyhere")
def buyhere():
    return render_template("buyhere.html")


    
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
