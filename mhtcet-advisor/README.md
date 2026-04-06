# MHT-CET College Preference Advisor

## 🎯 Overview

An intelligent decision-support system for Maharashtra engineering admissions that helps students optimize their CAP (Centralized Admission Process) preference list using historical cutoff data, probability modeling, and multi-round simulation.

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        MHT-CET ADVISOR SYSTEM                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   DATA       │    │   ANALYSIS   │    │   RECOMMENDATION     │  │
│  │   LAYER      │───▶│   ENGINE     │───▶│   ENGINE             │  │
│  └──────────────┘    └──────────────┘    └──────────────────────┘  │
│         │                   │                      │                │
│         ▼                   ▼                      ▼                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │ PDF Parser   │    │ Probability  │    │ Preference List      │  │
│  │ Data Store   │    │ Calculator   │    │ Generator            │  │
│  │ Seat Matrix  │    │ Trend Analyzer│   │ What-If Simulator    │  │
│  │ College Meta │    │ Round Sim    │    │ Float/Freeze Advisor │  │
│  └──────────────┘    └──────────────┘    └──────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                     STREAMLIT WEB APP                         │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │   │
│  │  │ Profile │ │ Browse  │ │Recommend│ │What-If  │ │ Export  │ │   │
│  │  │ Input   │ │ Colleges│ │ ations  │ │Simulator│ │ Results │ │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## 📊 Data Sources

### Primary Data (from fe2025.mahacet.org)

| Year | Seat Matrix | CAP Round I | CAP Round II | CAP Round III | CAP Round IV |
|------|-------------|-------------|--------------|---------------|--------------|
| 2022-23 | ✅ | MH + AI | MH + AI | MH + AI + Diploma | - |
| 2023-24 | ✅ | MH + AI | MH + AI | MH + AI + Diploma | - |
| 2024-25 | ✅ | MH + AI | MH + AI | MH + AI + Diploma | - |
| 2025-26 | ✅ | MH + AI | MH + AI | MH + AI + Diploma | MH + AI |

### Data Schema

```
cutoff_data/
├── raw/                    # Original PDFs
│   ├── 2022/
│   ├── 2023/
│   ├── 2024/
│   └── 2025/
├── parsed/                 # Extracted JSON/CSV
│   ├── cutoffs.parquet     # Main cutoff database
│   ├── seat_matrix.parquet # Seat availability
│   └── colleges.json       # College metadata
└── processed/              # Analysis-ready data
    ├── trends.parquet      # Year-over-year trends
    └── probabilities.parquet
```

## 🔧 Features

### 1. Student Profile Input
- **Percentile Entry**: Exact value, range, or rank with auto-conversion
- **Category Selection**: GEN, OBC, SC, ST, VJ, NT1, NT2, NT3, EWS
- **Special Quotas**: TFWS, PWD, Defence, Orphan, Minority
- **Gender**: For Ladies quota eligibility
- **Home University**: Mumbai, Pune, Nagpur, Aurangabad, etc.
- **Quota Type**: Maharashtra State (MH) or All India (AI)

### 2. Preference Recommendations
- **Dream Colleges** (< 30% probability): Aspirational choices
- **Target Colleges** (30-70% probability): Realistic targets
- **Safe Colleges** (> 70% probability): Backup options
- **Probability Scores**: Based on 4-year historical analysis

### 3. Multi-Round Simulation
- Simulates CAP Round I, II, III, IV outcomes
- Predicts likely allotment per round
- Shows cutoff movement patterns

### 4. Float/Freeze/Slide Advisor
- **Freeze**: Accept current seat, exit process
- **Float**: Accept seat but continue for better options
- **Slide**: Accept seat, try for better branch in same college
- AI-powered recommendation based on your preferences

### 5. What-If Simulator
- Drag-and-drop preference reordering
- Real-time impact analysis
- "Missed opportunity" detection

### 6. Cutoff Adjustment
- Global slider: Predict stricter/lenient cutoffs
- Range: -15% to +15% adjustment
- Affects all probability calculations

### 7. Filters
- Location/City preference
- Gender-specific quotas
- Fee budget constraints
- College type (Govt/Private/Autonomous)

### 8. Export
- Excel: Detailed preference list with all metadata
- PDF: Print-ready report for counseling sessions

### 9. ACAP Guidance
- Institute-level round information
- Leftover seat availability patterns
- Alternative admission routes

## 🚀 Installation

```bash
# Clone repository
git clone https://github.com/your-repo/mhtcet-advisor.git
cd mhtcet-advisor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

## 📁 Project Structure

```
mhtcet-advisor/
├── app.py                      # Main Streamlit application
├── requirements.txt            # Python dependencies
├── README.md                   # This file
│
├── src/
│   ├── __init__.py
│   ├── data_loader.py          # PDF parsing and data loading
│   ├── probability_engine.py   # Probability calculations
│   ├── recommendation_engine.py # Preference list generation
│   ├── round_simulator.py      # Multi-round CAP simulation
│   ├── what_if_analyzer.py     # What-if scenario analysis
│   └── export_utils.py         # Excel/PDF export functions
│
├── data/
│   ├── raw/                    # Original PDF files
│   ├── parsed/                 # Extracted structured data
│   └── processed/              # Analysis-ready datasets
│
├── config/
│   ├── categories.yaml         # Category codes and mappings
│   ├── colleges.yaml           # College metadata
│   └── home_universities.yaml  # Home university mappings
│
├── tests/
│   ├── test_data_loader.py
│   ├── test_probability.py
│   └── test_recommendations.py
│
└── notebooks/
    ├── data_exploration.ipynb
    └── model_validation.ipynb
```

## 📈 Algorithm Details

### Probability Calculation

```
P(admission) = weighted_average(
    historical_cutoff_comparison,
    trend_adjustment,
    round_specific_factor,
    seat_availability_factor
)

Where:
- historical_cutoff_comparison: Student percentile vs past cutoffs
- trend_adjustment: Year-over-year cutoff movement
- round_specific_factor: Cutoffs typically drop in later rounds
- seat_availability_factor: Based on seat matrix
```

### Dream/Target/Safe Classification

| Category | Probability Range | Description |
|----------|-------------------|-------------|
| Dream | 0% - 30% | Reach schools, worth trying |
| Target | 30% - 70% | Realistic chances |
| Safe | 70% - 100% | High confidence backup |

### Preference Ordering Strategy

1. **Top 20%**: Dream colleges (sorted by desirability)
2. **Middle 50%**: Target colleges (sorted by probability × desirability)
3. **Bottom 30%**: Safe colleges (ensure at least one admission)

## 🔒 Data Privacy

- No personal data is stored on servers
- All processing happens in-browser session
- Exported files are generated client-side

## 📝 License

MIT License - See LICENSE file for details

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Support

For issues and feature requests, please open a GitHub issue.

---

**Disclaimer**: This tool provides recommendations based on historical data. Actual admission outcomes depend on various factors and official CET Cell processes. Always verify with official sources.
