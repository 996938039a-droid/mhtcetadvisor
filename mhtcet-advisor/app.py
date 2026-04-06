"""
MHT-CET College Preference Advisor - Streamlit Web Application

A comprehensive tool to help Maharashtra engineering students optimize
their CAP round preference lists using historical cutoff data and
probability modeling.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import yaml
from pathlib import Path

# Import local modules
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.data_loader import CutoffDataLoader, create_sample_data
from src.probability_engine import ProbabilityEngine, AdmissionChance, RoundSimulator
from src.recommendation_engine import (
    RecommendationEngine, StudentProfile, PriorityType,
    PreferenceListItem
)
from src.export_utils import export_to_excel, export_to_pdf

# Page configuration
st.set_page_config(
    page_title="MHT-CET College Preference Advisor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1F4E79;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        border: 1px solid #e0e0e0;
    }
    .dream-badge {
        background-color: #FFF2CC;
        color: #856404;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-weight: bold;
    }
    .target-badge {
        background-color: #E2EFDA;
        color: #155724;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-weight: bold;
    }
    .safe-badge {
        background-color: #DDEBF7;
        color: #004085;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-weight: bold;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0 24px;
        background-color: #f0f2f6;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)


# Initialize session state
def init_session_state():
    """Initialize session state variables"""
    if 'cutoff_data' not in st.session_state:
        st.session_state.cutoff_data = None
    if 'recommendations' not in st.session_state:
        st.session_state.recommendations = None
    if 'preference_list' not in st.session_state:
        st.session_state.preference_list = []
    if 'profile' not in st.session_state:
        st.session_state.profile = None


@st.cache_data
def load_config():
    """Load configuration from YAML files"""
    config_path = Path(__file__).parent / "config" / "categories.yaml"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return {}


@st.cache_data
def load_cutoff_data():
    """Load cutoff data (use sample for demo)"""
    # For demo purposes, use sample data
    # In production, this would load from parsed PDFs
    return create_sample_data()


def get_category_options():
    """Get list of category options"""
    return [
        "OPEN", "OBC", "SC", "ST", "VJ", 
        "NT1", "NT2", "NT3", "EWS", "SEBC"
    ]


def get_home_university_options():
    """Get list of home universities"""
    return [
        "University of Mumbai",
        "Savitribai Phule Pune University",
        "Rashtrasant Tukadoji Maharaj Nagpur University",
        "Sant Gadge Baba Amravati University",
        "Dr. Babasaheb Ambedkar Marathwada University",
        "Swami Ramanand Teerth Marathwada University",
        "Dr. Babasaheb Ambedkar Technological University",
        "North Maharashtra University",
        "Shivaji University",
        "Autonomous Institute (State Level)"
    ]


def render_sidebar():
    """Render the sidebar with student profile inputs"""
    st.sidebar.markdown("## 👤 Student Profile")
    
    # Percentile input with multiple options
    percentile_input_type = st.sidebar.radio(
        "How would you like to enter your score?",
        ["Exact Percentile", "Percentile Range", "Merit Rank"],
        horizontal=True
    )
    
    if percentile_input_type == "Exact Percentile":
        percentile = st.sidebar.number_input(
            "Your MHT-CET Percentile",
            min_value=0.0,
            max_value=100.0,
            value=85.0,
            step=0.01,
            help="Enter your exact percentile score"
        )
    elif percentile_input_type == "Percentile Range":
        col1, col2 = st.sidebar.columns(2)
        with col1:
            min_p = st.number_input("Min", min_value=0.0, max_value=100.0, value=80.0)
        with col2:
            max_p = st.number_input("Max", min_value=0.0, max_value=100.0, value=90.0)
        percentile = (min_p + max_p) / 2
        st.sidebar.caption(f"Using midpoint: {percentile:.2f}")
    else:  # Merit Rank
        rank = st.sidebar.number_input(
            "Your Merit Rank",
            min_value=1,
            max_value=500000,
            value=10000,
            step=1
        )
        # Approximate conversion (this should be based on actual data)
        total_candidates = 300000  # Approximate
        percentile = (1 - (rank / total_candidates)) * 100
        percentile = max(0, min(100, percentile))
        st.sidebar.caption(f"Approximate Percentile: {percentile:.2f}")
    
    st.sidebar.markdown("---")
    
    # Category selection
    category = st.sidebar.selectbox(
        "Category",
        get_category_options(),
        help="Select your reservation category"
    )
    
    # Gender
    gender = st.sidebar.radio(
        "Gender",
        ["Male", "Female"],
        horizontal=True
    )
    
    # Quota
    quota = st.sidebar.radio(
        "Quota Type",
        ["MH (Maharashtra)", "AI (All India)"],
        horizontal=True
    )
    quota = "MH" if "MH" in quota else "AI"
    
    # Home University
    home_university = st.sidebar.selectbox(
        "Home University",
        ["Not Applicable"] + get_home_university_options(),
        help="Select your home university for quota preference"
    )
    if home_university == "Not Applicable":
        home_university = None
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎯 Special Quotas")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        has_tfws = st.checkbox("TFWS", help="Tuition Fee Waiver (Income < ₹8L)")
        has_pwd = st.checkbox("PWD", help="Person with Disability (40%+)")
    with col2:
        has_defence = st.checkbox("Defence", help="Defence personnel ward")
        is_orphan = st.checkbox("Orphan", help="Orphan quota")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Cutoff Adjustment")
    
    cutoff_adjustment = st.sidebar.slider(
        "Expected Cutoff Change",
        min_value=-15.0,
        max_value=15.0,
        value=0.0,
        step=0.5,
        help="Adjust if you expect cutoffs to be higher (+) or lower (-) than historical"
    )
    
    if cutoff_adjustment > 0:
        st.sidebar.warning(f"⬆️ Expecting {cutoff_adjustment:.1f}% stricter cutoffs")
    elif cutoff_adjustment < 0:
        st.sidebar.success(f"⬇️ Expecting {abs(cutoff_adjustment):.1f}% easier cutoffs")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎓 Branch Preferences")
    
    branch_families = [
        "Computer Science / IT",
        "Electronics & Telecommunication",
        "Electrical Engineering",
        "Mechanical Engineering",
        "Civil Engineering",
        "Chemical Engineering",
        "Other Branches"
    ]
    
    preferred_branches = st.sidebar.multiselect(
        "Preferred Branch Families",
        branch_families,
        default=["Computer Science / IT"],
        help="Select branch families you're interested in"
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🏛️ College Preferences")
    
    prefer_government = st.sidebar.checkbox("Prefer Government Colleges", value=True)
    include_private = st.sidebar.checkbox("Include Private Colleges", value=True)
    
    # Create profile
    profile = StudentProfile(
        percentile=percentile,
        category=category,
        gender=gender.lower(),
        quota=quota,
        home_university=home_university,
        has_tfws=has_tfws,
        has_pwd=has_pwd,
        has_defence=has_defence,
        is_orphan=is_orphan,
        preferred_branches=preferred_branches,
        prefer_government=prefer_government,
        include_private=include_private,
        priority_type=PriorityType.BALANCED
    )
    
    return profile, cutoff_adjustment


def render_header():
    """Render the main header"""
    st.markdown('<h1 class="main-header">🎓 MHT-CET College Preference Advisor</h1>', 
                unsafe_allow_html=True)
    st.markdown('''
        <p class="sub-header">
            Optimize your CAP round preferences using AI-powered analysis of 4 years of historical cutoff data
        </p>
    ''', unsafe_allow_html=True)


def render_metrics(result):
    """Render summary metrics"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Options",
            value=result.summary['total'],
            help="Total number of college-branch options"
        )
    
    with col2:
        st.metric(
            label="Dream Options",
            value=result.summary['dream'],
            delta="Aspirational",
            delta_color="off"
        )
    
    with col3:
        st.metric(
            label="Target Options",
            value=result.summary['target'],
            delta="Realistic",
            delta_color="off"
        )
    
    with col4:
        st.metric(
            label="Safe Options",
            value=result.summary['safe'],
            delta="Backup",
            delta_color="off"
        )


def get_chance_badge(chance_category):
    """Get HTML badge for chance category"""
    badges = {
        AdmissionChance.DREAM: '<span class="dream-badge">🌟 DREAM</span>',
        AdmissionChance.REACH: '<span class="dream-badge">🎯 REACH</span>',
        AdmissionChance.TARGET: '<span class="target-badge">✅ TARGET</span>',
        AdmissionChance.SAFE: '<span class="safe-badge">🛡️ SAFE</span>',
        AdmissionChance.ASSURED: '<span class="safe-badge">✨ ASSURED</span>',
    }
    return badges.get(chance_category, '<span>Unknown</span>')


def render_preference_list(preference_list):
    """Render the preference list as an interactive table"""
    if not preference_list:
        st.warning("No recommendations generated yet. Please check your profile settings.")
        return
    
    # Convert to DataFrame for display
    data = []
    for item in preference_list:
        data.append({
            "Rank": item.rank,
            "College": item.college_name,
            "Branch": item.branch_name,
            "Category": item.category_code,
            "Probability": f"{item.probability:.1%}",
            "Chance": item.chance_category.value,
            "Trend": item.trend.capitalize()
        })
    
    df = pd.DataFrame(data)
    
    # Style the dataframe
    def color_chance(val):
        colors = {
            "Dream": "background-color: #FFF2CC",
            "Reach": "background-color: #FFE6CC",
            "Target": "background-color: #E2EFDA",
            "Safe": "background-color: #DDEBF7",
            "Assured": "background-color: #C6EFCE"
        }
        return colors.get(val, "")
    
    styled_df = df.style.applymap(color_chance, subset=['Chance'])
    
    st.dataframe(
        styled_df,
        use_container_width=True,
        height=400,
        column_config={
            "Rank": st.column_config.NumberColumn("Rank", width="small"),
            "Probability": st.column_config.TextColumn("Prob.", width="small"),
        }
    )


def render_what_if_simulator(preference_list, profile, prob_engine):
    """Render the What-If simulator tab"""
    st.markdown("### 🔄 What-If Simulator")
    st.info("""
        Reorder your preferences to see how it affects your admission chances.
        Drag items up or down in the list below.
    """)
    
    if not preference_list:
        st.warning("Generate recommendations first to use the What-If simulator.")
        return
    
    # Simple reorder interface
    st.markdown("#### Move an option:")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        options = [f"{p.rank}. {p.college_name} - {p.branch_name}" for p in preference_list[:20]]
        selected = st.selectbox("Select option to move", options)
    
    with col2:
        from_pos = st.number_input("From position", min_value=1, max_value=len(preference_list), value=1)
    
    with col3:
        to_pos = st.number_input("To position", min_value=1, max_value=len(preference_list), value=1)
    
    if st.button("🔄 Simulate Reorder"):
        if from_pos != to_pos:
            st.success(f"Simulating moving option from position {from_pos} to {to_pos}...")
            
            # Show impact
            st.markdown("#### Impact Analysis")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Before:**")
                st.write(f"Position {from_pos}: {preference_list[from_pos-1].college_name}")
            
            with col2:
                st.markdown("**After:**")
                st.write(f"Position {to_pos}: (moved)")
            
            st.info("💡 Remember: In CAP, you get allotted to your HIGHEST preference where your rank qualifies!")


def render_round_simulator(preference_list, profile, prob_engine):
    """Render the multi-round simulator"""
    st.markdown("### 🔮 Multi-Round Simulation")
    st.info("""
        See how your chances evolve across CAP rounds. 
        Later rounds typically have lower cutoffs as seats become vacant.
    """)
    
    if not preference_list:
        st.warning("Generate recommendations first.")
        return
    
    # Round-wise probability visualization
    round_data = []
    for item in preference_list[:10]:  # Top 10 preferences
        for round_num in [1, 2, 3, 4]:
            # Simulate probability change per round
            base_prob = item.probability
            round_adjustment = {1: 0, 2: 0.05, 3: 0.10, 4: 0.15}
            adjusted_prob = min(1.0, base_prob + round_adjustment[round_num])
            
            round_data.append({
                "College": f"{item.college_name[:20]}...",
                "Round": f"Round {round_num}",
                "Probability": adjusted_prob
            })
    
    if round_data:
        df = pd.DataFrame(round_data)
        
        # Pivot for heatmap-style display
        pivot_df = df.pivot(index="College", columns="Round", values="Probability")
        
        st.dataframe(
            pivot_df.style.background_gradient(cmap="RdYlGn", vmin=0, vmax=1).format("{:.0%}"),
            use_container_width=True
        )


def render_float_freeze_advisor(preference_list, profile):
    """Render Float/Freeze/Slide advice section"""
    st.markdown("### 🎯 Float / Freeze / Slide Advisor")
    
    st.markdown("""
        After each CAP round allotment, you have three options:
        
        | Action | What it means |
        |--------|---------------|
        | **FREEZE** | Accept current seat, exit process |
        | **FLOAT** | Keep current seat, try for any better option |
        | **SLIDE** | Keep current seat, try for better branch in same college |
    """)
    
    st.markdown("---")
    
    # Simulate current allotment
    st.markdown("#### Simulate Your Decision")
    
    if not preference_list:
        st.warning("Generate recommendations first.")
        return
    
    allotted_options = [f"{p.rank}. {p.college_name} - {p.branch_name}" for p in preference_list[:20]]
    
    current_allotment = st.selectbox(
        "If you get allotted to:",
        allotted_options,
        key="allotment_select"
    )
    
    current_round = st.radio(
        "In which round?",
        ["Round 1", "Round 2", "Round 3", "Round 4"],
        horizontal=True
    )
    
    if st.button("🤔 Get Advice"):
        # Get the selected preference position
        selected_idx = int(current_allotment.split(".")[0]) - 1
        selected_item = preference_list[selected_idx]
        
        # Generate advice
        if selected_idx == 0:
            st.success("🎉 **FREEZE** - You got your top choice! Accept and celebrate!")
        elif selected_idx < 5 and selected_item.probability > 0.7:
            st.info("""
                🤔 **Consider FREEZE** - This is a good option and you already got it.
                Better options have lower probability.
            """)
        elif current_round == "Round 4":
            st.warning("⚠️ **FREEZE** - This is the final CAP round. Accept your seat!")
        else:
            better_options = preference_list[:selected_idx]
            high_prob_better = [p for p in better_options if p.probability > 0.3]
            
            if high_prob_better:
                same_college = [p for p in high_prob_better 
                               if p.college_code == selected_item.college_code]
                
                if same_college:
                    st.info(f"""
                        🔄 **SLIDE** - You have {len(same_college)} better branch option(s) 
                        in the same college with reasonable chances.
                    """)
                else:
                    st.info(f"""
                        🎈 **FLOAT** - You have {len(high_prob_better)} better option(s) 
                        with >30% probability. Keep trying!
                    """)
            else:
                st.success("✅ **FREEZE** - Low probability of getting better options. Accept this seat.")


def render_acap_guidance():
    """Render ACAP/Institute-level round guidance"""
    st.markdown("### 🏫 ACAP (Institute-Level) Guidance")
    
    st.markdown("""
        After all CAP rounds, vacant seats are filled through **Institute-Level Rounds (ACAP)**.
        
        #### Key Points:
        
        1. **When does ACAP happen?**
           - Usually in October, after CAP Round IV
           - Multiple mini-rounds may be conducted
        
        2. **Who should consider ACAP?**
           - Students who didn't get any CAP allotment
           - Students who want to try for better options
           - Those interested in specific colleges not filled via CAP
        
        3. **Process:**
           - Check vacant seat lists on CET Cell website
           - Apply directly to institutes
           - First-come-first-served in many cases
           - Some colleges conduct their own merit-based selection
        
        4. **Tips:**
           - Government colleges rarely have ACAP vacancies
           - Focus on good private colleges with remaining seats
           - Some autonomous institutes have separate processes
           - Keep documents ready for immediate admission
        
        #### Current Year Vacant Seats
    """)
    
    st.info("📋 Check the official CET Cell website for the latest vacant seat list after CAP Round IV.")
    
    st.link_button(
        "🔗 View Official Vacant Seats List",
        "https://fe2025.mahacet.org/ViewPublicDocument.aspx?MenuId=5630",
        use_container_width=True
    )


def render_export_section(result):
    """Render export options"""
    st.markdown("### 📥 Export Your Preference List")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Download Excel", use_container_width=True):
            excel_buffer = export_to_excel(result)
            st.download_button(
                label="⬇️ Click to Download Excel",
                data=excel_buffer.getvalue(),
                file_name=f"mhtcet_preferences_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    
    with col2:
        if st.button("📄 Download PDF", use_container_width=True):
            pdf_buffer = export_to_pdf(result)
            st.download_button(
                label="⬇️ Click to Download PDF",
                data=pdf_buffer.getvalue(),
                file_name=f"mhtcet_preferences_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )


def main():
    """Main application entry point"""
    init_session_state()
    
    # Render header
    render_header()
    
    # Get profile from sidebar
    profile, cutoff_adjustment = render_sidebar()
    
    # Load data
    cutoff_data = load_cutoff_data()
    
    # Initialize engines
    prob_engine = ProbabilityEngine(cutoff_data)
    rec_engine = RecommendationEngine(prob_engine)
    
    # Generate button
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        generate_clicked = st.button(
            "🚀 Generate Recommendations",
            type="primary",
            use_container_width=True
        )
    
    if generate_clicked:
        with st.spinner("Analyzing historical data and generating recommendations..."):
            result = rec_engine.generate_recommendations(
                profile=profile,
                cutoff_adjustment=cutoff_adjustment,
                max_options=50
            )
            st.session_state.recommendations = result
            st.session_state.preference_list = result.preference_list
    
    # Display results if available
    if st.session_state.recommendations:
        result = st.session_state.recommendations
        
        st.markdown("---")
        
        # Display warnings
        for warning in result.warnings:
            st.warning(warning)
        
        # Display metrics
        render_metrics(result)
        
        st.markdown("---")
        
        # Tabs for different views
        tabs = st.tabs([
            "📋 Preference List",
            "🔄 What-If Simulator", 
            "🔮 Round Simulator",
            "🎯 Float/Freeze Advisor",
            "🏫 ACAP Guide",
            "📥 Export"
        ])
        
        with tabs[0]:
            st.markdown("### 📋 Your Optimized Preference List")
            st.markdown("""
                Your preferences are ordered as: **Dream → Target → Safe**
                
                🌟 **Dream** = Low probability, aspirational  
                ✅ **Target** = Realistic chances  
                🛡️ **Safe** = High probability backup
            """)
            render_preference_list(result.preference_list)
            
            # Strategy notes
            if result.strategy_notes:
                st.markdown("### 💡 Strategy Notes")
                for note in result.strategy_notes:
                    st.info(note)
        
        with tabs[1]:
            render_what_if_simulator(
                result.preference_list, 
                profile, 
                prob_engine
            )
        
        with tabs[2]:
            render_round_simulator(
                result.preference_list,
                profile,
                prob_engine
            )
        
        with tabs[3]:
            render_float_freeze_advisor(result.preference_list, profile)
        
        with tabs[4]:
            render_acap_guidance()
        
        with tabs[5]:
            render_export_section(result)
    
    else:
        # Show instructions
        st.markdown("---")
        st.markdown("""
            ### 📝 How to Use This Tool
            
            1. **Fill your profile** in the sidebar (percentile, category, quota, etc.)
            2. **Adjust cutoff expectations** if you think cutoffs will change from historical
            3. **Select branch preferences** to focus recommendations
            4. **Click "Generate Recommendations"** to get your optimized list
            5. **Explore tabs** for simulation, advice, and export options
            
            ---
            
            ### ⚠️ Important Notes
            
            - This tool uses **4 years of historical cutoff data** (2022-2025)
            - Recommendations are **predictions** based on past trends
            - Always verify with official **CET Cell** announcements
            - The system accounts for **category, quota, and special reservations**
            
            ---
            
            ### 📊 Data Source
            
            All cutoff data is sourced from the official 
            [MHT-CET State CET Cell](https://fe2025.mahacet.org/StaticPages/HomePage) website.
        """)
    
    # Footer
    st.markdown("---")
    st.markdown("""
        <div style="text-align: center; color: #888; font-size: 0.8rem;">
            <p>
                MHT-CET College Preference Advisor | Built with ❤️ for Maharashtra students<br>
                <strong>Disclaimer:</strong> This is a decision-support tool. 
                Verify all information with official CET Cell sources.
            </p>
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
