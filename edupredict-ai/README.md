# EduPredict AI — Student Loan Risk Scoring System

EduPredict AI is a next-generation credit underwriting engine designed for student loans. It replaces traditional credit-history-based models with an AI-driven approach that predicts future earning potential based on academic performance, field of study demand, and internship experience.

## Prerequisites
- Python 3.9+
- Kaggle API token configured at `~/.kaggle/kaggle.json`. (Get it from [Kaggle Settings](https://www.kaggle.com/settings) -> API -> Create New Token)

## Installation
1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r edupredict-ai/requirements.txt
   ```

## Data Download
The project uses five Kaggle datasets:
```bash
kaggle datasets download -d muhamedumarjamil/student-placement-data-with-cgpa-and-salary -p data/raw --unzip
kaggle datasets download -d ruchikakumbhar/placement-prediction-dataset -p data/raw --unzip
kaggle datasets download -d architsharma01/loan-approval-prediction-dataset -p data/raw --unzip
kaggle datasets download -d adarshsng/lending-club-loan-data-csv -p data/raw --unzip
kaggle datasets download -d kaggle/college-scorecard -p data/raw --unzip
```

## How to Run
1. **Feature Engineering**: `python edupredict-ai/model/feature_engineering.py`
2. **Train Model**: `python edupredict-ai/model/train.py`
3. **Launch Dashboard**: `streamlit run edupredict-ai/app/streamlit_app.py`

## Model Performance
- **Test AUC**: 0.8219
- **CV AUC (5-fold)**: 0.8034 ± 0.0338
- **Baseline (CIBIL-only)**: 0.6200

## Feature List
- `cgpa_normalized`: Student's CGPA scaled to 0-1.
- `internships_count`: Total number of internships completed.
- `backlogs`: Number of active academic backlogs.
- `median_salary_normalized`: Benchmarked median salary for the field of study.
- `potential_score`: Derived metric representing future earning trajectory.
- `demand_proxy`: Job market demand for the student's field.
- `placement_rate_for_field`: Historical placement success rate for the specific degree field.

## License
MIT
