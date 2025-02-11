import streamlit as st
from logic import extract_text_from_pdf, extract_text_from_docx, extract_skills_with_openai, compare_skills, generate_score_explanation

# Set page config
st.set_page_config(page_title="Resume Analyzer", layout="wide")

# API key handling (update with your Streamlit secrets management)
apiK = st.secrets['openai']['api_key']  # Corrected key path

# File upload section - Add visual feedback
st.header("📁 Upload Documents", divider="rainbow")
col1, col2 = st.columns(2)
with col1:
    resume_file = st.file_uploader("Upload Resume (PDF/DOCX)", type=["pdf", "docx"], 
                                 help="Max file size: 5MB")
with col2:
    jd_file = st.file_uploader("Upload Job Description (PDF/DOCX)", type=["pdf", "docx"],
                             help="Supported formats: PDF, Word documents")

def process_uploaded_file(file):
    """Handle uploaded file processing"""
    if file is None:
        return None
    try:
        if file.name.lower().endswith('.pdf'):
            # Pass the file buffer directly
            return extract_text_from_pdf(file)
        elif file.name.lower().endswith('.docx'):
            # Read bytes for DOCX processing
            return extract_text_from_docx(file.getvalue())
        else:
            st.error(f"Unsupported file type: {file.name}")
            return None
            
        if not text.strip():
            st.error(f"Empty content in file: {file.name}")
            return None
            
        return text
    except Exception as e:
        st.error(f"Error processing {file.name}: {str(e)}")
        return None

if resume_file and jd_file:
    # Process documents
    with st.spinner("Analyzing documents..."):
        resume_text = process_uploaded_file(resume_file)
        jd_text = process_uploaded_file(jd_file)
        
        # Add null checks before processing
        if resume_text is None or jd_text is None:
            st.error("Failed to extract text from one or more files. Please check the file formats.")
            st.stop()  # Prevent further execution
        
        # Extract skills
        try:
            resume_skills = extract_skills_with_openai(resume_text)
            jd_requirements = extract_skills_with_openai(jd_text)
        except Exception as e:
            st.error(f"Error analyzing documents: {str(e)}")
            st.stop()
        
    # Display extracted skills
    st.header("Extracted Requirements")
    tab1, tab2 = st.tabs(["Resume Skills", "Job Description Requirements"])
    
    def display_skills(skills_data, title):
        """Display skills data in a visual format"""
        if 'error' in skills_data:
            st.error(skills_data['error'])
            return
        
        with st.container(border=True):
            st.subheader(f"🔍 {title}")
            
            # Technical Skills Section
            with st.expander("📚 Technical Skills", expanded=True):
                if skills_data.get('technical_skills'):
                    cols = st.columns(3)
                    for i, skill in enumerate(skills_data['technical_skills']):
                        cols[i%3].success(f"• {skill}")
                else:
                    st.warning("No technical skills detected", icon="⚠️")
            
            # Qualifications Section
            with st.expander("🎓 Education & Qualifications", expanded=True):
                if skills_data.get('qualifications'):
                    for qual in skills_data['qualifications']:
                        st.markdown(f"📌 {qual}")
                else:
                    st.warning("No qualifications detected", icon="⚠️")
            
            # Certifications Section
            with st.expander("📜 Certifications", expanded=True):
                if skills_data.get('certifications'):
                    cols = st.columns(2)
                    for i, cert in enumerate(skills_data['certifications']):
                        cols[i%2].markdown(f"🏅 {cert}")
                else:
                    st.warning("No certifications detected", icon="⚠️")

    with tab1:
        display_skills(resume_skills, "Candidate Skills Overview")

    with tab2:
        display_skills(jd_requirements, "Job Requirements Breakdown")
    
    # Run comparison
    if st.button("Run Comparison"):
        with st.spinner("Calculating match..."):
            comparison = compare_skills(resume_skills, jd_requirements)
        
        st.header("Match Analysis", divider="rainbow")
        
        # Main Score Card - Full Width
        with st.container(border=True):
            st.markdown("""
            <style>
            .big-score {
                font-size: 72px !important;
                font-weight: bold;
                text-align: center;
                margin: 20px 0;
            }
            </style>
            """, unsafe_allow_html=True)
            
            score = comparison.get('overall_score', 0)
            score_color = "red" if score < 50 else "orange" if score < 75 else "green"
            
            # Split into two columns for better layout
            main_col, help_col = st.columns([3, 2])
            with main_col:
                st.markdown(f"""
                <div style="text-align:center; padding:20px; background:linear-gradient(145deg, #f0f2f6, #ffffff);
                            border-radius:15px; box-shadow:0 4px 6px rgba(0,0,0,0.1)">
                    <div style="font-size:24px; color:#666; margin-bottom:10px">Match Score</div>
                    <div class="big-score" style="color:{score_color}">{score:.1f}%</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Add styled text above the progress bar
                st.markdown(f"""
                    <div style='font-weight:900; font-size:24px; margin-top:25px; margin-bottom:10px; text-align:center'>
                        {'🚀 IDEAL CANDIDATE' if score >= 90 else '📈 STRONG MATCH' if score >= 75 else '🤝 POTENTIAL CANDIDATE' if score >= 50 else '⚠️ SIGNIFICANT GAPS'}
                    </div>
                """, unsafe_allow_html=True)
                
                # Progress bar without text parameter
                st.progress(score/100)
            
            with help_col:
                st.subheader("📊 Interpretation Guide")
                st.markdown("""
                - **90-100%**: Ideal candidate 🏆
                - **75-89%**: Strong match 💪
                - **50-74%**: Potential candidate 🤝
                - **<50%**: Significant gaps ❌
                """)

        # Dynamic Score Breakdown
        with st.expander("🧮 Detailed Score Composition", expanded=True):
            if 'score_breakdown' in comparison:
                certs_required = comparison.get('certifications_required', False)
                
                max_weights = {
                    'technical_skills': 60 if not certs_required else 50,
                    'qualifications': 40 if not certs_required else 30,
                    'certifications': 20,
                    'bonuses': 10
                }

                # Create equal columns with proper spacing
                cols = st.columns(4 if certs_required else 3, gap="large")
                
                # Add custom styling for centering
                st.markdown("""
                <style>
                    .metric-container {
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        padding: 15px;
                        border-radius: 10px;
                        background-color: rgba(255,255,255,0.1);
                    }
                    .metric-label {
                        text-align: center !important;
                        margin-bottom: 8px !important;
                    }
                </style>
                """, unsafe_allow_html=True)

                for i, (category, score) in enumerate(comparison['score_breakdown'].items()):
                    if not certs_required and category == 'certifications':
                        continue
                    
                    max_weight = max_weights.get(category, 100)
                    normalized_score = (score / max_weight) * 100 if max_weight > 0 else 0
                    
                    category_info = {
                        'technical_skills': {"icon": "💻", "label": "Technical Skills"},
                        'qualifications': {"icon": "🎓", "label": "Qualifications"},
                        'certifications': {"icon": "📜", "label": "Certifications"},
                        'bonuses': {"icon": "⭐", "label": "Bonuses"}
                    }
                    
                    # Calculate column index based on certification presence
                    col_idx = i if certs_required else i if i < 3 else i-1
                    with cols[col_idx]:
                        st.markdown(f"""
                        <div class="metric-container">
                            <div class="metric-label">
                                {category_info[category]['icon']} {category_info[category]['label']}
                            </div>
                            <div style="font-size: 26px; font-weight: bold; margin: 8px 0;">
                                {normalized_score:.1f}%
                            </div>
                            <div style="font-size: 12px; color: #666; text-align: center">
                                Weight: {max_weight}%
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

        # Requirements analysis with visual indicators
        if comparison.get('missing_requirements'):
            with st.container(border=True):
                st.subheader("🔍 Gap Analysis", divider="red")
                cols = st.columns(2)
                with cols[0]:
                    st.markdown("### ❌ Missing Requirements")
                    st.caption("These key requirements from the JD are not fully met:")
                    for item in comparison['missing_requirements']:
                        st.error(f"• {item}", icon="🚫")
                with cols[1]:
                    if comparison.get('recommendations'):
                        st.markdown("### 💡 Improvement Suggestions")
                        for suggestion in comparison['recommendations']:
                            st.info(f"✨ {suggestion}")

        if comparison.get('matched_requirements'):
            with st.container(border=True):
                st.subheader("✅ Strengths & Matches", divider="green")
                st.caption("These JD requirements are strongly matched:")
                for item in comparison['matched_requirements']:
                    # Use a container with columns for better alignment
                    with st.container():
                        cols = st.columns([1, 15])  # Adjusted column ratio
                        with cols[0]:
                            st.success("✔️", icon="✅")
                        with cols[1]:
                            st.markdown(f"""
                            <div style="position: relative; top: -2px;">
                                <b>{item}</b><br>
                                <span style="color: #666; font-size: 0.9em">Perfect match with candidate profile</span>
                            </div>
                            """, unsafe_allow_html=True)

        if 'error' in comparison:
            st.error(f"🚨 Analysis error: {comparison['error']}", icon="⚠️")

        # Add explanation section
        with st.expander("📈 AI-Powered Match Breakdown", expanded=True):
            with st.spinner("Generating detailed analysis..."):
                # Generate explanation after displaying other results
                score_explanation = generate_score_explanation(resume_skills, jd_requirements, comparison)

                # Split explanation into sections 
                sections = score_explanation.split('## ')
                st.markdown("""
                    <style>
                    .analysis-header {
                        background: var(--secondary-background-color);
                        padding: 20px;
                        border-radius: 15px;
                        margin-bottom: 20px;
                    }
                    </style>
                    
                    <div class="analysis-header">
                        <h2 style="margin:0;">🔍 AI-Powered Deep Analysis</h2>
                        <p style="margin:0; color: var(--text-color)">Comprehensive breakdown of candidate suitability</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Combined card container with bottom margin
                with st.container(border=True):
                    cols = st.columns(2)
                    with cols[0]:
                        st.markdown("### 🎯 Key Strengths")
                        # Dynamic strengths from comparison results
                        if comparison.get('matched_requirements'):
                            for item in comparison['matched_requirements'][:3]:  # Top 3 matches
                                st.success(f"✅ {item}")
                        else:
                            st.warning("No strong matches found", icon="⚠️")
                            
                        st.markdown("### 📉 Improvement Areas")
                        # Dynamic gaps from comparison results
                        if comparison.get('missing_requirements'):
                            for item in comparison['missing_requirements'][:3]:  # Top 3 gaps
                                st.error(f"⚠️ {item}")
                        else:
                            st.success("All key requirements met!", icon="🎉")

                    with cols[1]:
                        st.markdown("### 🏆 Recommendation")
                        # Dynamic recommendation based on score
                        score = comparison.get('overall_score', 0)
                        if score >= 90:
                            rec_text = "🥇 Gold Tier Candidate - Ideal Hire"
                            rec_details = "Strongly recommend for senior roles with leadership potential"
                        elif score >= 75:
                            rec_text = "🥈 Silver Tier Candidate - Strong Match" 
                            rec_details = "Recommend for mid-level roles with growth opportunities"
                        elif score >= 50:
                            rec_text = "🥉 Bronze Tier Candidate - Potential Fit"
                            rec_details = "Consider for junior roles with mentorship"
                        else:
                            rec_text = "🚫 Not Recommended - Significant Gaps"
                            rec_details = "Doesn't meet minimum requirements"
                            
                        st.markdown(f"""
                        <div style="margin-bottom: 20px;">
                            <div style="font-size:18px; font-weight:bold;">
                                {rec_text}
                            </div>
                            <p style="margin:0; line-height:1.5;">
                            {rec_details}<br>
                            Score: {score:.1f}%
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                            
                        st.markdown("### 📅 Next Steps")
                        # Dynamic next steps based on score
                        steps = []
                        if score >= 75:
                            steps = [
                                "Schedule final interview with tech lead",
                                "Request reference checks",
                                "Prepare offer letter"
                            ]
                        elif score >= 50:
                            steps = [
                                "Conduct technical screening",
                                "Review portfolio projects",
                                "Schedule team interview"
                            ]
                        else:
                            steps = [
                                "Consider alternative candidates",
                                "Provide constructive feedback",
                                "Encourage re-application after upskilling"
                            ]
                        
                        st.markdown("""
                        <div style="margin-bottom: 20px;">
                        • {}<br>
                        • {}<br>
                        • {}
                        </div>
                        """.format(*steps), unsafe_allow_html=True)
                st.divider()
                with st.container(border=False):
                    st.markdown("### 📝 Detailed Assessment")
                    # Split explanation into sections and format properly
                    sections = score_explanation.split('## ')
                    for section in sections:
                        if section.strip():
                            parts = section.split('\n', 1)
                            if len(parts) > 1:
                                st.subheader(parts[0])
                                st.write(parts[1])
                            else:
                                st.write(section)
                    

        if 'error' in comparison:
            st.error(f"🚨 Analysis error: {comparison['error']}", icon="⚠️") 