import io
import re
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Philippine Water-Level Watch", page_icon="🌊", layout="wide")

SAMPLE = """river_or_site\tstation\tlocation\twater_level\tobserved_at\tstatus
Bacoor River Area\tSM Bacoor, Tirona Highway\tBacoor City, Cavite\t11 inches floodwater\t2026-08-08; time not shown\tFlood depth—not river-gauge level
Marusay River\tMarusay monitoring point\tImus City, Cavite\t2.6 ft ANL\t2026-08-06 08:30 PHT\tLatest exact river reading found
Zapote River\tZapote 3\tBacoor City, Cavite\tNormal water level\tLatest indexed BDRRMO monitoring; exact time unavailable\tQualitative
Mabolo/Binakayan River\tMabolo-Binakayan Bridge\tBacoor City, Cavite\tWater level monitored; exact value unavailable\tLatest indexed BDRRMO monitoring\tQualitative
"""

COORDS = {
    "SM Bacoor, Tirona Highway": (14.4443, 120.9500),
    "Marusay monitoring point": (14.4095, 120.9388),
    "Zapote 3": (14.4747, 120.9704),
    "Mabolo-Binakayan Bridge": (14.4545, 120.9300),
    "MDRRMC Calasiao Flood Monitoring": (16.0113, 120.3609),
    "South Bay RLS": (14.1815, 121.2850),
    "East Bay RLS": (14.2986, 121.4590),
    "Central Bay RLS": (14.4860, 121.2290),
    "West Bay RLS": (14.4081, 121.0415),
    "Marikina River water-level gauge": (14.6507, 121.1029),
    "MDRRMO Mabini river gauge": (16.0699, 119.9401),
    "Pantabangan Dam": (15.8120, 121.1015),
    "Sulipan monitoring station": (14.9534, 120.7582),
    "Isabel II Bridge": (14.4035, 120.9367),
    "Tomas Mascardo Bridge (Imus Bridge)": (14.4290, 120.9362),
}


def classify_level(text: str, river_or_site: str = ""):
    value = str(text).strip().lower()
    site = str(river_or_site).strip().lower()
    number = re.search(r"(-?\d+(?:\.\d+)?)", value)
    if "inch" in value and number:
        return float(number.group(1)) * 2.54, "Flood depth", "Measured"
    if re.search(r"\bft\b|feet|foot", value) and number:
        return float(number.group(1)) * 30.48, "River level", "Measured"
    if re.search(r"\bm\b|meter|metre", value) and number:
        kind = "Reservoir elevation" if "reservoir" in site or "dam" in site else "Water level"
        return float(number.group(1)) * 100, kind, "Measured"
    if "red" in value:
        return None, "Qualitative alert", "Red"
    if "normal" in value:
        return None, "Qualitative alert", "Normal"
    return None, "Unavailable", "No exact value"


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    required = ["river_or_site", "station", "location", "water_level", "observed_at"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError("Missing columns: " + ", ".join(missing))
    if "status" not in df.columns:
        df["status"] = ""
    df = df[required + ["status"]].copy()
    parsed = df.apply(lambda row: classify_level(row["water_level"], row["river_or_site"]), axis=1)
    df[["value_cm", "reading_type", "display_state"]] = pd.DataFrame(parsed.tolist(), index=df.index)
    df["latitude"] = df["station"].map(lambda value: COORDS.get(value, (None, None))[0])
    df["longitude"] = df["station"].map(lambda value: COORDS.get(value, (None, None))[1])
    return df


st.title("🌊 Philippine Water-Level Watch")
st.caption("Paste monitoring TSV to turn mixed river observations into an evidence-aware dashboard.")

with st.sidebar:
    st.subheader("Data input")
    source = st.radio("Choose source", ["Paste TSV", "Upload TSV"], horizontal=True)
    if source == "Paste TSV":
        raw = st.text_area("TSV data", SAMPLE, height=280)
    else:
        upload = st.file_uploader("Upload a .tsv file", type=["tsv", "txt"])
        raw = upload.getvalue().decode("utf-8-sig") if upload else SAMPLE
    st.caption("Station coordinates can be extended in the COORDS dictionary in app.py.")

try:
    data = prepare(pd.read_csv(io.StringIO(raw), sep="\t", dtype=str).fillna(""))
except Exception as exc:
    st.error(f"Could not read the TSV: {exc}")
    st.stop()

measured = data[data["value_cm"].notna()]
normal = int((data["display_state"] == "Normal").sum())
red = int((data["display_state"] == "Red").sum())
unavailable = int((data["display_state"] == "No exact value").sum())

c1, c2, c3, c4 = st.columns(4)
c1.metric("Stations", len(data))
c2.metric("Exact readings", len(measured))
c3.metric("Reported normal", normal)
c4.metric("Red alerts", red)

st.warning(
    "Raw elevations are not directly comparable across rivers, lakes, dams, and local gauges because their zero datums differ. "
    "Risk classification requires each station's official alert, alarm, and critical thresholds."
)

left, right = st.columns([1.15, 1])
with left:
    st.subheader("Monitoring locations")
    mapped = data.dropna(subset=["latitude", "longitude"])
    if len(mapped):
        fig_map = px.scatter_map(
            mapped,
            lat="latitude",
            lon="longitude",
            hover_name="station",
            hover_data={"river_or_site": True, "water_level": True, "observed_at": True,
                        "latitude": False, "longitude": False},
            color="reading_type",
            size=[16] * len(mapped),
            zoom=6.2,
            center={"lat": 15.0, "lon": 121.0},
            height=470,
        )
        fig_map.update_layout(map_style="carto-positron", margin=dict(l=0, r=0, t=0, b=0), legend_title="Evidence")
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.info("No mapped stations found.")

with right:
    st.subheader("Exact numeric observations by station")
    if len(measured):
        chart_data = measured.copy()
        chart_data["value_native"] = chart_data["water_level"].str.extract(r"(-?\d+(?:\.\d+)?)")[0].astype(float)
        chart_data["unit"] = chart_data["water_level"].str.extract(r"\b(ft|m|inches?)\b", flags=re.I)[0].fillna("")
        fig_bar = px.bar(
            chart_data,
            x="value_native",
            y="station",
            orientation="h",
            color="reading_type",
            text="water_level",
            hover_data=["river_or_site", "observed_at", "status"],
            facet_col="unit",
            labels={"value_native": "Reported value", "station": "Station", "unit": "Unit"},
            height=390,
        )
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_layout(margin=dict(l=0, r=20, t=10, b=0), legend_title="Measurement type")
        st.plotly_chart(fig_bar, use_container_width=True)
    st.caption("Bars are separated by reported unit. Compare trends at the same station—not absolute heights between stations.")

st.subheader("Station observation cards")
for _, row in data.iterrows():
    with st.container(border=True):
        a, b, c = st.columns([1.3, 1, 2])
        a.markdown(f"**{row['river_or_site']}**  \n{row['station']}")
        b.metric("Reported level", row["water_level"])
        assessment = row["status"] or row["display_state"]
        c.markdown(f"**Observed:** {row['observed_at']}  \n**Assessment:** {assessment}")

st.subheader("Validated data table")
display = data[["river_or_site", "station", "location", "water_level", "observed_at", "reading_type", "status"]]
st.dataframe(display, use_container_width=True, hide_index=True)
st.download_button("Download cleaned TSV", display.to_csv(sep="\t", index=False), "cavite_water_levels_cleaned.tsv")
