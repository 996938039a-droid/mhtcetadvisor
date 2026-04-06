"""
MHT-CET Probability Engine

This module calculates admission probabilities based on:
1. Historical cutoff comparisons
2. Year-over-year trend analysis
3. Round-specific factors
4. Seat availability considerations
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class AdmissionChance(Enum):
    """Classification of admission chances"""
    DREAM = "Dream"      # < 30% probability
    TARGET = "Target"    # 30-70% probability  
    SAFE = "Safe"        # > 70% probability
    REACH = "Reach"      # < 10% probability (very unlikely)
    ASSURED = "Assured"  # > 90% probability


@dataclass
class ProbabilityResult:
    """Result of probability calculation for a single option"""
    college_code: str
    college_name: str
    branch_code: str
    branch_name: str
    category_code: str
    probability: float  # 0.0 to 1.0
    chance_category: AdmissionChance
    historical_cutoffs: Dict[int, float]  # year -> percentile
    trend: str  # "rising", "falling", "stable"
    trend_slope: float  # percentile change per year
    confidence: float  # How confident we are in the prediction
    round_predictions: Dict[int, float]  # round -> probability
    notes: List[str]


class ProbabilityEngine:
    """
    Calculates admission probabilities based on historical data
    """
    
    # Round-specific adjustment factors
    # Later rounds typically have lower cutoffs
    ROUND_FACTORS = {
        1: 0.0,    # No adjustment for Round 1
        2: -1.5,   # Cutoffs typically drop ~1.5 percentile
        3: -3.0,   # Further drop
        4: -5.0,   # Significant drop in final round
    }
    
    # Confidence weights by recency
    YEAR_WEIGHTS = {
        0: 0.40,  # Most recent year
        1: 0.30,  # 1 year ago
        2: 0.20,  # 2 years ago
        3: 0.10,  # 3 years ago
    }
    
    def __init__(self, cutoff_data: pd.DataFrame):
        """
        Initialize with historical cutoff data
        
        Args:
            cutoff_data: DataFrame with columns:
                - year, round, college_code, branch_code, category_code
                - closing_percentile, quota, etc.
        """
        self.cutoff_data = cutoff_data
        self.current_year = cutoff_data['year'].max() if len(cutoff_data) > 0 else 2024
    
    def calculate_probability(
        self,
        student_percentile: float,
        college_code: str,
        branch_code: str,
        category_code: str,
        quota: str = "MH",
        target_round: int = 1,
        cutoff_adjustment: float = 0.0
    ) -> ProbabilityResult:
        """
        Calculate admission probability for a specific college-branch combination
        
        Args:
            student_percentile: Student's MHT-CET percentile
            college_code: Target college code
            branch_code: Target branch code
            category_code: Student's applicable category
            quota: MH or AI
            target_round: Which CAP round (1, 2, 3, or 4)
            cutoff_adjustment: Global adjustment factor (positive = stricter cutoffs)
        
        Returns:
            ProbabilityResult with calculated probability and metadata
        """
        # Get historical cutoffs for this combination
        mask = (
            (self.cutoff_data['college_code'] == college_code) &
            (self.cutoff_data['branch_code'] == branch_code) &
            (self.cutoff_data['category_code'] == category_code) &
            (self.cutoff_data['quota'] == quota) &
            (self.cutoff_data['round'] == target_round)
        )
        
        historical = self.cutoff_data[mask].sort_values('year')
        
        if len(historical) == 0:
            # No historical data - return uncertain result
            return self._create_uncertain_result(
                college_code, branch_code, category_code
            )
        
        # Extract historical cutoffs
        historical_cutoffs = dict(zip(
            historical['year'].tolist(),
            historical['closing_percentile'].tolist()
        ))
        
        # Calculate trend
        trend, trend_slope = self._calculate_trend(historical_cutoffs)
        
        # Predict cutoff for current/next year
        predicted_cutoff = self._predict_cutoff(
            historical_cutoffs, 
            trend_slope,
            cutoff_adjustment
        )
        
        # Adjust for round
        round_adjusted_cutoff = predicted_cutoff + self.ROUND_FACTORS.get(target_round, 0)
        
        # Calculate probability using sigmoid function
        probability = self._calculate_probability_score(
            student_percentile, 
            round_adjusted_cutoff,
            historical_cutoffs
        )
        
        # Classify chance
        chance_category = self._classify_chance(probability)
        
        # Calculate round-wise predictions
        round_predictions = {}
        for r in [1, 2, 3, 4]:
            r_cutoff = predicted_cutoff + self.ROUND_FACTORS.get(r, 0)
            round_predictions[r] = self._calculate_probability_score(
                student_percentile, r_cutoff, historical_cutoffs
            )
        
        # Calculate confidence based on data availability
        confidence = self._calculate_confidence(historical_cutoffs)
        
        # Generate notes
        notes = self._generate_notes(
            student_percentile, 
            predicted_cutoff, 
            trend,
            probability
        )
        
        # Get college and branch names
        college_name = historical['college_name'].iloc[0] if 'college_name' in historical.columns else college_code
        branch_name = historical['branch_name'].iloc[0] if 'branch_name' in historical.columns else branch_code
        
        return ProbabilityResult(
            college_code=college_code,
            college_name=college_name,
            branch_code=branch_code,
            branch_name=branch_name,
            category_code=category_code,
            probability=probability,
            chance_category=chance_category,
            historical_cutoffs=historical_cutoffs,
            trend=trend,
            trend_slope=trend_slope,
            confidence=confidence,
            round_predictions=round_predictions,
            notes=notes
        )
    
    def _calculate_trend(self, historical_cutoffs: Dict[int, float]) -> Tuple[str, float]:
        """
        Calculate trend from historical cutoffs
        
        Returns:
            Tuple of (trend_description, slope)
        """
        if len(historical_cutoffs) < 2:
            return "insufficient_data", 0.0
        
        years = sorted(historical_cutoffs.keys())
        percentiles = [historical_cutoffs[y] for y in years]
        
        # Simple linear regression
        n = len(years)
        x_mean = sum(years) / n
        y_mean = sum(percentiles) / n
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(years, percentiles))
        denominator = sum((x - x_mean) ** 2 for x in years)
        
        slope = numerator / denominator if denominator != 0 else 0
        
        # Classify trend
        if abs(slope) < 0.5:
            trend = "stable"
        elif slope > 0:
            trend = "rising"  # Cutoffs increasing (harder to get in)
        else:
            trend = "falling"  # Cutoffs decreasing (easier to get in)
        
        return trend, round(slope, 3)
    
    def _predict_cutoff(
        self, 
        historical_cutoffs: Dict[int, float],
        trend_slope: float,
        adjustment: float
    ) -> float:
        """
        Predict cutoff for upcoming admission cycle
        Uses weighted average with trend projection
        """
        if len(historical_cutoffs) == 0:
            return 50.0  # Default middle value
        
        years = sorted(historical_cutoffs.keys(), reverse=True)
        
        # Weighted average of recent years
        weighted_sum = 0.0
        weight_sum = 0.0
        
        for i, year in enumerate(years[:4]):  # Last 4 years max
            weight = self.YEAR_WEIGHTS.get(i, 0.05)
            weighted_sum += historical_cutoffs[year] * weight
            weight_sum += weight
        
        base_prediction = weighted_sum / weight_sum if weight_sum > 0 else 50.0
        
        # Add trend projection (half weight to avoid over-extrapolation)
        trend_adjustment = trend_slope * 0.5
        
        # Apply user's global adjustment
        final_prediction = base_prediction + trend_adjustment + adjustment
        
        # Clamp to valid range
        return max(0.0, min(100.0, final_prediction))
    
    def _calculate_probability_score(
        self,
        student_percentile: float,
        predicted_cutoff: float,
        historical_cutoffs: Dict[int, float]
    ) -> float:
        """
        Calculate probability using a sigmoid function
        
        The probability transitions smoothly around the predicted cutoff
        """
        # Calculate standard deviation from historical data
        if len(historical_cutoffs) >= 2:
            std_dev = np.std(list(historical_cutoffs.values()))
            std_dev = max(std_dev, 1.0)  # Minimum 1 percentile variation
        else:
            std_dev = 2.0  # Default assumption
        
        # Difference from predicted cutoff
        diff = student_percentile - predicted_cutoff
        
        # Sigmoid transformation
        # k controls steepness (higher = steeper transition)
        k = 1.5 / std_dev
        probability = 1 / (1 + np.exp(-k * diff))
        
        return round(probability, 3)
    
    def _classify_chance(self, probability: float) -> AdmissionChance:
        """Classify probability into admission chance category"""
        if probability >= 0.90:
            return AdmissionChance.ASSURED
        elif probability >= 0.70:
            return AdmissionChance.SAFE
        elif probability >= 0.30:
            return AdmissionChance.TARGET
        elif probability >= 0.10:
            return AdmissionChance.DREAM
        else:
            return AdmissionChance.REACH
    
    def _calculate_confidence(self, historical_cutoffs: Dict[int, float]) -> float:
        """
        Calculate confidence in prediction based on data availability
        
        More years of data = higher confidence
        Recent data = higher confidence
        Consistent data = higher confidence
        """
        if len(historical_cutoffs) == 0:
            return 0.1
        
        # Factor 1: Number of years
        years_factor = min(len(historical_cutoffs) / 4, 1.0)  # Max at 4 years
        
        # Factor 2: Recency
        most_recent = max(historical_cutoffs.keys())
        recency_factor = 1.0 if most_recent >= self.current_year - 1 else 0.7
        
        # Factor 3: Consistency (low std dev = high consistency)
        if len(historical_cutoffs) >= 2:
            std_dev = np.std(list(historical_cutoffs.values()))
            consistency_factor = 1.0 / (1.0 + std_dev / 5.0)
        else:
            consistency_factor = 0.5
        
        confidence = (years_factor * 0.4 + recency_factor * 0.3 + consistency_factor * 0.3)
        return round(confidence, 2)
    
    def _generate_notes(
        self,
        student_percentile: float,
        predicted_cutoff: float,
        trend: str,
        probability: float
    ) -> List[str]:
        """Generate helpful notes about the prediction"""
        notes = []
        
        diff = student_percentile - predicted_cutoff
        
        if diff > 5:
            notes.append("Your percentile is comfortably above historical cutoffs")
        elif diff > 2:
            notes.append("Good chances - you're above the typical cutoff")
        elif diff > 0:
            notes.append("Borderline - your percentile is close to cutoff")
        elif diff > -2:
            notes.append("Slightly below cutoff - consider this a reach option")
        else:
            notes.append("Significantly below historical cutoffs")
        
        if trend == "rising":
            notes.append("⚠️ Cutoffs have been increasing year over year")
        elif trend == "falling":
            notes.append("✅ Cutoffs have been decreasing - favorable trend")
        
        if probability < 0.3:
            notes.append("💡 Consider this as a Dream option - place early in your list")
        elif probability > 0.7:
            notes.append("✅ Safe option - good for backup")
        
        return notes
    
    def _create_uncertain_result(
        self,
        college_code: str,
        branch_code: str,
        category_code: str
    ) -> ProbabilityResult:
        """Create result when no historical data is available"""
        return ProbabilityResult(
            college_code=college_code,
            college_name=college_code,
            branch_code=branch_code,
            branch_name=branch_code,
            category_code=category_code,
            probability=0.5,
            chance_category=AdmissionChance.TARGET,
            historical_cutoffs={},
            trend="unknown",
            trend_slope=0.0,
            confidence=0.1,
            round_predictions={1: 0.5, 2: 0.55, 3: 0.6, 4: 0.65},
            notes=["⚠️ No historical data available for this combination"]
        )
    
    def get_all_options_for_student(
        self,
        student_percentile: float,
        category_code: str,
        quota: str = "MH",
        target_round: int = 1,
        cutoff_adjustment: float = 0.0,
        min_probability: float = 0.05,
        branch_filter: Optional[List[str]] = None,
        college_type_filter: Optional[List[str]] = None
    ) -> List[ProbabilityResult]:
        """
        Get all possible options for a student with probabilities
        
        Args:
            student_percentile: Student's percentile
            category_code: Student's category
            quota: MH or AI
            target_round: Target CAP round
            cutoff_adjustment: Global adjustment percentage
            min_probability: Minimum probability to include
            branch_filter: List of branch codes to filter (None = all)
            college_type_filter: List of college types to filter (None = all)
        
        Returns:
            List of ProbabilityResult sorted by probability (descending)
        """
        results = []
        
        # Get unique college-branch combinations
        relevant_data = self.cutoff_data[
            (self.cutoff_data['category_code'] == category_code) &
            (self.cutoff_data['quota'] == quota) &
            (self.cutoff_data['round'] == target_round)
        ]
        
        # Apply filters
        if branch_filter:
            relevant_data = relevant_data[
                relevant_data['branch_code'].isin(branch_filter)
            ]
        if college_type_filter:
            relevant_data = relevant_data[
                relevant_data['college_type'].isin(college_type_filter)
            ]
        
        # Get unique combinations
        combinations = relevant_data.groupby(
            ['college_code', 'branch_code']
        ).size().reset_index()[['college_code', 'branch_code']]
        
        for _, row in combinations.iterrows():
            result = self.calculate_probability(
                student_percentile=student_percentile,
                college_code=row['college_code'],
                branch_code=row['branch_code'],
                category_code=category_code,
                quota=quota,
                target_round=target_round,
                cutoff_adjustment=cutoff_adjustment
            )
            
            if result.probability >= min_probability:
                results.append(result)
        
        # Sort by probability (highest first)
        results.sort(key=lambda x: x.probability, reverse=True)
        
        return results
    
    def classify_options(
        self,
        results: List[ProbabilityResult]
    ) -> Dict[str, List[ProbabilityResult]]:
        """
        Classify options into Dream/Target/Safe categories
        
        Returns:
            Dictionary with keys 'dream', 'target', 'safe'
        """
        classified = {
            'reach': [],
            'dream': [],
            'target': [],
            'safe': [],
            'assured': []
        }
        
        for result in results:
            if result.chance_category == AdmissionChance.REACH:
                classified['reach'].append(result)
            elif result.chance_category == AdmissionChance.DREAM:
                classified['dream'].append(result)
            elif result.chance_category == AdmissionChance.TARGET:
                classified['target'].append(result)
            elif result.chance_category == AdmissionChance.SAFE:
                classified['safe'].append(result)
            else:
                classified['assured'].append(result)
        
        return classified


class RoundSimulator:
    """
    Simulates multi-round CAP admission outcomes
    """
    
    def __init__(self, probability_engine: ProbabilityEngine):
        self.engine = probability_engine
    
    def simulate_rounds(
        self,
        student_percentile: float,
        preference_list: List[Tuple[str, str, str]],  # (college, branch, category)
        quota: str = "MH",
        cutoff_adjustment: float = 0.0
    ) -> Dict[int, Dict]:
        """
        Simulate admission outcomes across all CAP rounds
        
        Args:
            student_percentile: Student's percentile
            preference_list: Ordered list of (college_code, branch_code, category_code)
            quota: MH or AI
            cutoff_adjustment: Global adjustment
        
        Returns:
            Dictionary of round -> {
                'likely_allotment': (college, branch) or None,
                'probability': float,
                'all_options': List of remaining options
            }
        """
        results = {}
        
        for round_num in [1, 2, 3, 4]:
            # Calculate probabilities for this round
            round_results = []
            for college_code, branch_code, category_code in preference_list:
                prob_result = self.engine.calculate_probability(
                    student_percentile=student_percentile,
                    college_code=college_code,
                    branch_code=branch_code,
                    category_code=category_code,
                    quota=quota,
                    target_round=round_num,
                    cutoff_adjustment=cutoff_adjustment
                )
                round_results.append(prob_result)
            
            # Find most likely allotment (first option with high probability)
            likely_allotment = None
            allotment_prob = 0.0
            
            for result in round_results:
                if result.probability > 0.5:  # More likely than not
                    likely_allotment = (result.college_code, result.branch_code)
                    allotment_prob = result.probability
                    break
            
            results[round_num] = {
                'likely_allotment': likely_allotment,
                'probability': allotment_prob,
                'all_options': round_results
            }
        
        return results
    
    def recommend_action(
        self,
        current_allotment: Tuple[str, str],
        preference_list: List[Tuple[str, str, str]],
        current_round: int,
        student_percentile: float,
        quota: str = "MH"
    ) -> Dict[str, any]:
        """
        Recommend Float/Freeze/Slide action
        
        Returns:
            Dictionary with recommendation and reasoning
        """
        # Find position of current allotment in preference list
        current_pos = None
        for i, (college, branch, _) in enumerate(preference_list):
            if college == current_allotment[0] and branch == current_allotment[1]:
                current_pos = i
                break
        
        if current_pos is None:
            return {
                'action': 'FREEZE',
                'reason': 'Current allotment not in preference list - accept and exit'
            }
        
        if current_pos == 0:
            return {
                'action': 'FREEZE',
                'reason': 'You got your top choice! Accept and exit.'
            }
        
        # Check probability of getting better options
        better_options = preference_list[:current_pos]
        can_improve = False
        
        for college, branch, category in better_options:
            # Simulate next round
            next_round = min(current_round + 1, 4)
            prob = self.engine.calculate_probability(
                student_percentile=student_percentile,
                college_code=college,
                branch_code=branch,
                category_code=category,
                quota=quota,
                target_round=next_round
            )
            
            if prob.probability > 0.4:  # Reasonable chance
                can_improve = True
                break
        
        if can_improve:
            # Check if slide is possible (better branch in same college)
            same_college_better = [
                (c, b, cat) for c, b, cat in better_options 
                if c == current_allotment[0]
            ]
            
            if same_college_better:
                return {
                    'action': 'SLIDE',
                    'reason': f'You might get a better branch in the same college in Round {current_round + 1}'
                }
            else:
                return {
                    'action': 'FLOAT',
                    'reason': f'Keep this seat but stay in process - you have chances for better colleges'
                }
        else:
            return {
                'action': 'FREEZE',
                'reason': 'Low probability of getting better options - accept current seat'
            }


if __name__ == "__main__":
    # Test with sample data
    from data_loader import create_sample_data
    
    sample_df = create_sample_data()
    engine = ProbabilityEngine(sample_df)
    
    # Test probability calculation
    result = engine.calculate_probability(
        student_percentile=96.5,
        college_code='01002',
        branch_code='0100224210',
        category_code='GOPENS',
        quota='MH',
        target_round=1
    )
    
    print("Probability Result:")
    print(f"  College: {result.college_name}")
    print(f"  Branch: {result.branch_name}")
    print(f"  Probability: {result.probability:.1%}")
    print(f"  Category: {result.chance_category.value}")
    print(f"  Trend: {result.trend} ({result.trend_slope:+.2f} per year)")
    print(f"  Confidence: {result.confidence:.0%}")
    print(f"  Notes: {result.notes}")
