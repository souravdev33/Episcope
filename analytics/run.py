"""Aggregate analytics and dashboard exports. Ground truth is never read here."""
import argparse
import json
import shutil
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

DISEASES = ["dengue", "diarrhoea", "influenza", "malaria"]
WEATHER_COLUMNS = ["precipitation_mm", "temperature_c", "relative_humidity_pct"]

def make_continuous_weeks(group, district, disease):
    group = group.copy()
    group["week_start"] = [
        datetime.combine(date.fromisocalendar(int(year), int(week), 1), datetime.min.time())
        for year, week in zip(group.epi_year, group.epi_week)
    ]
    group = group.sort_values("week_start").set_index("week_start")
    calendar = pd.date_range(group.index.min(), group.index.max(), freq="W-MON")
    group = group.reindex(calendar)
    iso = calendar.isocalendar()
    group["epi_year"] = iso.year.to_numpy()
    group["epi_week"] = iso.week.to_numpy()
    group["district"] = district
    group["disease"] = disease
    group["cases"] = group["cases"].fillna(0)
    group["admissions"] = group["admissions"].fillna(0)
    if all(column in group for column in WEATHER_COLUMNS):
        group[WEATHER_COLUMNS] = group[WEATHER_COLUMNS].interpolate(limit_direction="both")
    return group.reset_index(names="week_start")

def fit_weather_forecast(x, horizon=4):
    """Fit a small ridge-stabilized district model using lagged rain/temp/humidity."""
    if not all(column in x for column in WEATHER_COLUMNS):
        return None
    model = x.copy()
    model["case_lag1"] = model["cases"].shift(1)
    model["rain_lag4"] = model["precipitation_mm"].shift(4)
    model["temp_lag6"] = model["temperature_c"].shift(6)
    model["humidity_lag4"] = model["relative_humidity_pct"].shift(4)
    features = ["case_lag1", "rain_lag4", "temp_lag6", "humidity_lag4"]
    train = model.dropna(subset=features + ["cases"])
    if len(train) < 30:
        return None
    matrix = train[features].to_numpy(dtype=float)
    center = matrix.mean(axis=0)
    scale = matrix.std(axis=0)
    scale[scale == 0] = 1
    standardized = (matrix - center) / scale
    design = np.column_stack([np.ones(len(standardized)), standardized])
    penalty = np.diag([0.0, 2.0, 2.0, 2.0, 2.0])
    beta = np.linalg.solve(design.T @ design + penalty, design.T @ train["cases"].to_numpy(float))
    residuals = train["cases"].to_numpy(float) - design @ beta
    error_sd = max(1.0, float(np.std(residuals)))
    predictions = []
    cases = x["cases"].to_numpy(dtype=float)
    rain = x["precipitation_mm"].to_numpy(dtype=float)
    temp = x["temperature_c"].to_numpy(dtype=float)
    humidity = x["relative_humidity_pct"].to_numpy(dtype=float)
    for step in range(1, horizon + 1):
        rain_index = min(len(x) - 1, max(0, len(x) + step - 5))
        temp_index = min(len(x) - 1, max(0, len(x) + step - 7))
        lag_case = cases[-1] if step == 1 else predictions[-1][0]
        values = np.array([lag_case, rain[rain_index], temp[temp_index], humidity[rain_index]], dtype=float)
        values = np.where(np.isfinite(values), values, center)
        row = np.r_[1.0, (values - center) / scale]
        estimate = max(0.0, float(row @ beta))
        predictions.append((estimate, error_sd))
    return predictions

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/lake")
    parser.add_argument("--output", default="data/serving")
    args = parser.parse_args()
    from pyspark.sql import SparkSession

    spark = (SparkSession.builder.appName("EpiScopeAnalytics").master("local[*]")
             .config("spark.sql.shuffle.partitions", "8").getOrCreate())
    source = Path(args.input)
    output = Path(args.output)
    rows = spark.read.parquet(str(source / "gold" / "weekly")).toPandas()
    population_path = source.parent / "input" / "population.csv"
    population_frame = pd.read_csv(population_path)
    population = population_frame.set_index("district")["population"].astype(float).to_dict()

    aggregation = {"cases": ("cases", "sum"), "admissions": ("admissions", "sum")}
    for column in WEATHER_COLUMNS:
        if column in rows.columns:
            aggregation[column] = (column, "mean")
    grouped = rows.groupby(["district", "disease", "epi_year", "epi_week"],
                           as_index=False).agg(**aggregation)
    output.mkdir(parents=True, exist_ok=True)
    alerts, forecasts, heatmap, allocations, latest = [], [], [], [], {}
    for (district, disease), raw_group in grouped.groupby(["district", "disease"]):
        x = make_continuous_weeks(raw_group, district, disease)
        values = x["cases"].to_numpy(dtype=float)
        x["baseline"] = x["cases"].shift(1).rolling(8, min_periods=4).mean()
        x["sd"] = x["cases"].shift(1).rolling(8, min_periods=4).std().fillna(1).clip(lower=1)
        x["z"] = (x["cases"] - x["baseline"]) / x["sd"]
        x["alert"] = x["z"] >= 2.5
        for _, row in x.iterrows():
            count = int(row.cases)
            heatmap.append({"district": district, "disease": disease,
                            "year": int(row.epi_year), "week": int(row.epi_week),
                            "cases": count})
            if bool(row.alert):
                alerts.append({"district": district, "disease": disease,
                               "year": int(row.epi_year), "week": int(row.epi_week),
                               "observed": count, "expected": round(float(row.baseline), 1),
                               "score": round(float(row.z), 2),
                               "method": "8-week EARS-like z-score"})
        climate_model = fit_weather_forecast(x)
        recent_base = float(np.nanmean(values[-8:])) if len(values) else 0.0
        prior_predictions = []
        for horizon in range(1, 5):
            annual = values[-52 + horizon - 1] if len(values) >= 52 + horizon else recent_base
            if climate_model:
                estimate, error_sd = climate_model[horizon - 1]
                method = "district ridge model: case lag 1, rain lag 4, temperature lag 6, humidity lag 4"
            else:
                estimate = max(0.0, .75 * float(annual) + .25 * recent_base)
                error_sd = float(np.sqrt(estimate + 1))
                method = "seasonal-naive/recent-level blend (weather unavailable)"
            prior_predictions.append(estimate)
            center = max(0, round(estimate))
            interval = max(1.0, 1.28 * error_sd)
            forecasts.append({"district": district, "disease": disease,
                              "horizon": horizon, "mean": center,
                              "lower80": max(0, round(estimate - interval)),
                              "upper80": round(estimate + interval),
                              "method": method})
        latest[(district, disease)] = int(values[-1]) if len(values) else 0

    case_totals = {district: sum(value for (name, _), value in latest.items() if name == district)
                   for district in population}
    demand = {district: max(1, int(case_totals.get(district, 0) * .2 +
                                  population[district] / 100000))
              for district in population}
    weights = {district: 1.5 if district in
               ["Bandarban", "Rangamati", "Khagrachhari"] else 1.0
               for district in population}
    total_budget = 200000
    denominator = sum(weights[d] * demand[d] for d in population)
    population_total = sum(population.values())
    for district in population:
        need = demand[district]
        equity_floor = int(total_budget * population[district] / population_total * .15)
        recommended = min(need, max(equity_floor,
                         int(total_budget * weights[district] * need / denominator)))
        allocations.append({"district": district, "demand_units": need,
                            "current_stock_units": max(0, int(need * .35)),
                            "recommended_units": recommended,
                            "budget_cost": recommended, "population": population[district]})
    budget_curve = []
    for budget in [50000, 100000, 150000, 200000, 250000]:
        funded = sum(min(row["demand_units"],
                         int(budget * row["demand_units"] /
                             sum(item["demand_units"] for item in allocations)))
                     for row in allocations)
        budget_curve.append({"budget": budget, "units_funded": funded,
                             "equity_floor_share": .15})
    calendar = [{"division": "National", "disease": disease,
                 "prepare_month": "May", "campaign_month": "June",
                 "rationale": "seasonal planning hypothesis; validate before use"}
                for disease in DISEASES]

    for row in heatmap:
        if 0 < row["cases"] < 5:
            row["cases"] = None
            row["suppressed"] = True
        else:
            row["suppressed"] = False
    for row in forecasts:
        for key in ("mean", "lower80", "upper80"):
            if 0 < row[key] < 5:
                row[key] = None

    boundary_source = source / "reference" / "boundaries.geojson"
    boundaries = None
    if boundary_source.exists():
        boundaries = json.loads(boundary_source.read_text(encoding="utf-8"))
        shutil.copy2(boundary_source, output / "districts.geojson")
    metadata_source = source / "reference" / "source_metadata.json"
    source_metadata = None
    if metadata_source.exists():
        source_metadata = json.loads(metadata_source.read_text(encoding="utf-8"))
        shutil.copy2(metadata_source, output / "source_metadata.json")

    payload = {"generated_at": datetime.now().astimezone().isoformat(),
               "synthetic": True, "districts": list(population),
               "diseases": DISEASES, "population": population,
               "heatmap": heatmap, "alerts": alerts, "forecasts": forecasts,
               "allocations": allocations, "budget_curve": budget_curve,
               "calendar": calendar,
               "source_metadata": source_metadata,
               "boundary_source_loaded": boundaries is not None,
               "quality": json.loads((source / "gold" / "quality_report.json")
                                     .read_text(encoding="utf-8"))}
    (output / "dashboard.json").write_text(json.dumps(payload, allow_nan=False), encoding="utf-8")
    print(f"Exported {len(grouped)} district-disease-week rows, {len(alerts)} prototype threshold flags.")
    if source_metadata:
        print("Serving source metadata for public S1-S3 inputs.")
    spark.stop()

if __name__ == "__main__":
    main()



