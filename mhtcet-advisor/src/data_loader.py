"""
MHT-CET Cutoff Data Loader

This module handles:
1. Downloading PDFs from CET Cell website
2. Parsing cutoff data from PDFs
3. Normalizing and storing data in structured format
"""

import re
import json
import logging
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Tuple
import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CutoffEntry:
    """Single cutoff entry for a college-branch-category combination"""
    year: int
    round: int  # 1, 2, 3, 4
    college_code: str
    college_name: str
    branch_code: str
    branch_name: str
    category_code: str  # e.g., GOPENS, GSCS, etc.
    quota: str  # MH or AI
    home_university: str
    seat_type: str  # H (Home), O (Other), S (State)
    stage: int  # Allotment stage (usually 1 or 2)
    closing_rank: int
    closing_percentile: float
    college_type: str  # Government, Un-Aided, etc.
    is_autonomous: bool


@dataclass
class CollegeInfo:
    """College metadata"""
    code: str
    name: str
    city: str
    district: str
    college_type: str
    home_university: str
    is_autonomous: bool
    branches: List[str]


class CutoffDataLoader:
    """
    Handles loading and parsing of MHT-CET cutoff data from PDFs
    """
    
    # PDF URL patterns
    PDF_URLS = {
        2022: {
            'seat_matrix': 'http://fe2025.mahacet.org/2022/2022SeatMatrix.pdf',
            'cap1_mh': 'http://fe2025.mahacet.org/2022/2022ENGG_CAP1_CutOff.pdf',
            'cap1_ai': 'http://fe2025.mahacet.org/2022/2022ENGG_CAP1_AI_CutOff.pdf',
            'cap2_mh': 'http://fe2025.mahacet.org/2022/2022ENGG_CAP2_CutOff.pdf',
            'cap2_ai': 'http://fe2025.mahacet.org/2022/2022ENGG_CAP2_AI_CutOff.pdf',
            'cap3_mh': 'http://fe2025.mahacet.org/2022/2022ENGG_CAP3_CutOff.pdf',
            'cap3_ai': 'http://fe2025.mahacet.org/2022/2022ENGG_CAP3_AI_CutOff.pdf',
        },
        2023: {
            'seat_matrix': 'http://fe2025.mahacet.org/2023/2023SeatMatrix.pdf',
            'cap1_mh': 'http://fe2025.mahacet.org/2023/2023ENGG_CAP1_CutOff.pdf',
            'cap1_ai': 'http://fe2025.mahacet.org/2023/2023ENGG_CAP1_AI_CutOff.pdf',
            'cap2_mh': 'http://fe2025.mahacet.org/2023/2023ENGG_CAP2_CutOff.pdf',
            'cap2_ai': 'http://fe2025.mahacet.org/2023/2023ENGG_CAP2_AI_CutOff.pdf',
            'cap3_mh': 'http://fe2025.mahacet.org/2023/2023ENGG_CAP3_CutOff.pdf',
            'cap3_ai': 'http://fe2025.mahacet.org/2023/2023ENGG_CAP3_AI_CutOff.pdf',
        },
        2024: {
            'seat_matrix': 'http://fe2025.mahacet.org/2024/2024SeatMatrix.pdf',
            'cap1_mh': 'http://fe2025.mahacet.org/2024/2024ENGG_CAP1_CutOff.pdf',
            'cap1_ai': 'http://fe2025.mahacet.org/2024/2024ENGG_CAP1_AI_CutOff.pdf',
            'cap2_mh': 'http://fe2025.mahacet.org/2024/2024ENGG_CAP2_CutOff.pdf',
            'cap2_ai': 'http://fe2025.mahacet.org/2024/2024ENGG_CAP2_AI_CutOff.pdf',
            'cap3_mh': 'http://fe2025.mahacet.org/2024/2024ENGG_CAP3_CutOff.pdf',
            'cap3_ai': 'http://fe2025.mahacet.org/2024/2024ENGG_CAP3_AI_CutOff.pdf',
        },
    }
    
    # Regex patterns for parsing
    COLLEGE_PATTERN = r'^(\d{5})\s*-\s*(.+)$'
    BRANCH_PATTERN = r'^(\d{10})\s*-\s*(.+)$'
    CUTOFF_PATTERN = r'(\d+)\s*\((\d+\.\d+)\)'
    CATEGORY_PATTERN = r'^([GL]?(?:OPEN|SC|ST|VJ|NT[123]|OBC|SEBC|EWS|PWD\w*|DEF\w*|TFWS|ORPHAN|MI)[SHO]?)$'
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw"
        self.parsed_dir = self.data_dir / "parsed"
        self.processed_dir = self.data_dir / "processed"
        
        # Create directories
        for dir_path in [self.raw_dir, self.parsed_dir, self.processed_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def parse_cutoff_text(self, text: str, year: int, round_num: int, quota: str) -> List[CutoffEntry]:
        """
        Parse raw text extracted from cutoff PDF into structured entries
        
        The PDF format is:
        COLLEGE_CODE - College Name
        BRANCH_CODE - Branch Name
        Status: Type | Home University: University Name
        [Seat Type Header]
        CATEGORY1 CATEGORY2 CATEGORY3 ...
        Stage RANK(PERCENTILE) RANK(PERCENTILE) ...
        """
        entries = []
        lines = text.strip().split('\n')
        
        current_college_code = None
        current_college_name = None
        current_branch_code = None
        current_branch_name = None
        current_college_type = None
        current_home_university = None
        current_is_autonomous = False
        current_seat_type = "S"  # Default to State level
        current_categories = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines
            if not line:
                i += 1
                continue
            
            # Check for college header
            college_match = re.match(self.COLLEGE_PATTERN, line)
            if college_match:
                current_college_code = college_match.group(1)
                current_college_name = college_match.group(2).strip()
                i += 1
                continue
            
            # Check for branch header
            branch_match = re.match(self.BRANCH_PATTERN, line)
            if branch_match:
                current_branch_code = branch_match.group(1)
                current_branch_name = branch_match.group(2).strip()
                i += 1
                continue
            
            # Check for status line
            if line.startswith("Status:"):
                status_parts = line.split("|")
                for part in status_parts:
                    part = part.strip()
                    if "Status:" in part:
                        status_text = part.replace("Status:", "").strip()
                        current_college_type = status_text
                        current_is_autonomous = "Autonomous" in status_text
                    elif "Home University" in part:
                        current_home_university = part.split(":")[-1].strip()
                i += 1
                continue
            
            # Check for seat type headers
            if "Home University Seats" in line:
                if "Other Than Home University Candidates" in line:
                    current_seat_type = "O"
                else:
                    current_seat_type = "H"
                i += 1
                continue
            elif "State Level" in line:
                current_seat_type = "S"
                i += 1
                continue
            
            # Check for category header line
            categories_in_line = re.findall(self.CATEGORY_PATTERN, line)
            if len(categories_in_line) >= 3:  # Multiple categories indicate header
                current_categories = categories_in_line
                i += 1
                continue
            
            # Check for data line (Stage + cutoffs)
            if line.startswith(("I ", "II ", "III ", "IV ", " I ", " II ")):
                stage_match = re.match(r'\s*(I{1,4}|IV)\s+', line)
                if stage_match:
                    stage_str = stage_match.group(1).strip()
                    stage_map = {"I": 1, "II": 2, "III": 3, "IV": 4}
                    stage = stage_map.get(stage_str, 1)
                    
                    # Extract all cutoffs
                    cutoffs = re.findall(self.CUTOFF_PATTERN, line)
                    
                    # Match cutoffs with categories
                    for idx, (rank_str, percentile_str) in enumerate(cutoffs):
                        if idx < len(current_categories):
                            try:
                                entry = CutoffEntry(
                                    year=year,
                                    round=round_num,
                                    college_code=current_college_code or "",
                                    college_name=current_college_name or "",
                                    branch_code=current_branch_code or "",
                                    branch_name=current_branch_name or "",
                                    category_code=current_categories[idx],
                                    quota=quota,
                                    home_university=current_home_university or "",
                                    seat_type=current_seat_type,
                                    stage=stage,
                                    closing_rank=int(rank_str),
                                    closing_percentile=float(percentile_str),
                                    college_type=current_college_type or "",
                                    is_autonomous=current_is_autonomous
                                )
                                entries.append(entry)
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Error parsing entry: {e}")
                
                i += 1
                continue
            
            i += 1
        
        return entries
    
    def load_from_csv(self, filepath: str) -> pd.DataFrame:
        """Load cutoff data from pre-parsed CSV file"""
        return pd.read_csv(filepath)
    
    def load_from_parquet(self, filepath: str) -> pd.DataFrame:
        """Load cutoff data from parquet file (faster)"""
        return pd.read_parquet(filepath)
    
    def save_to_parquet(self, df: pd.DataFrame, filepath: str):
        """Save dataframe to parquet format"""
        df.to_parquet(filepath, index=False)
    
    def entries_to_dataframe(self, entries: List[CutoffEntry]) -> pd.DataFrame:
        """Convert list of CutoffEntry to DataFrame"""
        return pd.DataFrame([asdict(e) for e in entries])
    
    def get_combined_cutoff_data(self) -> pd.DataFrame:
        """
        Load and combine all years' cutoff data
        Returns a single DataFrame with all entries
        """
        parquet_path = self.parsed_dir / "cutoffs_combined.parquet"
        
        if parquet_path.exists():
            logger.info(f"Loading cached data from {parquet_path}")
            return pd.read_parquet(parquet_path)
        
        logger.warning("Combined data not found. Please run data extraction first.")
        return pd.DataFrame()
    
    def extract_category_from_code(self, category_code: str) -> Dict:
        """
        Parse category code into components
        
        Examples:
        - GOPENS -> Gender: General, Category: OPEN, Seat: State
        - LSCH -> Gender: Ladies, Category: SC, Seat: Home
        - PWDOPENS -> Special: PWD, Category: OPEN, Seat: State
        """
        result = {
            'gender': 'any',
            'base_category': 'OPEN',
            'seat_level': 'state',
            'is_special': False,
            'special_type': None
        }
        
        code = category_code.upper()
        
        # Check for special quotas first
        special_prefixes = ['PWD', 'DEF', 'TFWS', 'ORPHAN', 'MI']
        for prefix in special_prefixes:
            if code.startswith(prefix):
                result['is_special'] = True
                result['special_type'] = prefix
                code = code[len(prefix):]
                break
        
        # Check gender
        if code.startswith('L'):
            result['gender'] = 'female'
            code = code[1:]
        elif code.startswith('G'):
            result['gender'] = 'any'
            code = code[1:]
        
        # Check seat level (last character)
        if code.endswith('S'):
            result['seat_level'] = 'state'
            code = code[:-1]
        elif code.endswith('H'):
            result['seat_level'] = 'home'
            code = code[:-1]
        elif code.endswith('O'):
            result['seat_level'] = 'other'
            code = code[:-1]
        
        # Remaining is base category
        result['base_category'] = code if code else 'OPEN'
        
        return result
    
    def get_applicable_categories(
        self, 
        base_category: str, 
        gender: str, 
        home_university: Optional[str] = None,
        special_quotas: List[str] = None
    ) -> List[str]:
        """
        Generate list of applicable category codes for a student profile
        
        Args:
            base_category: Student's base category (OPEN, SC, ST, OBC, etc.)
            gender: 'male' or 'female'
            home_university: Student's home university (if applicable)
            special_quotas: List of special quotas (TFWS, PWD, DEF, etc.)
        
        Returns:
            List of category codes student can apply under
        """
        categories = []
        special_quotas = special_quotas or []
        
        # Determine gender prefix
        gender_prefixes = ['G']  # General always applicable
        if gender.lower() == 'female':
            gender_prefixes.append('L')
        
        # Determine seat suffixes
        seat_suffixes = ['S']  # State level always
        if home_university:
            seat_suffixes.extend(['H', 'O'])
        
        # Base categories (student's own + OPEN if not OPEN)
        base_cats = [base_category]
        if base_category != 'OPEN':
            base_cats.append('OPEN')
        
        # Generate all combinations
        for g_prefix in gender_prefixes:
            for b_cat in base_cats:
                for s_suffix in seat_suffixes:
                    categories.append(f"{g_prefix}{b_cat}{s_suffix}")
        
        # Add special quotas
        for quota in special_quotas:
            if quota == 'TFWS':
                categories.append('TFWS')
            elif quota == 'EWS':
                categories.append('EWS')
            else:
                # PWD, DEF combine with category
                for g_prefix in gender_prefixes:
                    for s_suffix in seat_suffixes:
                        categories.append(f"{quota}{g_prefix}{base_category}{s_suffix}")
        
        return list(set(categories))


class SeatMatrixLoader:
    """Handles loading seat matrix data"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
    
    def load_seat_matrix(self, year: int) -> pd.DataFrame:
        """Load seat matrix for a given year"""
        filepath = self.data_dir / "parsed" / f"seat_matrix_{year}.parquet"
        if filepath.exists():
            return pd.read_parquet(filepath)
        return pd.DataFrame()
    
    def get_seats_for_college_branch(
        self, 
        df: pd.DataFrame, 
        college_code: str, 
        branch_code: str,
        category: str
    ) -> int:
        """Get number of seats for specific college-branch-category"""
        mask = (
            (df['college_code'] == college_code) &
            (df['branch_code'] == branch_code) &
            (df['category'] == category)
        )
        result = df.loc[mask, 'seats']
        return int(result.iloc[0]) if len(result) > 0 else 0


def create_sample_data() -> pd.DataFrame:
    """
    Create sample cutoff data for testing
    Based on actual 2024 CAP Round I data structure
    """
    
    sample_data = [
        # Government College of Engineering, Amravati - CSE
        {
            'year': 2024, 'round': 1,
            'college_code': '01002', 'college_name': 'Government College of Engineering, Amravati',
            'branch_code': '0100224210', 'branch_name': 'Computer Science and Engineering',
            'category_code': 'GOPENS', 'quota': 'MH',
            'home_university': 'Autonomous Institute', 'seat_type': 'S', 'stage': 1,
            'closing_rank': 7872, 'closing_percentile': 97.39,
            'college_type': 'Government Autonomous', 'is_autonomous': True
        },
        {
            'year': 2024, 'round': 1,
            'college_code': '01002', 'college_name': 'Government College of Engineering, Amravati',
            'branch_code': '0100224210', 'branch_name': 'Computer Science and Engineering',
            'category_code': 'GOBCS', 'quota': 'MH',
            'home_university': 'Autonomous Institute', 'seat_type': 'S', 'stage': 1,
            'closing_rank': 8931, 'closing_percentile': 97.04,
            'college_type': 'Government Autonomous', 'is_autonomous': True
        },
        {
            'year': 2024, 'round': 1,
            'college_code': '01002', 'college_name': 'Government College of Engineering, Amravati',
            'branch_code': '0100224210', 'branch_name': 'Computer Science and Engineering',
            'category_code': 'GSCS', 'quota': 'MH',
            'home_university': 'Autonomous Institute', 'seat_type': 'S', 'stage': 1,
            'closing_rank': 17571, 'closing_percentile': 94.17,
            'college_type': 'Government Autonomous', 'is_autonomous': True
        },
        # Add more sample entries for different years to show trends
        {
            'year': 2023, 'round': 1,
            'college_code': '01002', 'college_name': 'Government College of Engineering, Amravati',
            'branch_code': '0100224210', 'branch_name': 'Computer Science and Engineering',
            'category_code': 'GOPENS', 'quota': 'MH',
            'home_university': 'Autonomous Institute', 'seat_type': 'S', 'stage': 1,
            'closing_rank': 8500, 'closing_percentile': 97.10,
            'college_type': 'Government Autonomous', 'is_autonomous': True
        },
        {
            'year': 2022, 'round': 1,
            'college_code': '01002', 'college_name': 'Government College of Engineering, Amravati',
            'branch_code': '0100224210', 'branch_name': 'Computer Science and Engineering',
            'category_code': 'GOPENS', 'quota': 'MH',
            'home_university': 'Autonomous Institute', 'seat_type': 'S', 'stage': 1,
            'closing_rank': 9200, 'closing_percentile': 96.85,
            'college_type': 'Government Autonomous', 'is_autonomous': True
        },
    ]
    
    return pd.DataFrame(sample_data)


if __name__ == "__main__":
    # Test the data loader
    loader = CutoffDataLoader()
    
    # Create and save sample data
    sample_df = create_sample_data()
    print("Sample data created:")
    print(sample_df.head())
    
    # Test category extraction
    test_categories = ['GOPENS', 'LSCH', 'PWDOBCS', 'TFWS', 'EWS']
    for cat in test_categories:
        parsed = loader.extract_category_from_code(cat)
        print(f"{cat} -> {parsed}")
    
    # Test applicable categories
    applicable = loader.get_applicable_categories(
        base_category='OBC',
        gender='female',
        home_university='University of Mumbai',
        special_quotas=['TFWS']
    )
    print(f"\nApplicable categories for Female OBC with TFWS: {applicable}")
