import io
import re
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Cavite River Watch", page_icon="🌊", layout="wide")

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
}


def classify_level(text: str):
    value = str(text).strip().lower()
    number = re.search(r"(-?\d+(?:\.\d+)?)", value)
    if "inch" in value and number:
        return float(number.group(1)) * 2.54, "Flood depth", "Measured"
    if re.search(r"\bft\b|feet|foot", value) and number:
        return float(number.group(1)) * 30.48, "River level", "Measured"
    if "normal" in value:
        return None, "Qualitative", "Normal"
    return None, "Unavailable", "No exact value"


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    expected = ["river_or_site", "station", "location", "water_level", "observed_at", "status"]
    missing = [column for column in expected if column not in df.columns]
    if missing:
        raise ValueError("Missing columns: " + ", ".join(missing))
    df = df[expected].copy()
    parsed = df["water_level"].apply(classify_level)
    df[["value_cm", "reading_type", "display_state"]] = pd.DataFrame(parsed.tolist(), index=df.index)
    df["latitude"] = df["station"].map(lambda value: COORDS.get(value, (None, None))[0])
    df["longitude"] = df["station"].map(lambda value: COORDS.get(value, (None, None))[1])
    return df


st.title("🌊 Cavite River Watch")
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
unavailable = int((data["display_state"] == "No exact value").sum())

c1, c2, c3, c4 = st.columns(4)
c1.metric("Stations", len(data))
c2.metric("Exact readings", len(measured))
c3.metric("Reported normal", normal)
c4.metric("Without exact value", unavailable)

st.warning(
    "Do not compare all bars as river stages: road flood depth and river level are different measurements. "
    "Threshold-based risk needs station-specific alert, alarm, and critical levels."
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
            zoom=10.4,
            center={"lat": 14.445, "lon": 120.945},
            height=470,
        )
        fig_map.update_layout(map_style="carto-positron", margin=dict(l=0, r=0, t=0, b=0), legend_title="Evidence")
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.info("No mapped stations found.")

with right:
    st.subheader("Exact numeric observations")
    if len(measured):
        fig_bar = px.bar(
            measured,
            x="value_cm",
            y="station",
            orientation="h",
            color="reading_type",
            text="water_level",
            hover_data=["river_or_site", "observed_at", "status"],
            labels={"value_cm": "Converted value (cm)", "station": "Station"},
            height=390,
        )
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_layout(margin=dict(l=0, r=20, t=10, b=0), legend_title="Measurement type")
        st.plotly_chart(fig_bar, use_container_width=True)
    st.caption("Conversion is for display only: 1 inch = 2.54 cm; 1 ft = 30.48 cm.")

st.subheader("Station observation cards")
for _, row in data.iterrows():
    with st.container(border=True):
        a, b, c = st.columns([1.3, 1, 2])
        a.markdown(f"**{row['river_or_site']}**  \n{row['station']}")
        b.metric("Reported level", row["water_level"])
        c.markdown(f"**Observed:** {row['observed_at']}  \n**Assessment:** {row['status']}")

st.subheader("Validated data table")
display = data[["river_or_site", "station", "location", "water_level", "observed_at", "reading_type", "status"]]
st.dataframe(display, use_container_width=True, hide_index=True)
st.download_button("Download cleaned TSV", display.to_csv(sep="\t", index=False), "cavite_water_levels_cleaned.tsv")

