# Cavite River Watch

A Streamlit dashboard for pasted or uploaded Philippine water-monitoring TSV data. It maps stations, recognizes metre/foot/inch readings, and interprets qualitative Red and Normal reports without treating unlike gauge datums as directly comparable.

## Run

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

The app expects these tab-separated columns:

Required: `river_or_site, station, location, water_level, observed_at`

Optional: `status`

For new stations, add verified latitude/longitude pairs to `COORDS` in `app.py`.
