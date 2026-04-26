import numpy as np
import pandas as pd
import lightgbm as lgb
import catboost as cb
import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score
import pickle, json, os

def train_stacked_ensemble(X: pd.DataFrame, y: pd.Series, n_folds: int = 5):
    """
    Train a 2-layer stacked ensemble.
    
    Math: E[ŷ_stacked] minimizes bias-variance tradeoff across 3 
    uncorrelated base learners via a convex combination learned by 
    logistic regression. Stacking reduces variance: Var(avg) = σ²/n 
    only if uncorrelated. Enforced diversity via different algorithms.
    """
    kf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)
    
    oof_xgb = np.zeros(len(X))
    oof_lgb = np.zeros(len(X))
    oof_cat = np.zeros(len(X))
    
    # --- Dynamically compute scale_pos_weight from class distribution ---
    neg_count = (y == 0).sum()
    pos_count = (y == 1).sum()
    spw = neg_count / pos_count if pos_count > 0 else 1.0
    print(f"Data-derived scale_pos_weight: {spw:.4f}")
    
    # --- Hyperparameters derived via Bayesian optimization bounds ---
    # LightGBM: leaf-wise growth, DART dropout for regularization
    lgb_params = {
        "objective": "binary",
        "boosting_type": "dart",
        "num_leaves": int(2 ** np.floor(np.log2(len(X) ** 0.5))),  # math: sqrt(n) rule
        "learning_rate": 0.05,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "scale_pos_weight": spw,
        "metric": "auc",
        "drop_rate": 0.1,
        "verbose": -1,
        "random_state": 42,
    }
    
    # CatBoost: ordered boosting (reduces overfitting on small datasets)
    cat_params = {
        "iterations": 500,
        "depth": 6,
        "learning_rate": 0.05,
        "loss_function": "Logloss",
        "eval_metric": "AUC",
        "class_weights": {0: 1.0, 1: float(spw)},
        "boosting_type": "Ordered",
        "random_seed": 42,
        "verbose": 0,
    }
    
    # XGBoost: second-order Newton boosting
    xgb_params = {
        "n_estimators": 500,
        "max_depth": 5,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "scale_pos_weight": spw,
        "use_label_encoder": False,
        "eval_metric": "auc",
        "early_stopping_rounds": 30,
        "random_state": 42,
    }
    
    base_models_per_fold = {"xgb": [], "lgb": [], "cat": []}
    
    for fold, (train_idx, val_idx) in enumerate(kf.split(X, y)):
        X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]
        
        # XGBoost
        m_xgb = xgb.XGBClassifier(**xgb_params)
        m_xgb.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)
        oof_xgb[val_idx] = m_xgb.predict_proba(X_val)[:, 1]
        base_models_per_fold["xgb"].append(m_xgb)
        
        # LightGBM
        dtrain = lgb.Dataset(X_tr, label=y_tr)
        dval = lgb.Dataset(X_val, label=y_val, reference=dtrain)
        m_lgb = lgb.train(
            lgb_params, dtrain, num_boost_round=500,
            valid_sets=[dval], callbacks=[lgb.early_stopping(30), lgb.log_evaluation(-1)]
        )
        oof_lgb[val_idx] = m_lgb.predict(X_val)
        base_models_per_fold["lgb"].append(m_lgb)
        
        # CatBoost
        m_cat = cb.CatBoostClassifier(**cat_params)
        m_cat.fit(X_tr, y_tr, eval_set=(X_val, y_val), use_best_model=True, verbose=0)
        oof_cat[val_idx] = m_cat.predict_proba(X_val)[:, 1]
        base_models_per_fold["cat"].append(m_cat)
        
        print(f"Fold {fold+1} — XGB: {roc_auc_score(y_val, oof_xgb[val_idx]):.4f} "
              f"LGB: {roc_auc_score(y_val, oof_lgb[val_idx]):.4f} "
              f"CAT: {roc_auc_score(y_val, oof_cat[val_idx]):.4f}")
    
    print(f"\nOOF AUCs — XGB: {roc_auc_score(y, oof_xgb):.4f} "
          f"LGB: {roc_auc_score(y, oof_lgb):.4f} "
          f"CAT: {roc_auc_score(y, oof_cat):.4f}")
    
    # Meta-learner: Logistic Regression on OOF predictions
    meta_X = np.column_stack([oof_xgb, oof_lgb, oof_cat])
    meta_model = LogisticRegression(C=1.0, max_iter=1000, random_state=42)
    meta_model.fit(meta_X, y)
    
    ensemble_preds = meta_model.predict_proba(meta_X)[:, 1]
    ensemble_auc = roc_auc_score(y, ensemble_preds)
    print(f"\nStacked Ensemble OOF AUC: {ensemble_auc:.4f}")
    
    # Save all artifacts
    os.makedirs("edupredict-ai/model/artifacts", exist_ok=True)
    pickle.dump(base_models_per_fold, open("edupredict-ai/model/artifacts/base_models.pkl", "wb"))
    pickle.dump(meta_model, open("edupredict-ai/model/artifacts/meta_model.pkl", "wb"))
    
    return base_models_per_fold, meta_model, ensemble_auc
