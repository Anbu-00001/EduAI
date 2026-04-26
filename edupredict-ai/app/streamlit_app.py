import streamlit as st
import pickle
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import shap
import os

st.set_page_config(
    page_title="EduPredict AI — Lender's Command Center",
    page_icon="🎓",
    layout="wide"
)

@st.cache_resource
def load_model():
    model = pickle.load(open("edupredict-ai/model/artifacts/model.pkl", "rb"))
    scaler = pickle.load(open("edupredict-ai/model/artifacts/scaler.pkl", "rb"))
    return model, scaler

@st.cache_data
def load_metrics():
    with open("edupredict-ai/model/artifacts/metrics.json") as f:
        return json.load(f)

# Wait until artifacts exist
if os.path.exists("edupredict-ai/model/artifacts/model.pkl") and os.path.exists("edupredict-ai/model/artifacts/metrics.json"):
    model, scaler = load_model()
    metrics = load_metrics()

    # ── Header ──────────────────────────────────────────────────
    st.title("🎓 EduPredict AI")
    st.subheader("Lender's Command Center — Future Earning Potential Engine")
    st.markdown("---")

    # ── Metric Cards (top row) ──────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Model AUC", f"{metrics['test_auc']:.4f}", 
                delta=f"+{metrics['test_auc'] - metrics['baseline_auc_cibil_only']:.4f} vs CIBIL baseline")
    with col2:
        st.metric("CV AUC (5-fold)", f"{metrics['cv_auc_mean']:.4f}",
                delta=f"±{metrics['cv_auc_std']:.4f}")
    with col3:
        st.metric("Training Samples", f"{metrics['train_size']:,}")
    with col4:
        st.metric("Test Samples", f"{metrics['test_size']:,}")

    st.markdown("---")

    # ── Main layout: Input | Result ─────────────────────────────
    left, right = st.columns([1, 1.2])

    with left:
        st.subheader("📋 Student Profile")
        
        st.markdown("**Academic Background**")
        cgpa = st.slider("CGPA (on 10-point scale)", 4.0, 10.0, 7.5, 0.1)
        backlogs = st.slider("Academic Backlogs", 0, 8, 0)
        
        st.markdown("**Experience**")
        internships = st.slider("Number of Internships", 0, 6, 2)
        projects = st.slider("Projects / Hackathons", 0, 10, 3)
        
        st.markdown("**Field & Placement Context**")
        field_demand = st.selectbox(
            "Degree Field",
            options=[
                "Computer Science / IT",
                "Data Science / AI",
                "MBA / Finance",
                "Mechanical Engineering",
                "Electrical Engineering",
                "Civil Engineering",
                "Biotechnology / Life Sciences",
            ]
        )
        DEMAND_MAP = {
            "Computer Science / IT": 0.95,
            "Data Science / AI": 0.90,
            "MBA / Finance": 0.65,
            "Mechanical Engineering": 0.55,
            "Electrical Engineering": 0.50,
            "Civil Engineering": 0.35,
            "Biotechnology / Life Sciences": 0.25,
        }
        SALARY_MAP = {
            "Computer Science / IT": 0.88,
            "Data Science / AI": 0.92,
            "MBA / Finance": 0.75,
            "Mechanical Engineering": 0.60,
            "Electrical Engineering": 0.58,
            "Civil Engineering": 0.42,
            "Biotechnology / Life Sciences": 0.38,
        }
        
        college_placement_rate = st.slider("College Placement Rate (%)", 20, 100, 75)
        
        st.markdown("**Loan Details**")
        loan_amount = st.number_input("Loan Amount (INR)", 
                                    min_value=50000, max_value=5000000, 
                                    value=500000, step=50000,
                                    format="%d")

    with right:
        st.subheader("🔍 Risk Assessment")
        
        if st.button("Assess Loan Risk", type="primary", use_container_width=True):
            # Compute features
            cgpa_norm = cgpa / 10.0
            internship_weight = min(internships / 3.0, 1.0)
            demand_proxy = DEMAND_MAP[field_demand]
            salary_norm = SALARY_MAP[field_demand]
            placement_rate_norm = college_placement_rate / 100.0
            
            potential_score = (
                cgpa_norm * 0.35 +
                internship_weight * 0.25 +
                placement_rate_norm * 0.25 +
                salary_norm * 0.15
            )
            
            features = np.array([[
                cgpa_norm,
                internships,
                backlogs,
                salary_norm,
                potential_score,
                demand_proxy,
                placement_rate_norm
            ]])
            
            features_sc = scaler.transform(features)
            prob = model.predict_proba(features_sc)[0][1]
            
            # Risk tier
            if prob >= 0.72:
                risk_tier = "🟢 GREEN — Low Risk"
                tier_color = "success"
                recommendation = "APPROVE — Strong earning trajectory"
            elif prob >= 0.50:
                risk_tier = "🟡 AMBER — Moderate Risk"
                tier_color = "warning"
                recommendation = "APPROVE WITH CONDITIONS — Monitor repayment quarterly"
            else:
                risk_tier = "🔴 RED — High Risk"
                tier_color = "error"
                recommendation = "DECLINE OR REQUIRE CO-SIGNER"
            
            # Display result
            st.metric("Repayment Probability", f"{prob:.1%}")
            st.metric("Potential Score", f"{potential_score:.2f} / 1.00")
            
            if tier_color == "success":
                st.success(f"**Risk Tier:** {risk_tier}")
                st.success(f"**Recommendation:** {recommendation}")
            elif tier_color == "warning":
                st.warning(f"**Risk Tier:** {risk_tier}")
                st.warning(f"**Recommendation:** {recommendation}")
            else:
                st.error(f"**Risk Tier:** {risk_tier}")
                st.error(f"**Recommendation:** {recommendation}")
            
            st.progress(float(prob))
            
            # SHAP waterfall
            st.markdown("**Why this score? (SHAP Explainability)**")
            try:
                explainer = shap.TreeExplainer(model)
                shap_vals = explainer.shap_values(features_sc)
                
                fig, ax = plt.subplots(figsize=(8, 4))
                feature_names = metrics["feature_cols"]
                importances = dict(zip(feature_names, shap_vals[0]))
                sorted_imp = sorted(importances.items(), key=lambda x: abs(x[1]), reverse=True)
                
                names = [x[0].replace("_", " ") for x in sorted_imp]
                vals = [x[1] for x in sorted_imp]
                colors = ["#22c55e" if v > 0 else "#ef4444" for v in vals]
                
                ax.barh(names, vals, color=colors, height=0.6)
                ax.axvline(0, color="gray", linewidth=0.8, linestyle="--")
                ax.set_xlabel("SHAP Value (impact on repayment probability)")
                ax.set_title("Feature Contributions for This Student")
                ax.tick_params(labelsize=9)
                plt.tight_layout()
                st.pyplot(fig)
                plt.close()
            except Exception as e:
                st.info("SHAP visualization unavailable for this prediction.")
            
            # Loan details
            st.markdown("---")
            emi_estimate = loan_amount * 0.023
            st.markdown(f"**Loan:** ₹{loan_amount:,} | "
                    f"**Est. Monthly EMI:** ₹{emi_estimate:,.0f} | "
                    f"**Field:** {field_demand}")

    # ── Bottom: SHAP global summary ──────────────────────────────
    st.markdown("---")
    st.subheader("📊 Global Feature Importance")
    if os.path.exists("edupredict-ai/model/artifacts/shap_summary.png"):
        col_a, col_b = st.columns([1, 1])
        with col_a:
            st.image("edupredict-ai/model/artifacts/shap_summary.png", 
                    caption="SHAP Feature Importance (training set)")
        with col_b:
            st.markdown("""
            **How to read this chart:**
            - Bars show each feature's average impact on the model's output
            - Longer bar = stronger influence on repayment prediction
            - Green features push toward "will repay"
            - Red features push toward "will default"
            
            **Key insight:** This model uses earning potential signals 
            (CGPA, field demand, salary trajectory) — not past credit history. 
            """)
else:
    st.warning("Model artifacts not found. Please run the training script first.")
