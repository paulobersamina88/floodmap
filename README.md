# Cavite River Watch

A Streamlit dashboard for pasted or uploaded river-monitoring TSV data. It maps stations, converts numeric readings to centimetres for display, and keeps road-flood depth separate from river-stage measurements.

## Run

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

The app expects these tab-separated columns:

`river_or_site, station, location, water_level, observed_at, status`

For new stations, add verified latitude/longitude pairs to `COORDS` in `app.py`.

