"""
MHT-CET Recommendation Engine

This module generates optimized preference lists based on:
1. Student profile and preferences
2. Probability calculations
3. Strategic ordering (Dream -> Target -> Safe)
4. User-defined priorities
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
from .probability_engine import ProbabilityEngine, ProbabilityResult, AdmissionChance


class PriorityType(Enum):
    """What the student prioritizes"""
    COLLEGE_FIRST = "college"  # Best college regardless of branch
    BRANCH_FIRST = "branch"    # Preferred branch regardless of college
    BALANCED = "balanced"      # Balance between college and branch


@dataclass
class StudentProfile:
    """Complete student profile for recommendations"""
    percentile: float
    category: str  # OPEN, OBC, SC, ST, etc.
    gender: str  # male, female
    quota: str  # MH, AI
    home_university: Optional[str] = None
    
    # Special quotas
    has_tfws: bool = False
    has_pwd: bool = False
    has_defence: bool = False
    is_orphan: bool = False
    is_minority: bool = False
    
    # Preferences
    preferred_branches: List[str] = field(default_factory=list)
    preferred_cities: List[str] = field(default_factory=list)
    max_fees: Optional[float] = None  # Annual fees in lakhs
    priority_type: PriorityType = PriorityType.BALANCED
    
    # College type preferences
    prefer_government: bool = True
    prefer_autonomous: bool = True
    include_private: bool = True


@dataclass
class PreferenceListItem:
    """Single item in the recommended preference list"""
    rank: int
    college_code: str
    college_name: str
    branch_code: str
    branch_name: str
    category_code: str
    probability: float
    chance_category: AdmissionChance
    trend: str
    notes: List[str]
    is_recommended: bool = True
    recommendation_reason: str = ""


@dataclass
class RecommendationResult:
    """Complete recommendation result"""
    student_profile: StudentProfile
    preference_list: List[PreferenceListItem]
    summary: Dict[str, int]  # Count by category
    warnings: List[str]
    strategy_notes: List[str]
    cutoff_adjustment: float


class RecommendationEngine:
    """
    Generates optimized preference lists for students
    """
    
    # Recommended distribution
    DREAM_RATIO = 0.20   # 20% dream options
    TARGET_RATIO = 0.50  # 50% target options
    SAFE_RATIO = 0.30    # 30% safe options
    
    # Minimum recommendations
    MIN_SAFE_OPTIONS = 5
    MIN_TOTAL_OPTIONS = 15
    
    def __init__(
        self, 
        probability_engine: ProbabilityEngine,
        college_metadata: Optional[pd.DataFrame] = None
    ):
        self.prob_engine = probability_engine
        self.college_metadata = college_metadata
    
    def generate_applicable_categories(
        self, 
        profile: StudentProfile
    ) -> List[str]:
        """
        Generate all applicable category codes for the student
        """
        categories = []
        
        # Gender prefix
        g_prefix = 'G'
        l_prefix = 'L' if profile.gender.lower() == 'female' else None
        
        # Base category
        base_cat = profile.category.upper()
        
        # Seat suffix based on home university
        if profile.home_university:
            seat_suffixes = ['S', 'H', 'O']  # State, Home, Other
        else:
            seat_suffixes = ['S']  # State level only
        
        # Generate combinations for base category
        for suffix in seat_suffixes:
            categories.append(f"G{base_cat}{suffix}")
            if l_prefix and profile.gender.lower() == 'female':
                categories.append(f"L{base_cat}{suffix}")
        
        # Add OPEN category if not already OPEN
        if base_cat != 'OPEN':
            for suffix in seat_suffixes:
                categories.append(f"GOPEN{suffix}")
                if l_prefix and profile.gender.lower() == 'female':
                    categories.append(f"LOPEN{suffix}")
        
        # Add special quotas
        if profile.has_tfws:
            categories.append('TFWS')
        
        if profile.has_pwd:
            for suffix in seat_suffixes:
                categories.append(f"PWDOPEN{suffix}")
                categories.append(f"PWD{base_cat}{suffix}")
        
        if profile.has_defence:
            for suffix in seat_suffixes:
                categories.append(f"DEFOPEN{suffix}")
                categories.append(f"DEF{base_cat}{suffix}")
        
        if profile.is_orphan:
            categories.append('ORPHAN')
        
        # EWS (typically available for OPEN category)
        if base_cat == 'OPEN':
            categories.append('EWS')
        
        return list(set(categories))
    
    def generate_recommendations(
        self,
        profile: StudentProfile,
        cutoff_adjustment: float = 0.0,
        max_options: int = 100
    ) -> RecommendationResult:
        """
        Generate optimized preference list for student
        
        Args:
            profile: Complete student profile
            cutoff_adjustment: Global cutoff adjustment percentage
            max_options: Maximum number of options to include
        
        Returns:
            RecommendationResult with ordered preference list
        """
        warnings = []
        strategy_notes = []
        
        # Get applicable categories
        applicable_categories = self.generate_applicable_categories(profile)
        
        # Collect all options with probabilities
        all_options = []
        
        for category in applicable_categories:
            options = self.prob_engine.get_all_options_for_student(
                student_percentile=profile.percentile,
                category_code=category,
                quota=profile.quota,
                target_round=1,
                cutoff_adjustment=cutoff_adjustment,
                min_probability=0.01
            )
            all_options.extend(options)
        
        # Remove duplicates (keep highest probability)
        unique_options = self._deduplicate_options(all_options)
        
        # Apply filters
        filtered_options = self._apply_filters(unique_options, profile)
        
        # Check if we have enough options
        if len(filtered_options) < self.MIN_TOTAL_OPTIONS:
            warnings.append(
                f"⚠️ Only {len(filtered_options)} options found. "
                "Consider relaxing your filters or checking special quotas."
            )
        
        # Score and rank options
        scored_options = self._score_options(filtered_options, profile)
        
        # Generate optimized preference order
        preference_list = self._optimize_preference_order(
            scored_options, 
            profile,
            max_options
        )
        
        # Add strategy notes
        strategy_notes = self._generate_strategy_notes(preference_list, profile)
        
        # Low percentile warning
        if profile.percentile < 50:
            warnings.append(
                "⚠️ With percentile below 50, CAP options are limited. "
                "Consider: ACAP rounds, diploma courses, or management quota."
            )
        
        # Count by category
        summary = {
            'total': len(preference_list),
            'dream': sum(1 for p in preference_list if p.chance_category == AdmissionChance.DREAM),
            'target': sum(1 for p in preference_list if p.chance_category == AdmissionChance.TARGET),
            'safe': sum(1 for p in preference_list if p.chance_category in [AdmissionChance.SAFE, AdmissionChance.ASSURED]),
            'government': sum(1 for p in preference_list if 'Government' in p.college_name),
        }
        
        return RecommendationResult(
            student_profile=profile,
            preference_list=preference_list,
            summary=summary,
            warnings=warnings,
            strategy_notes=strategy_notes,
            cutoff_adjustment=cutoff_adjustment
        )
    
    def _deduplicate_options(
        self, 
        options: List[ProbabilityResult]
    ) -> List[ProbabilityResult]:
        """
        Remove duplicate college-branch combinations, keeping highest probability
        """
        seen = {}
        for opt in options:
            key = (opt.college_code, opt.branch_code)
            if key not in seen or opt.probability > seen[key].probability:
                seen[key] = opt
        return list(seen.values())
    
    def _apply_filters(
        self,
        options: List[ProbabilityResult],
        profile: StudentProfile
    ) -> List[ProbabilityResult]:
        """
        Apply user preference filters
        """
        filtered = options
        
        # Branch filter
        if profile.preferred_branches:
            branch_codes = set(profile.preferred_branches)
            # Include exact matches and partial matches
            filtered = [
                opt for opt in filtered
                if opt.branch_code in branch_codes or
                any(pb.lower() in opt.branch_name.lower() for pb in profile.preferred_branches)
            ]
        
        # College type filter
        if not profile.include_private:
            filtered = [
                opt for opt in filtered
                if 'Government' in opt.college_name or 'Govt' in opt.college_name
            ]
        
        # Fee filter (if metadata available)
        if profile.max_fees and self.college_metadata is not None:
            # TODO: Implement fee filtering with metadata
            pass
        
        return filtered
    
    def _score_options(
        self,
        options: List[ProbabilityResult],
        profile: StudentProfile
    ) -> List[Tuple[ProbabilityResult, float]]:
        """
        Score options based on desirability and probability
        
        Returns list of (option, score) tuples
        """
        scored = []
        
        for opt in options:
            score = 0.0
            
            # Probability factor (0-40 points)
            score += opt.probability * 40
            
            # College type bonus (0-30 points)
            if 'Government' in opt.college_name:
                score += 30
            elif opt.is_autonomous:
                score += 20
            else:
                score += 10
            
            # Branch preference bonus (0-20 points)
            if profile.preferred_branches:
                if opt.branch_code in profile.preferred_branches:
                    score += 20
                elif any(pb.lower() in opt.branch_name.lower() for pb in profile.preferred_branches):
                    score += 15
            
            # Trend bonus (0-10 points)
            if opt.trend == "falling":
                score += 10  # Favorable trend
            elif opt.trend == "stable":
                score += 5
            
            # Confidence factor
            score *= opt.confidence
            
            scored.append((opt, score))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return scored
    
    def _optimize_preference_order(
        self,
        scored_options: List[Tuple[ProbabilityResult, float]],
        profile: StudentProfile,
        max_options: int
    ) -> List[PreferenceListItem]:
        """
        Create optimized preference order following Dream -> Target -> Safe strategy
        """
        # Classify options
        dreams = []
        targets = []
        safes = []
        
        for opt, score in scored_options:
            if opt.chance_category in [AdmissionChance.REACH, AdmissionChance.DREAM]:
                dreams.append((opt, score))
            elif opt.chance_category == AdmissionChance.TARGET:
                targets.append((opt, score))
            else:
                safes.append((opt, score))
        
        # Calculate distribution
        total = min(max_options, len(scored_options))
        n_dreams = min(len(dreams), int(total * self.DREAM_RATIO))
        n_safes = max(self.MIN_SAFE_OPTIONS, min(len(safes), int(total * self.SAFE_RATIO)))
        n_targets = total - n_dreams - n_safes
        n_targets = min(n_targets, len(targets))
        
        # Build preference list
        preference_list = []
        rank = 1
        
        # Add dream options (sorted by score within category)
        for opt, score in dreams[:n_dreams]:
            item = PreferenceListItem(
                rank=rank,
                college_code=opt.college_code,
                college_name=opt.college_name,
                branch_code=opt.branch_code,
                branch_name=opt.branch_name,
                category_code=opt.category_code,
                probability=opt.probability,
                chance_category=opt.chance_category,
                trend=opt.trend,
                notes=opt.notes,
                is_recommended=True,
                recommendation_reason="Dream option - aspirational choice"
            )
            preference_list.append(item)
            rank += 1
        
        # Add target options
        for opt, score in targets[:n_targets]:
            item = PreferenceListItem(
                rank=rank,
                college_code=opt.college_code,
                college_name=opt.college_name,
                branch_code=opt.branch_code,
                branch_name=opt.branch_name,
                category_code=opt.category_code,
                probability=opt.probability,
                chance_category=opt.chance_category,
                trend=opt.trend,
                notes=opt.notes,
                is_recommended=True,
                recommendation_reason="Target option - realistic chance"
            )
            preference_list.append(item)
            rank += 1
        
        # Add safe options
        for opt, score in safes[:n_safes]:
            item = PreferenceListItem(
                rank=rank,
                college_code=opt.college_code,
                college_name=opt.college_name,
                branch_code=opt.branch_code,
                branch_name=opt.branch_name,
                category_code=opt.category_code,
                probability=opt.probability,
                chance_category=opt.chance_category,
                trend=opt.trend,
                notes=opt.notes,
                is_recommended=True,
                recommendation_reason="Safe option - high confidence backup"
            )
            preference_list.append(item)
            rank += 1
        
        return preference_list
    
    def _generate_strategy_notes(
        self,
        preference_list: List[PreferenceListItem],
        profile: StudentProfile
    ) -> List[str]:
        """
        Generate strategic advice for the student
        """
        notes = []
        
        if len(preference_list) == 0:
            notes.append("❌ No options found matching your criteria. Try adjusting filters.")
            return notes
        
        # Count by category
        n_dreams = sum(1 for p in preference_list if p.chance_category in [AdmissionChance.DREAM, AdmissionChance.REACH])
        n_safes = sum(1 for p in preference_list if p.chance_category in [AdmissionChance.SAFE, AdmissionChance.ASSURED])
        
        notes.append(f"📋 Your list has {len(preference_list)} options: {n_dreams} dream, {len(preference_list) - n_dreams - n_safes} target, {n_safes} safe")
        
        if n_safes < 3:
            notes.append("⚠️ Consider adding more safe options to ensure admission")
        
        if n_dreams > len(preference_list) * 0.3:
            notes.append("💡 Your list has many dream options - don't forget realistic targets!")
        
        # TFWS note
        if profile.has_tfws:
            notes.append("✅ TFWS quota applied - check TFWS seats separately in each college")
        
        # Home university note
        if profile.home_university:
            notes.append(f"🏠 Home University ({profile.home_university}) preference applied")
        
        # Government college note
        if profile.prefer_government:
            n_govt = sum(1 for p in preference_list if 'Government' in p.college_name)
            notes.append(f"🏛️ {n_govt} government college options included")
        
        return notes
    
    def reorder_preference(
        self,
        current_list: List[PreferenceListItem],
        move_from: int,
        move_to: int
    ) -> List[PreferenceListItem]:
        """
        Reorder preference list (for What-If simulator)
        """
        if move_from < 0 or move_from >= len(current_list):
            return current_list
        if move_to < 0 or move_to >= len(current_list):
            return current_list
        
        item = current_list.pop(move_from)
        current_list.insert(move_to, item)
        
        # Update ranks
        for i, item in enumerate(current_list):
            item.rank = i + 1
        
        return current_list
    
    def analyze_reorder_impact(
        self,
        original_list: List[PreferenceListItem],
        new_list: List[PreferenceListItem],
        profile: StudentProfile
    ) -> Dict:
        """
        Analyze the impact of reordering preferences
        """
        impact = {
            'changes': [],
            'risks': [],
            'benefits': [],
            'missed_opportunities': []
        }
        
        # Find items that moved significantly
        for orig_item in original_list:
            new_pos = next(
                (i for i, n in enumerate(new_list) 
                 if n.college_code == orig_item.college_code and 
                    n.branch_code == orig_item.branch_code),
                None
            )
            
            if new_pos is not None:
                change = new_pos - (orig_item.rank - 1)
                
                if abs(change) >= 3:
                    impact['changes'].append({
                        'college': orig_item.college_name,
                        'branch': orig_item.branch_name,
                        'old_rank': orig_item.rank,
                        'new_rank': new_pos + 1,
                        'change': change
                    })
        
        # Check for risks (safe option moved down)
        for i, item in enumerate(new_list):
            if item.chance_category in [AdmissionChance.SAFE, AdmissionChance.ASSURED]:
                if item.rank > len(new_list) * 0.8:
                    impact['risks'].append(
                        f"Safe option '{item.college_name} - {item.branch_name}' "
                        f"moved to position {item.rank}. Risk of missing backup!"
                    )
        
        # Check for benefits (dream option at top)
        if new_list and new_list[0].chance_category in [AdmissionChance.DREAM, AdmissionChance.REACH]:
            impact['benefits'].append(
                f"Dream option '{new_list[0].college_name}' at top - "
                "you'll be considered for it first!"
            )
        
        return impact


def analyze_missed_opportunities(
    student_percentile: float,
    preference_list: List[PreferenceListItem],
    all_options: List[ProbabilityResult]
) -> List[Dict]:
    """
    Identify colleges/branches the student might miss due to ordering
    """
    missed = []
    
    # Get all colleges in preference list
    in_list = set(
        (p.college_code, p.branch_code) 
        for p in preference_list
    )
    
    # Find high-probability options not in list
    for opt in all_options:
        key = (opt.college_code, opt.branch_code)
        if key not in in_list and opt.probability > 0.5:
            missed.append({
                'college': opt.college_name,
                'branch': opt.branch_name,
                'probability': opt.probability,
                'reason': "High probability but not in your preference list"
            })
    
    return missed[:10]  # Top 10 missed opportunities


if __name__ == "__main__":
    # Test recommendation engine
    from data_loader import create_sample_data
    from probability_engine import ProbabilityEngine
    
    # Create sample data
    sample_df = create_sample_data()
    prob_engine = ProbabilityEngine(sample_df)
    rec_engine = RecommendationEngine(prob_engine)
    
    # Create sample profile
    profile = StudentProfile(
        percentile=96.5,
        category="OBC",
        gender="male",
        quota="MH",
        home_university="Sant Gadge Baba Amravati University",
        has_tfws=True,
        preferred_branches=["Computer Science", "Information Technology"],
        priority_type=PriorityType.BRANCH_FIRST
    )
    
    # Generate recommendations
    result = rec_engine.generate_recommendations(profile, cutoff_adjustment=0)
    
    print("Recommendation Summary:")
    print(f"  Total options: {result.summary['total']}")
    print(f"  Dream: {result.summary['dream']}")
    print(f"  Target: {result.summary['target']}")
    print(f"  Safe: {result.summary['safe']}")
    print(f"\nWarnings: {result.warnings}")
    print(f"\nStrategy: {result.strategy_notes}")
    
    print("\nTop 5 Preferences:")
    for item in result.preference_list[:5]:
        print(f"  {item.rank}. {item.college_name} - {item.branch_name}")
        print(f"     Probability: {item.probability:.1%} ({item.chance_category.value})")
