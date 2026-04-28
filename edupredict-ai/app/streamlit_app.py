import streamlit as st
import json
import os
import requests
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="EduPredict AI — Lender's Command Center",
    page_icon="🎓",
    layout="wide"
)

API_URL = os.environ.get("API_URL", "http://localhost:8000")
API_KEY = "ep_demo_dashboard_key_2026"

@st.cache_data
def load_metrics():
    try:
        with open("model/artifacts/metrics.json") as f:
            return json.load(f)
    except Exception:
        return None

metrics = load_metrics()

# ── Header ──────────────────────────────────────────────────
st.title("🎓 EduPredict AI")
st.subheader("Lender's Command Center — Future Earning Potential Engine")
st.markdown("---")

if metrics:
    # ── Metric Cards (top row) ──────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Model AUC (Graph)", f"{metrics.get('graph_regularised_auc', 0):.4f}", 
                delta=f"+{metrics.get('auc_improvement', 0):.4f} vs CIBIL")
    with col2:
        st.metric("Ensemble AUC", f"{metrics.get('stacked_ensemble_auc', 0):.4f}")
    with col3:
        st.metric("Training Samples", f"{metrics.get('train_size', 0):,}")
    with col4:
        st.metric("Feature Set", f"v{metrics.get('n_features_v4', 13)}")
else:
    st.warning("Model metrics not found. Ensure training pipeline has run.")

st.markdown("---")

# ── Links to Monitoring ─────────────────────────────────────
st.markdown("### 📊 System Monitoring & Observability")
st.markdown(
    "Monitor live model performance, drift, and fairness metrics:  \n"
    "- **Grafana Dashboard:** [http://localhost:3000](http://localhost:3000) *(User: admin, Pass: edupredict)*  \n"
    "- **Prometheus Metrics:** [http://localhost:9090](http://localhost:9090)  \n"
    "- **FastAPI Backend (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)"
)
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
    
    st.markdown("**Field & Placement Context**")
    # API expects snake_case for field_of_study matching the model categories
    FIELD_MAP = {
        "Computer Science / IT": "computer_science",
        "Data Science / AI": "data_science",
        "MBA / Finance": "mba_finance",
        "Mechanical Engineering": "mechanical_engineering",
        "Electrical Engineering": "electrical_engineering",
        "Civil Engineering": "civil_engineering",
        "Biotechnology / Life Sciences": "biotechnology"
    }
    field_display = st.selectbox("Degree Field", options=list(FIELD_MAP.keys()))
    field_slug = FIELD_MAP[field_display]
    
    college_placement_rate = st.slider("College Placement Rate (%)", 20, 100, 75)
    
    st.markdown("**Financial Context**")
    loan_amount = st.number_input("Loan Amount (INR)", 
                                min_value=50000, max_value=5000000, 
                                value=800000, step=50000,
                                format="%d")
    family_income = st.number_input("Annual Family Income (INR)",
                                   min_value=0, max_value=10000000,
                                   value=500000, step=50000,
                                   format="%d")

with right:
    st.subheader("🔍 Risk Assessment (Live API Inference)")
    
    if st.button("Assess Loan Risk", type="primary", use_container_width=True):
        # Prepare payload for API
        payload = {
            "cgpa": float(cgpa),
            "internships_count": int(internships),
            "backlogs": int(backlogs),
            "field_of_study": field_slug,
            "college_placement_rate": float(college_placement_rate),
            "loan_amount_inr": float(loan_amount),
            "annual_family_income_inr": float(family_income)
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": API_KEY
        }
        
        try:
            with st.spinner("Calling EduPredict API..."):
                response = requests.post(f"{API_URL}/v1/assess", json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                
            prob = data.get("repayment_probability", 0.0)
            risk_tier = data.get("risk_tier", "UNKNOWN")
            recommendation = data.get("recommendation", "")
            potential_score = data.get("potential_score", 0.0)
            shap_vals = data.get("shap_contributions", {})
            
            # Display result
            st.metric("Repayment Probability", f"{prob:.1%}")
            st.metric("Potential Score", f"{potential_score:.2f} / 1.00")
            
            if risk_tier == "GREEN":
                st.success(f"**Risk Tier:** 🟢 GREEN — Low Risk")
                st.success(f"**Recommendation:** {recommendation}")
            elif risk_tier == "AMBER":
                st.warning(f"**Risk Tier:** 🟡 AMBER — Moderate Risk")
                st.warning(f"**Recommendation:** {recommendation}")
            else:
                st.error(f"**Risk Tier:** 🔴 RED — High Risk")
                st.error(f"**Recommendation:** {recommendation}")
            
            st.progress(float(prob))
            st.caption(f"Assessment ID: `{data.get('assessment_id')}` | Model: `{data.get('model_version')}`")
            
            # SHAP waterfall from API
            if shap_vals:
                st.markdown("**Why this score? (API SHAP Explainability)**")
                fig, ax = plt.subplots(figsize=(8, 4))
                
                # Sort features by absolute contribution
                sorted_imp = sorted(shap_vals.items(), key=lambda x: abs(x[1]), reverse=True)
                # Keep top 10 for readability
                sorted_imp = sorted_imp[:10]
                
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
                
        except requests.exceptions.RequestException as e:
            st.error(f"API Error: Failed to reach backend at {API_URL}/v1/assess")
            st.code(str(e))

# ── Bottom: SHAP global summary ──────────────────────────────
st.markdown("---")
st.subheader("📊 Global Feature Importance")
if os.path.exists("model/artifacts/shap_summary.png"):
    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.image("model/artifacts/shap_summary.png", 
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
    st.info("Global SHAP summary not available.")
