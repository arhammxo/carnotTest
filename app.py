import streamlit as st
from finalFIX import extract_text_from_pdf, extract_text_from_docx, extract_skills_with_openai, compare_skills

# Set page config
st.set_page_config(page_title="Resume Analyzer", layout="wide")

# API key handling (update with your Streamlit secrets management)
apiK = st.secrets['openai']['api_key']  # Corrected key path

# File upload section
st.header("Upload Documents")
col1, col2 = st.columns(2)
with col1:
    resume_file = st.file_uploader("Upload Resume", type=["pdf", "docx"])
with col2:
    jd_file = st.file_uploader("Upload Job Description", type=["pdf", "docx"])

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
        
        with st.container():
            st.subheader(title)
            
            # Technical Skills Section
            cols = st.columns(3)
            with cols[0]:
                st.markdown("### 📚 Technical Skills")
                if skills_data.get('technical_skills'):
                    for skill in skills_data['technical_skills']:
                        st.markdown(f"- {skill}")
                else:
                    st.markdown("*No technical skills detected*")
            
            # Qualifications Section
            with cols[1]:
                st.markdown("### 🎓 Qualifications")
                if skills_data.get('qualifications'):
                    for qual in skills_data['qualifications']:
                        st.markdown(f"- {qual}")
                else:
                    st.markdown("*No qualifications detected*")
            
            # Certifications Section
            with cols[2]:
                st.markdown("### 📜 Certifications")
                if skills_data.get('certifications'):
                    for cert in skills_data['certifications']:
                        st.markdown(f"- {cert}")
                else:
                    st.markdown("*No certifications detected*")

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
                st.markdown(f'<div class="big-score" style="color:{score_color}">{score:.1f}%</div>', 
                          unsafe_allow_html=True)
                st.progress(score/100, text=f"Position Fit: {score_color.capitalize()} Zone")
            
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
                # Determine certification requirements from JD analysis
                certs_required = comparison.get('certifications_required', False)
                
                # Adjust max weights based on certification requirements
                max_weights = {
                    'technical_skills': 60 if not certs_required else 50,
                    'qualifications': 40 if not certs_required else 30,
                    'certifications': 20,
                    'bonuses': 10
                }

                # Create columns based on certification presence
                num_cols = 3 if not certs_required else 4
                cols = st.columns(num_cols)
                
                for i, (category, score) in enumerate(comparison['score_breakdown'].items()):
                    # Skip certifications if not required
                    if not certs_required and category == 'certifications':
                        continue
                    
                    max_weight = max_weights.get(category, 100)
                    normalized_score = (score / max_weight) * 100 if max_weight > 0 else 0
                    
                    # Custom icons and labels
                    category_info = {
                        'technical_skills': {"icon": "💻", "label": "Technical Skills"},
                        'qualifications': {"icon": "🎓", "label": "Qualifications"},
                        'certifications': {"icon": "📜", "label": "Certifications"},
                        'bonuses': {"icon": "⭐", "label": "Bonuses"}
                    }
                    
                    with cols[i%num_cols]:
                        st.metric(
                            label=f"{category_info[category]['icon']} {category_info[category]['label']}",
                            value=f"{normalized_score:.1f}%",
                            help=f"Weighted contribution: {max_weight}% of total score"
                        )

        # Requirements analysis with visual indicators
        if comparison.get('missing_requirements'):
            with st.container(border=True):
                st.subheader("❌ Missing Requirements", divider="red")
                st.caption("These key requirements from the JD are not fully met:")
                for item in comparison['missing_requirements']:
                    st.markdown(f"🔴 {item}")

        if comparison.get('matched_requirements'):
            with st.container(border=True):
                st.subheader("✅ Matched Requirements", divider="green")
                st.caption("These JD requirements are strongly matched:")
                cols = st.columns(2)
                for i, item in enumerate(comparison['matched_requirements']):
                    cols[i%2].markdown(f"🟢 {item}")

        if 'error' in comparison:
            st.error(f"🚨 Analysis error: {comparison['error']}", icon="⚠️") 