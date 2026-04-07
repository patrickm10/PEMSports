import os
import joblib
import logging
import polars as pl
import xgboost as xgb
import shap
from typing import List, Tuple
from src.pipelines.ml_features import build_ml_features

logger = logging.getLogger(__name__)

# Model Registry Configuration
MODEL_DIR = "src/backend/models/v1"
FORECAST_DIR = "data/forecasts"

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(FORECAST_DIR, exist_ok=True)

def train_alpha_model(pos: str) -> None:
    """
    Trains a position-specific XGBoost model to predict 
    situational points performance deltas.
    """
    pos = pos.upper()
    logger.info(f"Starting training pipeline for {pos}...")
    
    # 1. Load Features
    df = build_ml_features(pos)
    if df.is_empty():
        logger.warning(f"No data for {pos}. Skipping.")
        return

    # 2. Prepare Data (X and y)
    # Define features to ignore (ID/Target)
    drop_cols = ["player_id", "player", "year", "week", "points_delta", "fpts", "fpts_ppr", "season_avg_fpts"]
    feature_cols = [c for c in df.columns if c not in drop_cols]
    
    X = df.select(feature_cols).to_pandas()
    y = df.select("points_delta").to_pandas()

    # 3. Train XGBoost
    model = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        objective="reg:squarederror"
    )
    model.fit(X, y)
    
    # 4. Persistence
    model_path = os.path.join(MODEL_DIR, f"{pos.lower()}_v1.joblib")
    joblib.dump(model, model_path)
    logger.info(f"Successfully saved {pos} model to {model_path}")

    # 5. Generate Weekly Forecasts with SHAP
    generate_forecasts(df, model, feature_cols, pos)

def generate_forecasts(df: pl.DataFrame, model: xgb.XGBRegressor, features: List[str], pos: str) -> None:
    """
    Generates weekly projections and translates SHAP values 
    into human-readable insight flags.
    """
    import pandas as pd
    X_full = df.select(features).to_pandas()
    
    # Calculate SHAP Explanations
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_full)
    
    # Get top 2 features per row for 'insight_flags'
    insight_flags = []
    preds = model.predict(X_full)
    
    for i in range(len(shap_values)):
        # Get feature importance for this specific row
        row_shap = shap_values[i]
        top_indices = row_shap.argsort()[-2:][::-1] # indices of top 2 positive contributors
        
        flags = []
        for idx in top_indices:
            feat_name = features[idx]
            val = row_shap[idx]
            if val > 0.1: # Only add labels if they are meaningful contributors
                flags.append(f"{feat_name.replace('_', ' ').title()} (+{val:.1f})")
        
        insight_flags.append(",".join(flags))

    # 6. Build Final Forecast DataFrame
    forecast_df = df.select(["player_id", "year", "week", "fpts", "season_avg_fpts"]).with_columns([
        pl.Series("predicted_alpha", preds).round(2),
        pl.Series("insight_flags", insight_flags)
    ])
    
    # Final 'Smart Projection' calculated by baseline + predicted Situational Delta
    forecast_df = forecast_df.with_columns([
        (pl.col("season_avg_fpts") + pl.col("predicted_alpha")).round(2).alias("smart_projection")
    ])

    save_path = os.path.join(FORECAST_DIR, f"{pos.lower()}_alpha.parquet")
    forecast_df.write_parquet(save_path)
    logger.info(f"Forecasts written for {pos} to {save_path}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Orchestrate for all core positions
    for p in ["QB", "RB", "WR", "TE"]:
        train_alpha_model(p)
