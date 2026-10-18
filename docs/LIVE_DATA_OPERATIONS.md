# Live data and map deployment

The October 18 deployment returned Open-Meteo HTTP 429 and served the January 1,
2025 sample. A successful HTTP response from Atmos does not imply current data.
Check `/api/forecast/delhi`: `data_source`, `observed_at`, `freshness`, and
`ground_stations` are the relevant fields.

## Backend

- Install the updated requirements (including filelock).
- Set `ATMOS_CACHE_DIR` to a writable persistent disk directory on Render. Without
  a persistent disk the cache survives process restarts, but not replacement of
  the deployment filesystem. Files must be private to the application.
- Workers sharing this directory coordinate refreshes. Separate Render instances
  need a shared cache/scheduler; filesystem locks cannot coordinate separate disks.
- Initial inputs request three days; subsequent refreshes overlap one day and
  retain up to 31 days as history accumulates. Inputs are fetched at most hourly.
- HTTP 429 stores a shared cooldown using Retry-After (30 minutes if absent).
  Transient network/5xx failures retry twice with backoff. A failed refresh keeps
  the previous live snapshot and its original timestamp, including after restart.
- `WAQI_TOKEN` enables the existing ground-calibration adapter. Configure it in
  Render secrets, never a NEXT_PUBLIC variable. Without it the output remains
  regional CAMS model data, which cannot resolve actual ward variation.
- Repeated 429s on shared-host IPs may require an appropriately licensed provider
  plan or dedicated ingestion service. Caching reduces requests; it cannot grant
  quota or guarantee live access.

## Frontend

- Rebuild Vercel with `NEXT_PUBLIC_API_URL` pointing to the Render backend.
- The default basemap is OpenStreetMap with visible attribution and ordinary
  browser caching. No bulk downloading/offline prefetch. Review the OSM tile
  policy before higher-traffic deployment: https://operations.osmfoundation.org/policies/tiles/
- Optionally set `NEXT_PUBLIC_CARTO_API_KEY` for CARTO tiles (a browser-visible
  basemap key; apply domain restrictions through the provider). Both layers send
  the key. See https://www.carto.com/basemaps/apikey/.
- Dashboard/map reload data every five minutes while visible and upon returning
  to the tab. Dates use IST and the API base timestamp, not the rendering time.
- Polygon selection displays that ward's interpolated estimate. Opening the
  nearby station is a separate, explicitly labelled action.

## Accuracy limits and remaining model work

This change does not train or claim a validated ward prediction model. The 29
station-location inputs are not 29 independent ground measurements. Ward colours
interpolate PM2.5 concentration before applying the AQI curve, restrict inputs to
20 km, and disclose nearby input counts and unvalidated spatial uncertainty.
Identical regional inputs must still give identical outputs.

The live weather merge now uses UTC for both providers. The bundled legacy model
was trained with misaligned weather labels; retrain on corrected historical data
and compare chronological and withheld-station errors before claiming improved
forecast accuracy. WAQI sub-index inversion is approximate, not a raw CPCB
concentration feed. Prefer a licensed/raw concentration source for training and
official AQI computation with pollutant-specific averaging windows.

For a validated ward model, collect timestamped ground concentration history,
retain station IDs/coordinates, add weather and measured local spatial features,
train against ground concentrations, and validate on entire withheld stations and
future time blocks. Report uncertainty and coverage per ward. Do not add arbitrary
ward offsets, manufacture confidence bands, or treat the current AQI estimate as
official multi-pollutant AQI.

## Release checks

Run backend tests and frontend production build. After deployment, confirm the
observation timestamp advances, inspect any refresh error, and confirm sufficient
ground coverage. During a simulated provider outage the timestamp must stop
advancing and freshness must become stale. The historical demo must never be
labelled current. View the map at desktop/mobile widths and inspect a polygon.
