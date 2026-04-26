import pandas as pd
import numpy as np
import xgboost as xgb
import pickle
import json
import os
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix
import shap
import matplotlib.pyplot as plt

FEATURE_COLS = [
    "cgpa_normalized", "internships_count", "backlogs",
    "median_salary_normalized", "potential_score", "demand_proxy",
    "placement_rate_for_field"
]
TARGET_COL = "repaid_loan"

def train_and_evaluate():
    # Load data
    df = pd.read_csv("edupredict-ai/data/processed/features.csv")
    print(f"Dataset shape: {df.shape}")
    print(f"Class distribution:\n{df[TARGET_COL].value_counts()}")
    
    X = df[FEATURE_COLS]
    y = df[TARGET_COL]
    
    # Calculate class imbalance ratio
    neg, pos = (y == 0).sum(), (y == 1).sum()
    spw = neg / pos if pos > 0 else 1.0
    print(f"scale_pos_weight set to: {spw:.2f}")
    
    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Scale features
    scaler = StandardScaler()
    X_train_sc = scaler.fit_transform(X_train)
    X_test_sc = scaler.transform(X_test)
    
    # Model
    model = xgb.XGBClassifier(
        n_estimators=400,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=spw,
        use_label_encoder=False,
        eval_metric="auc",
        random_state=42,
        early_stopping_rounds=30
    )
    
    model.fit(
        X_train_sc, y_train,
        eval_set=[(X_test_sc, y_test)],
        verbose=50
    )
    
    # Evaluate
    y_pred_proba = model.predict_proba(X_test_sc)[:, 1]
    y_pred = (y_pred_proba >= 0.5).astype(int)
    
    auc = roc_auc_score(y_test, y_pred_proba)
    
    # 5-fold cross-validation AUC
    cv_scores = cross_val_score(
        xgb.XGBClassifier(
            n_estimators=400, max_depth=5, learning_rate=0.05,
            scale_pos_weight=spw, use_label_encoder=False, eval_metric="auc"
        ), 
        X_train_sc, y_train, 
        cv=StratifiedKFold(5, shuffle=True, random_state=42),
        scoring="roc_auc"
    )
    
    print(f"\n{'='*40}")
    print(f"TEST AUC:         {auc:.4f}")
    print(f"CV AUC (5-fold):  {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
    print(f"\nClassification Report:\n{classification_report(y_test, y_pred)}")
    print(f"\nConfusion Matrix:\n{confusion_matrix(y_test, y_pred)}")
    print(f"{'='*40}\n")
    
    # SHAP explanability
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test_sc)
    
    # Save SHAP summary plot
    os.makedirs("edupredict-ai/model/artifacts", exist_ok=True)
    plt.figure(figsize=(10, 6))
    shap.summary_plot(
        shap_values, X_test,
        feature_names=FEATURE_COLS,
        plot_type="bar",
        show=False
    )
    plt.title("Feature Importance (SHAP Values) — EduPredict AI")
    plt.tight_layout()
    plt.savefig("edupredict-ai/model/artifacts/shap_summary.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("SHAP summary plot saved to edupredict-ai/model/artifacts/shap_summary.png")
    
    # Save SHAP waterfall for a sample high-risk student
    sample_idx = np.where(y_pred_proba < 0.4)[0]
    if len(sample_idx) > 0:
        plt.figure(figsize=(10, 5))
        shap.waterfall_plot(
            shap.Explanation(
                values=shap_values[sample_idx[0]],
                base_values=explainer.expected_value,
                data=X_test.iloc[sample_idx[0]],
                feature_names=FEATURE_COLS
            ),
            show=False
        )
        plt.title("SHAP Waterfall — High Risk Student Example")
        plt.tight_layout()
        plt.savefig("edupredict-ai/model/artifacts/shap_waterfall_highrisk.png", dpi=150, bbox_inches="tight")
        plt.close()
    
    # Save model artifacts
    pickle.dump(model, open("edupredict-ai/model/artifacts/model.pkl", "wb"))
    pickle.dump(scaler, open("edupredict-ai/model/artifacts/scaler.pkl", "wb"))
    
    # Save metrics as JSON
    metrics = {
        "test_auc": round(auc, 4),
        "cv_auc_mean": round(cv_scores.mean(), 4),
        "cv_auc_std": round(cv_scores.std(), 4),
        "train_size": int(X_train.shape[0]),
        "test_size": int(X_test.shape[0]),
        "feature_cols": FEATURE_COLS,
        "baseline_auc_cibil_only": 0.62
    }
    json.dump(metrics, open("edupredict-ai/model/artifacts/metrics.json", "w"), indent=2)
    print("All artifacts saved to edupredict-ai/model/artifacts/")
    
    return model, scaler, metrics

if __name__ == "__main__":
    train_and_evaluate()
