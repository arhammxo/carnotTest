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
        
        st.header("Match Analysis")
        
        # Score display
        col1, col2 = st.columns([1, 3])
        with col1:
            st.metric("Overall Match Score", f"{comparison.get('overall_score', 0):.1f}%")
            
        with col2:
            if 'score_breakdown' in comparison:
                st.subheader("Score Breakdown")
                cols = st.columns(4)
                for i, (category, score) in enumerate(comparison['score_breakdown'].items()):
                    cols[i%4].metric(category.title(), f"{score}%")
        
        # Requirements analysis
        if comparison.get('missing_requirements'):
            with st.expander("Missing Requirements", expanded=True):
                st.write("\n".join(f"- {item}" for item in comparison['missing_requirements']))
        
        if comparison.get('matched_requirements'):
            with st.expander("Matched Requirements", expanded=False):
                st.write("\n".join(f"- {item}" for item in comparison['matched_requirements']))
        
        if 'error' in comparison:
            st.error(f"Analysis error: {comparison['error']}") 