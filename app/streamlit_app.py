import streamlit as st
import json
import os
import requests
import matplotlib.pyplot as plt

# Internal ML Ops tool — not for lender/student use
# Run: streamlit run app/streamlit_app.py
# Access: http://localhost:8501 (internal network only)

st.set_page_config(
    page_title="EduPredict AI — Lender's Command Center",
    page_icon="🎓",
    layout="wide"
)

API_URL = os.environ.get("API_URL", "http://localhost:8000")
API_KEY = os.environ.get("DEMO_API_KEY", "")
if not API_KEY:
    st.error("DEMO_API_KEY environment variable not set. Run: export DEMO_API_KEY=your_key")
    st.stop()

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
