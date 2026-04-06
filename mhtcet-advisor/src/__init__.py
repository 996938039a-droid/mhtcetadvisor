"""
MHT-CET College Preference Advisor - Source Package

This package contains the core modules for the MHT-CET advisor system.
"""

from .data_loader import (
    CutoffDataLoader,
    CutoffEntry,
    CollegeInfo,
    SeatMatrixLoader,
    create_sample_data
)

from .probability_engine import (
    ProbabilityEngine,
    ProbabilityResult,
    AdmissionChance,
    RoundSimulator
)

from .recommendation_engine import (
    RecommendationEngine,
    StudentProfile,
    PreferenceListItem,
    RecommendationResult,
    PriorityType
)

__version__ = "1.0.0"
__author__ = "MHT-CET Advisor Team"

__all__ = [
    # Data Loader
    "CutoffDataLoader",
    "CutoffEntry",
    "CollegeInfo",
    "SeatMatrixLoader",
    "create_sample_data",
    
    # Probability Engine
    "ProbabilityEngine",
    "ProbabilityResult",
    "AdmissionChance",
    "RoundSimulator",
    
    # Recommendation Engine
    "RecommendationEngine",
    "StudentProfile",
    "PreferenceListItem",
    "RecommendationResult",
    "PriorityType",
]
