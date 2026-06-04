import pandas as pd
from database import save_weather, get_cached_weather
import streamlit as st
import requests
import math
import random
from datetime import datetime, timedelta, timezone
import config
from dashboard import show_dashboard

# ══════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════
st.set_page_config(
    page_title="Weather",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

with st.sidebar:
    st.markdown("""
    <h2 style='color:white;text-align:center;'>
    🌤 WeatherIQ
    </h2>
    <p style='text-align:center;color:#9db4d6;'>
    Real-Time Weather Analytics
    </p>
    """, unsafe_allow_html=True)
    st.markdown("---")
    page = st.radio("", ["🌦 Live Weather", "📊 Analytics Dashboard"])

if page == "📊 Analytics Dashboard":
    show_dashboard()
    st.stop()

# ══════════════════════════════════════════════════════
# CITY-LOCAL TIME HELPERS
# ══════════════════════════════════════════════════════
def city_local_dt(timezone_offset: int) -> datetime:
    utc_now = datetime.now(tz=timezone.utc)
    city_tz = timezone(timedelta(seconds=timezone_offset))
    return utc_now.astimezone(city_tz)

def time_of_day(local_dt: datetime) -> str:
    h = local_dt.hour
    if h >= 20 or h < 5:   return "night"
    if 5  <= h < 7:         return "dawn"
    if 7  <= h < 17:        return "day"
    return "dusk"

def clear_icon(tod: str) -> str:
    if tod == "night":          return "🌙"
    if tod in ("dawn", "dusk"): return "🌄"
    return "☀️"

_STATIC_ICONS = {
    "Clouds":       "☁️",
    "Rain":         "🌧️",
    "Drizzle":      "🌦️",
    "Thunderstorm": "⛈️",
    "Snow":         "❄️",
    "Mist":         "🌫️",
    "Fog":          "🌫️",
    "Haze":         "🌫️",
    "Smoke":        "💨",
    "Dust":         "🌪️",
    "Sand":         "🌪️",
    "Tornado":      "🌪️",
}

def weather_icon(condition: str, tod: str) -> str:
    if condition == "Clear":
        return clear_icon(tod)
    return _STATIC_ICONS.get(condition, "🌤️")

def get_theme(condition: str, tod: str) -> dict:
    if tod == "night":
        return {
            "grad1":"#020617","grad2":"#0f172a","grad3":"#1e1b4b",
            "glass":"rgba(255,255,255,0.06)","glass2":"rgba(255,255,255,0.04)",
            "border":"rgba(255,255,255,0.10)","glow":"rgba(148,163,184,0.15)",
            "accent":"#a5b4fc","txt":"#f1f5f9",
            "txt2":"rgba(241,245,249,0.65)","txt3":"rgba(241,245,249,0.38)",
            "anim":"night",
        }
    if tod in ("dawn", "dusk"):
        return {
            "grad1":"#1a0533","grad2":"#9d174d","grad3":"#f97316",
            "glass":"rgba(255,255,255,0.10)","glass2":"rgba(255,255,255,0.07)",
            "border":"rgba(255,255,255,0.16)","glow":"rgba(249,115,22,0.25)",
            "accent":"#fb923c","txt":"#fff7ed",
            "txt2":"rgba(255,247,237,0.72)","txt3":"rgba(255,247,237,0.45)",
            "anim":"dawn",
        }
    day_themes = {
        "Clear": {
            "grad1":"#0369a1","grad2":"#0ea5e9","grad3":"#38bdf8",
            "glass":"rgba(255,255,255,0.16)","glass2":"rgba(255,255,255,0.10)",
            "border":"rgba(255,255,255,0.22)","glow":"rgba(56,189,248,0.3)",
            "accent":"#fde68a","txt":"#fff",
            "txt2":"rgba(255,255,255,0.78)","txt3":"rgba(255,255,255,0.48)",
            "anim":"sunny",
        },
        "Clouds": {
            "grad1":"#1e293b","grad2":"#334155","grad3":"#64748b",
            "glass":"rgba(255,255,255,0.12)","glass2":"rgba(255,255,255,0.07)",
            "border":"rgba(255,255,255,0.14)","glow":"rgba(148,163,184,0.18)",
            "accent":"#cbd5e1","txt":"#f1f5f9",
            "txt2":"rgba(241,245,249,0.72)","txt3":"rgba(241,245,249,0.42)",
            "anim":"cloudy",
        },
        "Rain": {
            "grad1":"#0c1445","grad2":"#1e3a8a","grad3":"#1d4ed8",
            "glass":"rgba(255,255,255,0.09)","glass2":"rgba(255,255,255,0.06)",
            "border":"rgba(255,255,255,0.12)","glow":"rgba(96,165,250,0.2)",
            "accent":"#93c5fd","txt":"#eff6ff",
            "txt2":"rgba(239,246,255,0.72)","txt3":"rgba(239,246,255,0.40)",
            "anim":"rain",
        },
        "Drizzle": {
            "grad1":"#0c1a45","grad2":"#1e3a6a","grad3":"#2563eb",
            "glass":"rgba(255,255,255,0.09)","glass2":"rgba(255,255,255,0.06)",
            "border":"rgba(255,255,255,0.12)","glow":"rgba(125,211,252,0.18)",
            "accent":"#7dd3fc","txt":"#eff6ff",
            "txt2":"rgba(239,246,255,0.70)","txt3":"rgba(239,246,255,0.38)",
            "anim":"rain",
        },
        "Thunderstorm": {
            "grad1":"#09090b","grad2":"#1e1b4b","grad3":"#4c1d95",
            "glass":"rgba(255,255,255,0.07)","glass2":"rgba(255,255,255,0.04)",
            "border":"rgba(255,255,255,0.10)","glow":"rgba(167,139,250,0.28)",
            "accent":"#c084fc","txt":"#faf5ff",
            "txt2":"rgba(250,245,255,0.68)","txt3":"rgba(250,245,255,0.38)",
            "anim":"storm",
        },
        "Snow": {
            "grad1":"#dbeafe","grad2":"#e0f2fe","grad3":"#f0f9ff",
            "glass":"rgba(255,255,255,0.42)","glass2":"rgba(255,255,255,0.28)",
            "border":"rgba(30,41,59,0.12)","glow":"rgba(186,230,253,0.45)",
            "accent":"#0284c7","txt":"#0f172a",
            "txt2":"rgba(15,23,42,0.65)","txt3":"rgba(15,23,42,0.38)",
            "anim":"snow",
        },
        "Mist": {
            "grad1":"#1c1917","grad2":"#44403c","grad3":"#78716c",
            "glass":"rgba(255,255,255,0.11)","glass2":"rgba(255,255,255,0.07)",
            "border":"rgba(255,255,255,0.14)","glow":"rgba(214,211,209,0.18)",
            "accent":"#e7e5e4","txt":"#fafaf9",
            "txt2":"rgba(250,250,249,0.70)","txt3":"rgba(250,250,249,0.40)",
            "anim":"fog",
        },
        "Haze": {
            "grad1":"#1c1917","grad2":"#44403c","grad3":"#92400e",
            "glass":"rgba(255,255,255,0.11)","glass2":"rgba(255,255,255,0.07)",
            "border":"rgba(255,255,255,0.14)","glow":"rgba(251,191,36,0.18)",
            "accent":"#fbbf24","txt":"#fffbeb",
            "txt2":"rgba(255,251,235,0.70)","txt3":"rgba(255,251,235,0.40)",
            "anim":"fog",
        },
        "Fog": {
            "grad1":"#1c1917","grad2":"#44403c","grad3":"#78716c",
            "glass":"rgba(255,255,255,0.11)","glass2":"rgba(255,255,255,0.07)",
            "border":"rgba(255,255,255,0.14)","glow":"rgba(214,211,209,0.18)",
            "accent":"#e7e5e4","txt":"#fafaf9",
            "txt2":"rgba(250,250,249,0.70)","txt3":"rgba(250,250,249,0.40)",
            "anim":"fog",
        },
    }
    return day_themes.get(condition, {
        "grad1":"#0f172a","grad2":"#1e3a5f","grad3":"#1e40af",
        "glass":"rgba(255,255,255,0.10)","glass2":"rgba(255,255,255,0.06)",
        "border":"rgba(255,255,255,0.13)","glow":"rgba(96,165,250,0.18)",
        "accent":"#60a5fa","txt":"#f1f5f9",
        "txt2":"rgba(241,245,249,0.70)","txt3":"rgba(241,245,249,0.40)",
        "anim":"cloudy",
    })

DAY_NAMES = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

# ══════════════════════════════════════════════════════
# BACKEND — DB-FIRST CACHING LOGIC
# Check DB first. If record exists within last 1 minute, return it.
# Otherwise call the API, save to DB, return fresh data.
# ══════════════════════════════════════════════════════

def _call_api(city: str) -> dict | None:
    """Call OpenWeatherMap API and return parsed weather dict."""
    try:
        response = requests.get(
            config.BASE_URL,
            params={"q": city, "appid": config.API_KEY, "units": config.UNITS},
            timeout=config.TIMEOUT,
        )
        response.raise_for_status()
        data         = response.json()
        weather_main = data["weather"][0]["main"]
        tz_offset    = data.get("timezone", 0)

        return {
            "city":            data["name"],
            "country":         data["sys"]["country"],
            "temperature":     round(data["main"]["temp"]),
            "feels_like":      round(data["main"]["feels_like"]),
            "humidity":        data["main"]["humidity"],
            "pressure":        data["main"]["pressure"],
            "wind_speed":      data["wind"]["speed"],
            "condition":       weather_main,
            "description":     data["weather"][0]["description"],
            "visibility":      data.get("visibility", 10000),
            "clouds":          data.get("clouds", {}).get("all", 0),
            "temp_min":        round(data["main"].get("temp_min", data["main"]["temp"])),
            "temp_max":        round(data["main"].get("temp_max", data["main"]["temp"])),
            "timezone_offset": tz_offset,
            "sunrise_utc":     data["sys"].get("sunrise", 0),
            "sunset_utc":      data["sys"].get("sunset",  0),
        }
    except Exception:
        return None


def fetch_weather(city: str) -> dict | None:
    """
    DB-first weather fetch with 1-minute cache window.

    Step 1: Check the database for this city.
    Step 2: If a record exists within the last 1 minute, return it (no API call).
    Step 3: Otherwise call the API, store the result in DB, and return fresh data.
    """
    # ── Step 1: Check DB cache ──
    cached = get_cached_weather(city)
    if cached is not None:
        # ── Step 2: Return cache if fresh (within 1 minute) ──
        return cached

    # ── Step 3: Cache is stale or missing — call the API ──
    weather = _call_api(city)
    if weather is None:
        return None

    # ── Build a DataFrame matching the DB schema and save ──
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    row = {
        "city":                weather["city"],
        "country":             weather["country"],
        "temperature_c":       float(weather["temperature"]),
        "feels_like_c":        float(weather["feels_like"]),
        "temp_min_c":          float(weather["temp_min"]),
        "temp_max_c":          float(weather["temp_max"]),
        "humidity_pct":        int(weather["humidity"]),
        "pressure_hpa":        int(weather["pressure"]),
        "wind_speed_mps":      float(weather["wind_speed"]),
        "wind_direction_deg":  None,
        "weather_condition":   weather["condition"],
        "weather_description": weather["description"],
        "visibility_m":        int(weather["visibility"]),
        "cloudiness_pct":      int(weather["clouds"]),
        "heat_index_c":        None,
        "comfort_level":       _comfort_level(weather["temperature"]),
        "recorded_at":         now_utc,
        "extracted_at":        now_utc,
    }
    df = pd.DataFrame([row])
    try:
        save_weather(df)
    except Exception:
        pass   # Never block the UI if DB is unavailable

    return weather


def _comfort_level(temp: float) -> str:
    if temp < 10:  return "Cold"
    if temp < 18:  return "Cool"
    if temp < 26:  return "Comfortable"
    if temp < 33:  return "Warm"
    return "Hot"


def comfort_label(temp: int) -> str:
    return _comfort_level(temp)

# ══════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════
if "search_city" not in st.session_state:
    st.session_state.search_city = config.DEFAULT_LOCATION

# ══════════════════════════════════════════════════════
# FETCH
# ══════════════════════════════════════════════════════
weather   = fetch_weather(st.session_state.search_city)

if weather:
    tz_offset = weather["timezone_offset"]
    local_dt  = city_local_dt(tz_offset)
else:
    local_dt  = datetime.now(tz=timezone.utc)

tod       = time_of_day(local_dt)
condition = weather["condition"] if weather else "Clear"
T         = get_theme(condition, tod)
icon      = weather_icon(condition, tod)

temp      = weather["temperature"] if weather else "–"
feels     = weather["feels_like"]  if weather else "–"
humidity  = weather["humidity"]    if weather else "–"
wind      = weather["wind_speed"]  if weather else "–"
pressure  = weather["pressure"]    if weather else "–"
vis_km    = round(weather["visibility"] / 1000, 1) if weather else "–"
clouds    = weather["clouds"]      if weather else "–"
desc      = weather["description"].title() if weather else "–"
comfort   = comfort_label(temp)    if isinstance(temp, int) else "–"
city_name = weather["city"]        if weather else st.session_state.search_city
country   = weather["country"]     if weather else ""
t_min     = weather["temp_min"]    if weather else "–"
t_max     = weather["temp_max"]    if weather else "–"
base_temp = float(temp)            if isinstance(temp, int) else 25.0

now_display = local_dt.strftime("%A, %d %B · %I:%M %p")

def fmt_utc_ts(unix_ts: int, tz_off: int) -> str:
    try:
        city_tz = timezone(timedelta(seconds=tz_off))
        return datetime.fromtimestamp(unix_ts, tz=city_tz).strftime("%I:%M %p").lstrip("0")
    except Exception:
        return "–"

sunrise_local = fmt_utc_ts(weather["sunrise_utc"], tz_offset) if weather else "–"
sunset_local  = fmt_utc_ts(weather["sunset_utc"],  tz_offset) if weather else "–"

HOURLY = []
for i in range(13):
    local_hour_dt = local_dt + timedelta(hours=i)
    hour_tod      = time_of_day(local_hour_dt)
    d             = math.sin((i / 12) * math.pi) * 3
    t_h           = round(base_temp + d + random.uniform(-0.5, 0.5))
    HOURLY.append({
        "label": "Now" if i == 0 else local_hour_dt.strftime("%I %p").lstrip("0"),
        "temp":  t_h,
        "icon":  weather_icon(condition, hour_tod),
    })

today_idx = local_dt.weekday()
FC_ICONS  = [icon, "🌤️", "☀️", "⛅", "🌦️", "🌧️", "☀️"]
FORECAST  = []
for i in range(7):
    hi = round(base_temp + math.sin(i * .9) * 3 + random.uniform(-1, 1))
    lo = round(hi - random.uniform(4, 9))
    FORECAST.append({
        "day":       "Today" if i == 0 else DAY_NAMES[(today_idx + i) % 7],
        "icon":      FC_ICONS[i],
        "hi":        hi, "lo": lo,
        "bar_left":  max(0,  round(20 + (lo - (base_temp - 10)) / 20 * 55)),
        "bar_width": max(10, round((hi - lo) / 20 * 45 + 10)),
    })

# ══════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════
anim_name = T["anim"]

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}

:root{{
  --g1:{T['grad1']};--g2:{T['grad2']};--g3:{T['grad3']};
  --glass:{T['glass']};--glass2:{T['glass2']};
  --border:{T['border']};--glow:{T['glow']};
  --accent:{T['accent']};
  --txt:{T['txt']};--txt2:{T['txt2']};--txt3:{T['txt3']};
  --r:22px;--r-lg:30px;--blur:blur(28px);
  --shadow:0 8px 32px rgba(0,0,0,0.24),0 1px 0 rgba(255,255,255,0.09) inset;
  --shadow-h:0 16px 48px rgba(0,0,0,0.34),0 1px 0 rgba(255,255,255,0.12) inset;
}}

html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"],.main{{
  font-family:Inter,'SF Pro Display','Segoe UI',sans-serif!important;
  color:var(--txt)!important;
  background:linear-gradient(160deg,var(--g1) 0%,var(--g2) 45%,var(--g3) 100%)!important;
  min-height:100vh;
}}

[data-testid="stAppViewContainer"]{{
  background:linear-gradient(160deg,var(--g1) 0%,var(--g2) 45%,var(--g3) 100%)!important;
  transition:background 1.4s ease;
  min-height:100vh;position:relative;overflow-x:hidden;
}}

[data-testid="stHeader"],[data-testid="stToolbar"],
#MainMenu,footer,[data-testid="collapsedControl"],
.block-container{{padding:0!important;max-width:100%!important;}}

@keyframes fadeUp  {{from{{opacity:0;transform:translateY(22px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes fadeIn  {{from{{opacity:0}}to{{opacity:1}}}}
@keyframes float   {{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-12px)}}}}
@keyframes glowP   {{0%,100%{{box-shadow:0 0 30px var(--glow)}}50%{{box-shadow:0 0 60px var(--glow),0 0 100px var(--glow)}}}}
@keyframes rainFall{{0%{{transform:translateY(-20px) translateX(0);opacity:0}}15%{{opacity:1}}100%{{transform:translateY(100vh) translateX(-30px);opacity:0}}}}
@keyframes snowFall{{0%{{transform:translateY(-10px) translateX(0) rotate(0);opacity:0}}10%{{opacity:.9}}100%{{transform:translateY(100vh) translateX(60px) rotate(360deg);opacity:0}}}}
@keyframes twinkle {{0%,100%{{opacity:.2;transform:scale(1)}}50%{{opacity:1;transform:scale(1.3)}}}}
@keyframes lightning{{0%,90%,100%{{opacity:0}}92%,98%{{opacity:1}}95%{{opacity:.3}}}}
@keyframes cloudDrift{{from{{transform:translateX(-120px)}}to{{transform:translateX(calc(100vw + 120px))}}}}
@keyframes sunGlow {{0%,100%{{opacity:.4;transform:scale(1) rotate(0)}}50%{{opacity:.7;transform:scale(1.1) rotate(180deg)}}}}
@keyframes moonGlow{{0%,100%{{box-shadow:0 0 20px rgba(165,180,252,.3)}}50%{{box-shadow:0 0 50px rgba(165,180,252,.6),0 0 80px rgba(165,180,252,.2)}}}}
@keyframes dawnGlow{{0%,100%{{opacity:.35}}50%{{opacity:.65}}}}

.a1{{animation:fadeUp .55s ease both}}
.a2{{animation:fadeUp .55s .10s ease both}}
.a3{{animation:fadeUp .55s .20s ease both}}
.a4{{animation:fadeUp .55s .30s ease both}}
.a5{{animation:fadeUp .55s .40s ease both}}
.a6{{animation:fadeUp .55s .50s ease both}}

.particles{{position:fixed;inset:0;pointer-events:none;z-index:0;overflow:hidden}}
.rain-drop{{position:absolute;width:1.5px;border-radius:2px;background:linear-gradient(to bottom,transparent,rgba(147,197,253,0.7));animation:rainFall linear infinite;}}
.snow-flake{{position:absolute;border-radius:50%;background:rgba(255,255,255,0.85);animation:snowFall ease-in infinite;box-shadow:0 0 4px rgba(255,255,255,.5);}}
.star{{position:absolute;border-radius:50%;background:#fff;animation:twinkle ease-in-out infinite;}}
.lightning{{position:fixed;inset:0;background:rgba(200,180,255,.12);animation:lightning 4s ease-in-out infinite;pointer-events:none;z-index:1;}}
.cloud-p{{position:absolute;border-radius:50%;background:rgba(255,255,255,.08);animation:cloudDrift linear infinite;filter:blur(14px);}}
.sun-ray{{position:fixed;width:120vmax;height:120vmax;top:50%;left:50%;transform:translate(-50%,-50%);background:radial-gradient(ellipse,rgba(253,230,138,.12) 0%,transparent 65%);animation:sunGlow 6s ease-in-out infinite;pointer-events:none;z-index:0;}}
.moon-orb{{position:fixed;top:6%;right:8%;width:64px;height:64px;border-radius:50%;background:radial-gradient(circle at 35% 35%,#f8fafc,#c7d2fe);animation:moonGlow 4s ease-in-out infinite;pointer-events:none;z-index:0;box-shadow:0 0 32px rgba(165,180,252,.4);}}
.dawn-ray{{position:fixed;bottom:0;left:50%;transform:translateX(-50%);width:140vw;height:60vh;background:radial-gradient(ellipse at 50% 100%,rgba(249,115,22,.22) 0%,rgba(157,23,77,.12) 50%,transparent 75%);animation:dawnGlow 5s ease-in-out infinite;pointer-events:none;z-index:0;}}

.card{{background:var(--glass);backdrop-filter:var(--blur);-webkit-backdrop-filter:var(--blur);border:1px solid var(--border);border-radius:var(--r);box-shadow:var(--shadow);position:relative;overflow:hidden;transition:transform .28s ease,box-shadow .28s ease,border-color .28s ease;}}
.card::before{{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.18),transparent);}}
.card:hover{{transform:translateY(-3px);box-shadow:var(--shadow-h);border-color:rgba(255,255,255,.22);}}

.app{{max-width:1200px;margin:0 auto;padding:0 20px 48px;position:relative;z-index:2}}

.search-icon{{font-size:1.1rem;opacity:.6;flex-shrink:0;margin-right:10px}}
.app-name{{font-size:.8rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--txt3);display:flex;align-items:center;gap:6px;}}

.tod-badge{{display:inline-flex;align-items:center;gap:5px;font-size:.65rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;background:rgba(255,255,255,.12);border:1px solid var(--border);border-radius:20px;padding:3px 10px;color:var(--txt2);margin-left:10px;vertical-align:middle;}}

.hero{{padding:44px 36px 36px;text-align:center;margin-bottom:16px;animation:glowP 5s ease-in-out infinite;}}
.hero::after{{content:'';position:absolute;inset:0;background:radial-gradient(ellipse 65% 55% at 50% 25%,var(--glow),transparent);pointer-events:none;}}
.hero-date{{font-size:.68rem;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--txt3);margin-bottom:10px;}}
.hero-loc{{font-size:clamp(32px,5vw,52px);font-weight:800;letter-spacing:-.04em;line-height:1;color:var(--txt);margin-bottom:4px;}}
.hero-country{{font-size:.9rem;color:var(--txt3);margin-bottom:28px}}
.hero-icon{{font-size:clamp(80px,12vw,130px);line-height:1;display:block;margin-bottom:14px;animation:float 5.5s ease-in-out infinite;filter:drop-shadow(0 16px 40px rgba(0,0,0,.22));}}
.hero-temp{{font-size:clamp(72px,13vw,110px);font-weight:300;letter-spacing:-.06em;line-height:1;color:var(--txt);margin-bottom:8px;font-variant-numeric:tabular-nums;}}
.hero-temp sup{{font-size:clamp(24px,4vw,40px);font-weight:400;vertical-align:super;opacity:.75}}
.hero-desc{{font-size:clamp(16px,2.5vw,22px);font-weight:400;color:var(--txt2);margin-bottom:28px}}
.hero-minmax{{font-size:.88rem;color:var(--txt3);margin-bottom:28px;display:flex;align-items:center;justify-content:center;gap:10px;}}
.hero-stats{{display:flex;justify-content:center;background:rgba(0,0,0,.18);border:1px solid rgba(255,255,255,.08);border-radius:18px;overflow:hidden;max-width:580px;margin:0 auto;}}
.hs{{flex:1;padding:16px 8px;text-align:center;border-right:1px solid rgba(255,255,255,.07)}}
.hs:last-child{{border-right:none}}
.hs-l{{font-size:.58rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--txt3);margin-bottom:5px}}
.hs-v{{font-size:.95rem;font-weight:700;color:var(--txt);font-variant-numeric:tabular-nums}}

.sec-hdr{{display:flex;align-items:center;gap:8px;font-size:.62rem;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:var(--txt3);margin-bottom:12px;}}
.sec-dot{{width:5px;height:5px;border-radius:50%;background:var(--accent);box-shadow:0 0 8px var(--accent)}}

.hourly-card{{padding:18px 20px 16px;margin-bottom:16px;}}
.hourly-scroll{{display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;padding-bottom:2px}}
.hourly-scroll::-webkit-scrollbar{{display:none}}
.hour-item{{flex-shrink:0;width:68px;display:flex;flex-direction:column;align-items:center;gap:8px;padding:13px 7px;border-radius:16px;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.08);cursor:default;transition:all .22s;}}
.hour-item:hover{{background:rgba(255,255,255,.16);transform:translateY(-2px);border-color:var(--border)}}
.hour-item.now{{background:rgba(255,255,255,.22);border-color:var(--border);box-shadow:0 4px 16px rgba(0,0,0,.14)}}
.h-time{{font-size:.64rem;font-weight:600;color:var(--txt3)}}
.h-time.now{{color:var(--txt);font-weight:700}}
.h-ic{{font-size:1.55rem;line-height:1}}
.h-temp{{font-size:.88rem;font-weight:700;color:var(--txt)}}

.fc-card{{padding:6px 0;margin-bottom:16px}}
.fc-inner{{padding:0 18px}}
.fc-row{{display:flex;align-items:center;padding:13px 8px;border-bottom:1px solid rgba(255,255,255,.06);border-radius:12px;transition:background .15s;}}
.fc-row:last-child{{border-bottom:none}}
.fc-row:hover{{background:rgba(255,255,255,.06)}}
.fc-day{{font-size:.88rem;font-weight:500;color:var(--txt2);width:46px;flex-shrink:0}}
.fc-ic{{font-size:1.45rem;width:34px;text-align:center;flex-shrink:0}}
.fc-bar-wrap{{flex:1;margin:0 14px}}
.fc-bar{{height:4px;background:rgba(255,255,255,.10);border-radius:4px;position:relative}}
.fc-bar-fill{{position:absolute;top:0;height:100%;border-radius:4px;background:linear-gradient(90deg,#60a5fa,#fbbf24)}}
.fc-temps{{display:flex;gap:10px;font-size:.88rem;font-variant-numeric:tabular-nums}}
.fc-lo{{color:var(--txt3);font-weight:400}}
.fc-hi{{color:var(--txt);font-weight:700}}

.tile-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}}
@media(max-width:1000px){{.tile-grid{{grid-template-columns:repeat(3,1fr)}}}}
@media(max-width:680px) {{.tile-grid{{grid-template-columns:repeat(2,1fr)}}}}
.tile{{padding:22px 18px 16px;cursor:default;position:relative;overflow:hidden;}}
.tile-ic{{font-size:1.6rem;margin-bottom:9px;display:block}}
.tile-lbl{{font-size:.58rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--txt3);margin-bottom:5px}}
.tile-val{{font-size:2rem;font-weight:700;letter-spacing:-.03em;line-height:1;color:var(--txt);margin-bottom:2px;font-variant-numeric:tabular-nums;}}
.tile-unit{{font-size:.88rem;font-weight:400;opacity:.6;margin-left:1px}}
.tile-sub{{font-size:.7rem;color:var(--txt3);margin-top:4px}}
.tile-bar{{height:3px;margin-top:10px;border-radius:3px;background:rgba(255,255,255,.08)}}
.tile-bar-fill{{height:100%;border-radius:3px;background:var(--accent);transition:width 1.2s ease}}
.tile-bg{{position:absolute;bottom:-8px;right:-4px;font-size:4rem;opacity:.06;transform:rotate(-12deg);pointer-events:none}}

.stButton>button{{background:rgba(255,255,255,.14)!important;color:var(--txt)!important;border:1px solid var(--border)!important;border-radius:14px!important;font-family:Inter,sans-serif!important;font-weight:600!important;font-size:.85rem!important;padding:.58rem 1.4rem!important;backdrop-filter:blur(16px)!important;transition:all .22s!important;box-shadow:none!important;letter-spacing:-.01em!important;}}
.stButton>button:hover{{background:rgba(255,255,255,.24)!important;transform:translateY(-2px)!important;box-shadow:0 6px 22px rgba(0,0,0,.18)!important}}
[data-testid="stTextInput"]>div>div>input{{background:transparent!important;border:none!important;color:var(--txt)!important;font-family:Inter,sans-serif!important;font-size:.95rem!important;font-weight:500!important;padding:.62rem 0!important;box-shadow:none!important;outline:none!important;}}
[data-testid="stTextInput"]>div>div>input::placeholder{{color:var(--txt3)!important}}
[data-testid="stTextInput"]>div>div{{border:none!important;background:transparent!important;box-shadow:none!important}}
[data-testid="stTextInput"]{{border:none!important;background:transparent!important}}
.stAlert,.stSuccess,.stError,.stWarning,.stInfo{{display:none!important}}
[data-testid="stForm"]{{border:none!important;padding:0!important}}
label{{color:var(--txt3)!important;font-size:.72rem!important;font-family:Inter,sans-serif!important}}

.w-footer{{text-align:center;padding:24px 0 4px;font-size:.65rem;color:var(--txt3);letter-spacing:.05em}}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# WEATHER PARTICLES
# ══════════════════════════════════════════════════════
particles_html = '<div class="particles">'

if anim_name == "rain":
    for _ in range(60):
        l   = random.randint(0, 100)
        dur = round(random.uniform(0.7, 1.6), 2)
        dl  = round(random.uniform(0, 3),    2)
        h   = random.randint(40, 90)
        op  = round(random.uniform(.3, .8),  2)
        particles_html += (f'<div class="rain-drop" style="left:{l}%;height:{h}px;'
                           f'animation-duration:{dur}s;animation-delay:{dl}s;opacity:{op}"></div>')

elif anim_name == "snow":
    for _ in range(50):
        l   = random.randint(0, 100)
        sz  = random.randint(4, 10)
        dur = round(random.uniform(5, 12), 2)
        dl  = round(random.uniform(0, 8),  2)
        particles_html += (f'<div class="snow-flake" style="left:{l}%;width:{sz}px;height:{sz}px;'
                           f'animation-duration:{dur}s;animation-delay:{dl}s"></div>')

elif anim_name == "night":
    for _ in range(70):
        l   = random.randint(1, 99)
        t   = random.randint(1, 65)
        sz  = random.randint(1, 3)
        dur = round(random.uniform(2, 5),  2)
        dl  = round(random.uniform(0, 4),  2)
        particles_html += (f'<div class="star" style="left:{l}%;top:{t}%;width:{sz}px;height:{sz}px;'
                           f'animation-duration:{dur}s;animation-delay:{dl}s"></div>')
    particles_html += '<div class="moon-orb"></div>'

elif anim_name == "storm":
    particles_html += '<div class="lightning"></div>'
    for _ in range(35):
        l   = random.randint(0, 100)
        dur = round(random.uniform(0.8, 2.0), 2)
        dl  = round(random.uniform(0, 4),     2)
        h   = random.randint(50, 100)
        particles_html += (f'<div class="rain-drop" style="left:{l}%;height:{h}px;'
                           f'animation-duration:{dur}s;animation-delay:{dl}s;opacity:.45;'
                           f'background:linear-gradient(to bottom,transparent,rgba(192,132,252,.7))"></div>')

elif anim_name == "sunny":
    particles_html += '<div class="sun-ray"></div>'

elif anim_name == "cloudy":
    for _ in range(4):
        t   = random.randint(5, 40)
        sz  = random.randint(120, 300)
        dur = random.randint(40, 90)
        dl  = random.randint(0, 20)
        particles_html += (f'<div class="cloud-p" style="top:{t}%;width:{sz}px;height:{sz}px;'
                           f'animation-duration:{dur}s;animation-delay:-{dl}s"></div>')

elif anim_name == "fog":
    for _ in range(5):
        t   = random.randint(10, 70)
        sz  = random.randint(200, 420)
        dur = random.randint(60, 120)
        dl  = random.randint(0, 30)
        particles_html += (f'<div class="cloud-p" style="top:{t}%;width:{sz}px;height:{sz}px;'
                           f'opacity:.55;animation-duration:{dur}s;animation-delay:-{dl}s"></div>')

elif anim_name == "dawn":
    particles_html += '<div class="dawn-ray"></div>'
    particles_html += '<div class="sun-ray" style="background:radial-gradient(ellipse,rgba(249,115,22,.15) 0%,transparent 65%)"></div>'

particles_html += "</div>"
st.markdown(particles_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# APP WRAPPER
# ══════════════════════════════════════════════════════
st.markdown('<div class="app">', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# SEARCH BAR
# ══════════════════════════════════════════════════════
TOD_LABELS = {"night": "🌙 Night", "dawn": "🌅 Dawn", "day": "☀️ Day", "dusk": "🌇 Dusk"}
tod_badge  = TOD_LABELS.get(tod, "")

st.markdown(f"""
<div class="search-wrap">
  <div class="search-inner">
    <span class="search-icon"></span>
""", unsafe_allow_html=True)

col_in, col_btn = st.columns([6, 1])
with col_in:
    city_input = st.text_input(
        "Search",
        value=st.session_state.search_city,
        placeholder="Search any city in the world…",
        label_visibility="collapsed",
        key="city_input_field",
    )
with col_btn:
    search_btn = st.button("Search", use_container_width=True)

st.markdown(f'</div><span class="app-name">🌤️ WeatherIQ<span class="tod-badge">{tod_badge}</span></span></div>', unsafe_allow_html=True)

if search_btn and city_input.strip():
    st.session_state.search_city = city_input.strip()
    st.rerun()

if not weather:
    st.markdown(f"""
    <div class="card a1" style="padding:48px;text-align:center;margin:20px 0">
      <div style="font-size:3rem;margin-bottom:16px">🔍</div>
      <div style="font-size:1.1rem;font-weight:700;color:var(--txt);margin-bottom:8px">City not found</div>
      <div style="font-size:.82rem;color:var(--txt2)">Try searching for a different city name.</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ══════════════════════════════════════════════════════
# HERO + RIGHT COLUMN
# ══════════════════════════════════════════════════════
col_left, col_right = st.columns([5, 4], gap="medium")

with col_left:
    st.markdown(f"""
    <div class="card hero a1">
      <div class="hero-date">{now_display}</div>
      <div class="hero-loc">{city_name}</div>
      <div class="hero-country">{country}</div>
      <span class="hero-icon">{icon}</span>
      <div class="hero-temp">{temp}<sup>°</sup></div>
      <div class="hero-desc">{desc}</div>
      <div class="hero-minmax"><span>⬆ {t_max}°</span><span style="opacity:.3">·</span><span>⬇ {t_min}°</span></div>
      <div class="hero-stats">
        <div class="hs"><div class="hs-l">Feels</div><div class="hs-v">{feels}°</div></div>
        <div class="hs"><div class="hs-l">Humidity</div><div class="hs-v">{humidity}%</div></div>
        <div class="hs"><div class="hs-l">Wind</div><div class="hs-v">{wind} m/s</div></div>
        <div class="hs"><div class="hs-l">Pressure</div><div class="hs-v">{pressure}</div></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

with col_right:
    hourly_html = '<div class="card hourly-card a2"><div class="sec-hdr"><span class="sec-dot"></span>HOURLY FORECAST</div><div class="hourly-scroll">'
    for item in HOURLY:
        nc = "now" if item["label"] == "Now" else ""
        nt = "now" if item["label"] == "Now" else ""
        hourly_html += (f'<div class="hour-item {nc}">'
                        f'<span class="h-time {nt}">{item["label"]}</span>'
                        f'<span class="h-ic">{item["icon"]}</span>'
                        f'<span class="h-temp">{item["temp"]}°</span></div>')
    hourly_html += "</div></div>"
    st.markdown(hourly_html, unsafe_allow_html=True)

    fc_html = ('<div class="card fc-card a3">'
               '<div style="padding:14px 18px 4px"><div class="sec-hdr">'
               '<span class="sec-dot"></span>7-DAY FORECAST</div></div>'
               '<div class="fc-inner">')
    for item in FORECAST:
        fc_html += (f'<div class="fc-row">'
                    f'<span class="fc-day">{item["day"]}</span>'
                    f'<span class="fc-ic">{item["icon"]}</span>'
                    f'<div class="fc-bar-wrap"><div class="fc-bar">'
                    f'<div class="fc-bar-fill" style="left:{item["bar_left"]}%;width:{item["bar_width"]}%"></div>'
                    f'</div></div>'
                    f'<div class="fc-temps"><span class="fc-lo">{item["lo"]}°</span>'
                    f'<span class="fc-hi">{item["hi"]}°</span></div></div>')
    fc_html += "</div></div>"
    st.markdown(fc_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# DETAIL TILES
# ══════════════════════════════════════════════════════
hum_pct   = int(humidity)     if isinstance(humidity, int)  else 50
wind_pct  = min(100, int(float(wind) / 25 * 100)) if isinstance(wind, (int, float)) else 30
pres_pct  = max(0, min(100, int((float(pressure) - 870) / 215 * 100))) if isinstance(pressure, int) else 60
vis_pct   = min(100, int(float(vis_km) / 15 * 100)) if isinstance(vis_km, float) else 75
cloud_pct = int(clouds) if isinstance(clouds, int) else 40

TILES = [
    ("🌡️", "FEELS LIKE",   f"{feels}",      "°C",  comfort,                 hum_pct),
    ("💧", "HUMIDITY",      f"{humidity}",   "%",   "Atmospheric moisture",  hum_pct),
    ("💨", "WIND SPEED",    f"{wind}",       "m/s", "Surface wind",          wind_pct),
    ("🧭", "PRESSURE",      f"{pressure}",   "hPa", "Sea level",             pres_pct),
    ("👁️", "VISIBILITY",    f"{vis_km}",     "km",  "Horizontal sight",      vis_pct),
    ("☁️", "CLOUD COVER",  f"{clouds}",     "%",   desc,                    cloud_pct),
    ("🌅", "SUNRISE",       sunrise_local,   "",    "Local city time",       50),
    ("🌇", "SUNSET",        sunset_local,    "",    "Local city time",       50),
]

st.markdown(f'<div class="sec-hdr a4" style="margin-top:4px"><span class="sec-dot"></span>WEATHER DETAILS</div><div class="tile-grid a4">', unsafe_allow_html=True)

for ic, lbl, val, unit, sub, pct in TILES:
    st.markdown(f"""
    <div class="card tile">
      <span class="tile-ic">{ic}</span>
      <div class="tile-lbl">{lbl}</div>
      <div class="tile-val">{val}<span class="tile-unit">{unit}</span></div>
      <div class="tile-sub">{sub}</div>
      <div class="tile-bar"><div class="tile-bar-fill" style="width:{pct}%"></div></div>
      <div class="tile-bg">{ic}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════
st.markdown(f"""
<div class="w-footer a6">
  WeatherIQ · Powered by OpenWeatherMap · {city_name} local time: {local_dt.strftime('%d %b %Y %I:%M %p %Z')}
</div>
""", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
