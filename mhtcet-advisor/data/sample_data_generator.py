"""
Sample Data Generator for MHT-CET Advisor

Generates realistic sample cutoff data based on actual MHT-CET patterns
for testing and demonstration purposes.
"""

import pandas as pd
import numpy as np
from typing import List, Dict
import random


# Top colleges with approximate cutoff ranges (based on real patterns)
COLLEGES = [
    # Government Autonomous (Top Tier)
    {"code": "01001", "name": "College of Engineering, Pune (COEP)", "type": "Government Autonomous", "city": "Pune", "base_cutoff": 98.5},
    {"code": "01002", "name": "Veermata Jijabai Technological Institute (VJTI)", "type": "Government Autonomous", "city": "Mumbai", "base_cutoff": 98.0},
    {"code": "01003", "name": "Government College of Engineering, Amravati", "type": "Government Autonomous", "city": "Amravati", "base_cutoff": 96.5},
    {"code": "01004", "name": "Government College of Engineering, Aurangabad", "type": "Government Autonomous", "city": "Aurangabad", "base_cutoff": 95.0},
    {"code": "01005", "name": "Government College of Engineering, Karad", "type": "Government Autonomous", "city": "Karad", "base_cutoff": 94.0},
    
    # Government (Second Tier)
    {"code": "02001", "name": "Government Engineering College, Chandrapur", "type": "Government", "city": "Chandrapur", "base_cutoff": 88.0},
    {"code": "02002", "name": "Government Engineering College, Yavatmal", "type": "Government", "city": "Yavatmal", "base_cutoff": 85.0},
    {"code": "02003", "name": "Government Engineering College, Jalgaon", "type": "Government", "city": "Jalgaon", "base_cutoff": 86.0},
    
    # Private Autonomous (Good)
    {"code": "03001", "name": "Vishwakarma Institute of Technology", "type": "Un-Aided Autonomous", "city": "Pune", "base_cutoff": 93.0},
    {"code": "03002", "name": "Pune Institute of Computer Technology", "type": "Un-Aided Autonomous", "city": "Pune", "base_cutoff": 94.0},
    {"code": "03003", "name": "K J Somaiya College of Engineering", "type": "Un-Aided Autonomous", "city": "Mumbai", "base_cutoff": 92.0},
    {"code": "03004", "name": "DJ Sanghvi College of Engineering", "type": "Un-Aided Autonomous", "city": "Mumbai", "base_cutoff": 91.0},
    {"code": "03005", "name": "Sardar Patel Institute of Technology", "type": "Un-Aided", "city": "Mumbai", "base_cutoff": 90.0},
    
    # Private (Medium Tier)
    {"code": "04001", "name": "Sinhgad College of Engineering", "type": "Un-Aided", "city": "Pune", "base_cutoff": 80.0},
    {"code": "04002", "name": "AISSMS College of Engineering", "type": "Un-Aided", "city": "Pune", "base_cutoff": 82.0},
    {"code": "04003", "name": "Pillai College of Engineering", "type": "Un-Aided", "city": "Navi Mumbai", "base_cutoff": 78.0},
    {"code": "04004", "name": "BVDU College of Engineering", "type": "Un-Aided", "city": "Pune", "base_cutoff": 75.0},
    
    # Lower Tier
    {"code": "05001", "name": "XYZ Institute of Technology", "type": "Un-Aided", "city": "Nashik", "base_cutoff": 60.0},
    {"code": "05002", "name": "ABC Engineering College", "type": "Un-Aided", "city": "Nagpur", "base_cutoff": 55.0},
    {"code": "05003", "name": "Regional Engineering Institute", "type": "Un-Aided", "city": "Solapur", "base_cutoff": 50.0},
]

# Branches with relative demand factor
BRANCHES = [
    {"code": "24210", "name": "Computer Science and Engineering", "demand_factor": 1.0},
    {"code": "24211", "name": "Computer Engineering", "demand_factor": 0.98},
    {"code": "24212", "name": "Information Technology", "demand_factor": 0.95},
    {"code": "24213", "name": "Computer Science and Engineering (AI/ML)", "demand_factor": 1.02},
    {"code": "24214", "name": "Artificial Intelligence and Data Science", "demand_factor": 1.01},
    {"code": "24220", "name": "Electronics and Telecommunication Engineering", "demand_factor": 0.85},
    {"code": "24221", "name": "Electronics Engineering", "demand_factor": 0.80},
    {"code": "24230", "name": "Electrical Engineering", "demand_factor": 0.70},
    {"code": "24240", "name": "Mechanical Engineering", "demand_factor": 0.65},
    {"code": "24250", "name": "Civil Engineering", "demand_factor": 0.55},
    {"code": "24260", "name": "Chemical Engineering", "demand_factor": 0.50},
]

# Categories with relative cutoff offsets
CATEGORIES = [
    {"code": "GOPENS", "name": "General Open - State", "offset": 0},
    {"code": "GOBCS", "name": "General OBC - State", "offset": -1.5},
    {"code": "GSCS", "name": "General SC - State", "offset": -8},
    {"code": "GSTS", "name": "General ST - State", "offset": -12},
    {"code": "GVJS", "name": "General VJ - State", "offset": -6},
    {"code": "GNT1S", "name": "General NT1 - State", "offset": -5},
    {"code": "GNT2S", "name": "General NT2 - State", "offset": -4},
    {"code": "GNT3S", "name": "General NT3 - State", "offset": -4},
    {"code": "EWS", "name": "Economically Weaker Section", "offset": -2},
    {"code": "TFWS", "name": "Tuition Fee Waiver", "offset": 2},  # Actually harder to get
    {"code": "LOPENS", "name": "Ladies Open - State", "offset": -1},
    {"code": "LOBCS", "name": "Ladies OBC - State", "offset": -2.5},
]

# Year-over-year trend factors
YEAR_TRENDS = {
    2022: -0.5,   # Slightly lower cutoffs
    2023: 0.0,    # Baseline
    2024: 0.5,    # Slightly higher
    2025: 0.8,    # More competition
}

# Round adjustment factors
ROUND_ADJUSTMENTS = {
    1: 0.0,
    2: -1.5,
    3: -3.0,
    4: -5.0,
}


def generate_sample_cutoff_data() -> pd.DataFrame:
    """
    Generate comprehensive sample cutoff data
    
    Returns:
        DataFrame with realistic cutoff entries
    """
    data = []
    
    for college in COLLEGES:
        for branch in BRANCHES:
            # Calculate base cutoff for this college-branch combo
            base_cutoff = college["base_cutoff"] * branch["demand_factor"]
            
            # Only generate entries for valid combinations
            # (not all colleges have all branches)
            if random.random() > 0.3:  # 70% of combinations exist
                
                for category in CATEGORIES:
                    for year in [2022, 2023, 2024, 2025]:
                        for round_num in [1, 2, 3]:  # Most data is for rounds 1-3
                            
                            # Calculate cutoff with variations
                            cutoff = (
                                base_cutoff 
                                + category["offset"]
                                + YEAR_TRENDS[year]
                                + ROUND_ADJUSTMENTS[round_num]
                                + random.gauss(0, 1)  # Random variation
                            )
                            
                            # Clamp to valid range
                            cutoff = max(1, min(99.99, cutoff))
                            
                            # Calculate rank (approximate inverse)
                            total_candidates = 300000
                            rank = int((100 - cutoff) / 100 * total_candidates)
                            rank = max(1, rank)
                            
                            # Only include if cutoff is reasonable
                            if cutoff > 30:  # Filter very low cutoffs
                                data.append({
                                    "year": year,
                                    "round": round_num,
                                    "college_code": college["code"],
                                    "college_name": college["name"],
                                    "branch_code": college["code"] + branch["code"],
                                    "branch_name": branch["name"],
                                    "category_code": category["code"],
                                    "quota": "MH",
                                    "home_university": "Autonomous Institute",
                                    "seat_type": "S",
                                    "stage": 1,
                                    "closing_rank": rank,
                                    "closing_percentile": round(cutoff, 2),
                                    "college_type": college["type"],
                                    "is_autonomous": "Autonomous" in college["type"]
                                })
    
    return pd.DataFrame(data)


def generate_minimal_sample_data() -> pd.DataFrame:
    """
    Generate minimal sample data for quick testing
    
    Returns:
        DataFrame with a small set of entries
    """
    data = [
        # COEP - CSE (top college, top branch)
        {"year": 2024, "round": 1, "college_code": "01001", "college_name": "College of Engineering, Pune (COEP)",
         "branch_code": "0100124210", "branch_name": "Computer Science and Engineering",
         "category_code": "GOPENS", "quota": "MH", "home_university": "Autonomous Institute",
         "seat_type": "S", "stage": 1, "closing_rank": 450, "closing_percentile": 99.85,
         "college_type": "Government Autonomous", "is_autonomous": True},
        
        {"year": 2023, "round": 1, "college_code": "01001", "college_name": "College of Engineering, Pune (COEP)",
         "branch_code": "0100124210", "branch_name": "Computer Science and Engineering",
         "category_code": "GOPENS", "quota": "MH", "home_university": "Autonomous Institute",
         "seat_type": "S", "stage": 1, "closing_rank": 480, "closing_percentile": 99.84,
         "college_type": "Government Autonomous", "is_autonomous": True},
        
        {"year": 2022, "round": 1, "college_code": "01001", "college_name": "College of Engineering, Pune (COEP)",
         "branch_code": "0100124210", "branch_name": "Computer Science and Engineering",
         "category_code": "GOPENS", "quota": "MH", "home_university": "Autonomous Institute",
         "seat_type": "S", "stage": 1, "closing_rank": 520, "closing_percentile": 99.83,
         "college_type": "Government Autonomous", "is_autonomous": True},
        
        # VJTI - CSE
        {"year": 2024, "round": 1, "college_code": "01002", "college_name": "Veermata Jijabai Technological Institute (VJTI)",
         "branch_code": "0100224210", "branch_name": "Computer Science and Engineering",
         "category_code": "GOPENS", "quota": "MH", "home_university": "Autonomous Institute",
         "seat_type": "S", "stage": 1, "closing_rank": 750, "closing_percentile": 99.75,
         "college_type": "Government Autonomous", "is_autonomous": True},
        
        {"year": 2023, "round": 1, "college_code": "01002", "college_name": "Veermata Jijabai Technological Institute (VJTI)",
         "branch_code": "0100224210", "branch_name": "Computer Science and Engineering",
         "category_code": "GOPENS", "quota": "MH", "home_university": "Autonomous Institute",
         "seat_type": "S", "stage": 1, "closing_rank": 800, "closing_percentile": 99.73,
         "college_type": "Government Autonomous", "is_autonomous": True},
        
        # GEC Amravati - CSE
        {"year": 2024, "round": 1, "college_code": "01003", "college_name": "Government College of Engineering, Amravati",
         "branch_code": "0100324210", "branch_name": "Computer Science and Engineering",
         "category_code": "GOPENS", "quota": "MH", "home_university": "Autonomous Institute",
         "seat_type": "S", "stage": 1, "closing_rank": 7500, "closing_percentile": 97.50,
         "college_type": "Government Autonomous", "is_autonomous": True},
        
        {"year": 2023, "round": 1, "college_code": "01003", "college_name": "Government College of Engineering, Amravati",
         "branch_code": "0100324210", "branch_name": "Computer Science and Engineering",
         "category_code": "GOPENS", "quota": "MH", "home_university": "Autonomous Institute",
         "seat_type": "S", "stage": 1, "closing_rank": 8000, "closing_percentile": 97.33,
         "college_type": "Government Autonomous", "is_autonomous": True},
        
        {"year": 2022, "round": 1, "college_code": "01003", "college_name": "Government College of Engineering, Amravati",
         "branch_code": "0100324210", "branch_name": "Computer Science and Engineering",
         "category_code": "GOPENS", "quota": "MH", "home_university": "Autonomous Institute",
         "seat_type": "S", "stage": 1, "closing_rank": 8500, "closing_percentile": 97.17,
         "college_type": "Government Autonomous", "is_autonomous": True},
        
        # OBC entries
        {"year": 2024, "round": 1, "college_code": "01003", "college_name": "Government College of Engineering, Amravati",
         "branch_code": "0100324210", "branch_name": "Computer Science and Engineering",
         "category_code": "GOBCS", "quota": "MH", "home_university": "Autonomous Institute",
         "seat_type": "S", "stage": 1, "closing_rank": 8500, "closing_percentile": 97.17,
         "college_type": "Government Autonomous", "is_autonomous": True},
        
        # Medium tier colleges
        {"year": 2024, "round": 1, "college_code": "03001", "college_name": "Vishwakarma Institute of Technology",
         "branch_code": "0300124210", "branch_name": "Computer Science and Engineering",
         "category_code": "GOPENS", "quota": "MH", "home_university": "Savitribai Phule Pune University",
         "seat_type": "S", "stage": 1, "closing_rank": 15000, "closing_percentile": 95.00,
         "college_type": "Un-Aided Autonomous", "is_autonomous": True},
        
        {"year": 2024, "round": 1, "college_code": "04001", "college_name": "Sinhgad College of Engineering",
         "branch_code": "0400124210", "branch_name": "Computer Science and Engineering",
         "category_code": "GOPENS", "quota": "MH", "home_university": "Savitribai Phule Pune University",
         "seat_type": "S", "stage": 1, "closing_rank": 45000, "closing_percentile": 85.00,
         "college_type": "Un-Aided", "is_autonomous": False},
        
        # Lower tier (for low percentile students)
        {"year": 2024, "round": 1, "college_code": "05001", "college_name": "XYZ Institute of Technology",
         "branch_code": "0500124210", "branch_name": "Computer Science and Engineering",
         "category_code": "GOPENS", "quota": "MH", "home_university": "North Maharashtra University",
         "seat_type": "S", "stage": 1, "closing_rank": 120000, "closing_percentile": 60.00,
         "college_type": "Un-Aided", "is_autonomous": False},
        
        {"year": 2024, "round": 1, "college_code": "05002", "college_name": "ABC Engineering College",
         "branch_code": "0500224210", "branch_name": "Computer Science and Engineering",
         "category_code": "GOPENS", "quota": "MH", "home_university": "RTMNU",
         "seat_type": "S", "stage": 1, "closing_rank": 150000, "closing_percentile": 50.00,
         "college_type": "Un-Aided", "is_autonomous": False},
    ]
    
    return pd.DataFrame(data)


def save_sample_data(output_dir: str = "data/parsed"):
    """Save sample data to parquet files"""
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate full dataset
    full_df = generate_sample_cutoff_data()
    full_df.to_parquet(f"{output_dir}/cutoffs_combined.parquet", index=False)
    print(f"Generated {len(full_df)} cutoff entries")
    
    # Generate minimal for quick testing
    minimal_df = generate_minimal_sample_data()
    minimal_df.to_parquet(f"{output_dir}/cutoffs_minimal.parquet", index=False)
    print(f"Generated {len(minimal_df)} minimal entries")


if __name__ == "__main__":
    # Generate and save sample data
    save_sample_data()
    
    # Print sample statistics
    df = generate_sample_cutoff_data()
    print("\nSample Data Statistics:")
    print(f"Total entries: {len(df)}")
    print(f"Years: {df['year'].unique()}")
    print(f"Colleges: {df['college_name'].nunique()}")
    print(f"Branches: {df['branch_name'].nunique()}")
    print(f"Categories: {df['category_code'].nunique()}")
