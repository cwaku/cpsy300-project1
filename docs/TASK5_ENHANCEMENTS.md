# Task 5: Enhancement Research and Implementation

## Options chosen

1. **Multi-stage Docker builds and smaller container images** (applied to Task 2 and Task 3).
2. **Optimising data processing logic** (applied to the Task 3 serverless function).

We did not pick the cold-start option because our serverless function is a plain Python
script invoked against a local Azurite emulator, so there is no real cold start to measure
or improve honestly.

## Research conducted

**Option 1.** We reviewed the Docker documentation on multi-stage builds and the
`python:*-slim` images, and inspected our own dependency tree with `uv pip tree`. Two
findings drove the design: (a) the single `requirements.txt` was installing the full Azure
SDK, `cryptography`, `requests` and `watchdog` into the analysis image even though
`data_analysis.py` imports none of them, and installing matplotlib, seaborn, fonttools and
pillow into the function image even though `lambda_function.py` only needs pandas and the
Blob SDK; (b) `azure-functions` and `werkzeug` were pinned but never imported by any script.

**Option 2.** We profiled the function's load-and-aggregate path with `time.perf_counter`
and `DataFrame.memory_usage(deep=True)`. The function only uses four of the eight CSV
columns, yet it parsed all eight, kept `Recipe_name` and `Cuisine_type` as Python string
objects, and filled missing values with a per-column loop. Pandas documentation recommends
`usecols`, categorical dtypes for low-cardinality text, and vectorised operations for
exactly this pattern.

## Improvements applied

**Option 1**

- Split `requirements.txt` into `requirements-analysis.txt` and `requirements-function.txt`
  (same version pins, subsets only). The full file remains for local development and CI.
- Rewrote the `Dockerfile` as a multi-stage build: two builder stages install dependencies
  with `pip install --prefix=/install`, and two slim runtime stages copy only the resulting
  site-packages plus the scripts they need. `docker build .` still produces the analysis
  image by default; `docker build --target function` produces the function image.
- `docker-compose.yml` now builds the `serverless-function` service from the `function`
  target instead of reusing the analysis image.
- The CI pipeline builds both targets, prints `docker image ls` so the sizes are recorded
  in the run log, and smoke-tests that the function image imports cleanly.

**Option 2**

- `lambda_function.py` now reads only the four required columns with `usecols`, loads
  `Diet_type` as a `category`, fills missing macronutrients in one vectorised statement,
  and aggregates with `groupby(observed=True)`.

## Impact

| Measurement (installed Python packages, pinned versions) | Before | After | Change |
|---|---|---|---|
| Analysis image dependencies | 223 MB, 29 packages | 174 MB, 13 packages | -49 MB (-22%) |
| Function image dependencies | 223 MB, 29 packages | 121 MB, 17 packages | -102 MB (-46%) |

Package sizes were measured as the `site-packages` footprint of a fresh virtual environment
built from each requirements file with the same version pins. Final Docker image sizes are
printed by the "Report image sizes" step of the CI pipeline.

| Function processing (7,806 rows, median of 30 runs) | Before | After | Change |
|---|---|---|---|
| CSV parse (`read_csv`) | 5.4 ms | 3.7 ms | -31% |
| End to end (parse, fill, aggregate) | 6.3 ms | 4.7 ms | 1.34x faster |
| DataFrame memory | 2.93 MB | 0.20 MB | -93% |

Results are numerically identical before and after. The absolute times are small on this
dataset, but the savings scale linearly with row count: the same changes on a dataset ten
times larger would avoid parsing roughly 27 MB of unused text and keep the working set
small enough to stay within the memory limits of a consumption-plan Azure Function.
Smaller images also mean faster pulls on every CI run and every deployment.
