from flask import Flask, render_template, jsonify
import numpy as np
import pandas as pd
from datetime import datetime

app = Flask(__name__)

def generate_dummy_credit_risk_data(seed: int = 42):
    """
    Dummy credit risk dataset aligned to a corporate energy/trading context.
    Fields commonly used in credit risk analytics: EAD, PD, LGD, EL, rating, limits, DPD, etc.
    """
    rng = np.random.default_rng(seed)

    n = 60  # counterparties
    names = [
        "NorthSea Logistics", "BlueWave Trading", "Orion Petrochem", "Delta Refining",
        "Apex Shipping", "GreenGrid Utilities", "Meridian Metals", "Polar LNG",
        "Horizon Aviation Fuel", "Caspian Drilling", "Atlas Lubricants", "Sierra Chemicals",
        "Helios Power", "Nova Commodity", "Trident Marine", "Summit Pipeline",
        "Vega Mining", "Coastal Bunkers", "Sequoia Renewables", "Harbor Storage"
    ]
    # pad to n with simple pattern
    while len(names) < n:
        names.append(f"Counterparty {len(names)+1:02d}")

    regions = rng.choice(
        ["UK", "EU", "Americas", "Middle East", "Asia"],
        size=n,
        p=[0.22, 0.28, 0.22, 0.13, 0.15]
    )
    industries = rng.choice(
        ["Trading", "Shipping", "Refining", "Upstream", "Utilities", "Chemicals"],
        size=n
    )

    ratings = rng.choice(
        ["AAA", "AA", "A", "BBB", "BB", "B", "CCC"],
        size=n,
        p=[0.05, 0.10, 0.18, 0.28, 0.20, 0.14, 0.05]
    )

    # Map rating to PD bands (annual) typical-ish for demo
    pd_map = {
        "AAA": (0.0002, 0.0010),
        "AA":  (0.0005, 0.0025),
        "A":   (0.0015, 0.0060),
        "BBB": (0.0060, 0.0200),
        "BB":  (0.0200, 0.0600),
        "B":   (0.0600, 0.1500),
        "CCC": (0.1500, 0.3500),
    }

    pd_vals = np.array([rng.uniform(*pd_map[r]) for r in ratings])

    # LGD: secured/short-term often lower; keep a realistic range for corp credit demo
    lgd = rng.uniform(0.25, 0.65, size=n)

    # Limits and EAD (Exposure at Default) in USD millions for simplicity
    credit_limit = rng.uniform(10, 250, size=n)  # $m
    utilization = np.clip(rng.normal(0.55, 0.20, size=n), 0.05, 0.98)
    ead = credit_limit * utilization

    # Days past due (DPD) — mostly current, some late
    dpd = rng.choice([0, 5, 15, 30, 60, 90], size=n, p=[0.68, 0.10, 0.08, 0.08, 0.04, 0.02])

    # Expected Loss (EL) = EAD * PD * LGD (still in $m)
    el = ead * pd_vals * lgd

    df = pd.DataFrame({
        "counterparty": names[:n],
        "region": regions,
        "industry": industries,
        "rating": ratings,
        "credit_limit_m": np.round(credit_limit, 2),
        "utilization_pct": np.round(utilization * 100, 1),
        "ead_m": np.round(ead, 2),
        "pd_pct": np.round(pd_vals * 100, 2),
        "lgd_pct": np.round(lgd * 100, 1),
        "dpd": dpd,
        "expected_loss_m": np.round(el, 3),
    })

    # Monthly EL trend (last 12 months) - ALWAYS 12 points
    end_month = pd.Timestamp.today().normalize().replace(day=1)
    start_month = end_month - pd.DateOffset(months=11)
    months = pd.date_range(start=start_month, periods=12, freq="MS")

    base = float(df["expected_loss_m"].sum())
    drift = np.linspace(-0.06, 0.08, 12)
    noise = rng.normal(0, 0.03, 12)

    trend = base * (1 + drift + noise)
    trend = np.clip(trend, base * 0.6, base * 1.6)

    trend_df = pd.DataFrame({
        "month": months.strftime("%b %Y").tolist(),
        "portfolio_expected_loss_m": np.round(trend, 3).tolist()
    })

    return df, trend_df

# Generate once for a stable demo
DATA_DF, TREND_DF = generate_dummy_credit_risk_data(seed=42)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/portfolio")
def portfolio():
    df = DATA_DF.copy()

    kpis = {
        "total_exposure_m": round(float(df["ead_m"].sum()), 2),
        "total_expected_loss_m": round(float(df["expected_loss_m"].sum()), 3),
        "avg_pd_pct": round(float(df["pd_pct"].mean()), 2),
        "avg_lgd_pct": round(float(df["lgd_pct"].mean()), 1),
        "counterparties": int(df.shape[0]),
    }

    exposure_by_region = (df.groupby("region")["ead_m"].sum().sort_values(ascending=False)).round(2)
    el_by_rating = (df.groupby("rating")["expected_loss_m"].sum()).reindex(
        ["AAA", "AA", "A", "BBB", "BB", "B", "CCC"]
    ).fillna(0).round(3)

    top10 = df.sort_values("ead_m", ascending=False).head(10)

    payload = {
        "kpis": kpis,
        "charts": {
            "exposure_by_region": {
                "labels": exposure_by_region.index.tolist(),
                "values": exposure_by_region.values.tolist()
            },
            "expected_loss_by_rating": {
                "labels": el_by_rating.index.tolist(),
                "values": el_by_rating.values.tolist()
            },
            "monthly_el_trend": {
                "labels": TREND_DF["month"].tolist(),
                "values": TREND_DF["portfolio_expected_loss_m"].tolist()
            }
        },
        "top10": top10.to_dict(orient="records"),
        "asof": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    return jsonify(payload)

if __name__ == "__main__":
    app.run(debug=True)
