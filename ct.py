import argparse
import os
import PyPDF2
from docx import Document
from anthropic import Anthropic
import json
import re
from collections import defaultdict

apiK = 'your_anthropic_api_key_here'  # Update with your Anthropic API key

def extract_text_from_pdf(file_path):
    """Extract text from PDF resume"""
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = '\n'.join([page.extract_text() for page in reader.pages])
    return text

def extract_text_from_docx(file_path):
    """Extract text from DOCX resume"""
    doc = Document(file_path)
    return '\n'.join([para.text for para in doc.paragraphs])

def clean_resume_text(text):
    """Normalize whitespace and remove special characters"""
    text = re.sub(r'\s+', ' ', text)  # Collapse multiple whitespaces
    text = re.sub(r'[^\w\s\-.,!?]', '', text)  # Remove non-standard characters
    return text.strip()

def extract_skills_with_openai(text):
    """Use Claude API to extract skills and qualifications"""
    client = Anthropic(api_key=apiK)
    
    prompt = """Analyze this resume text and extract technical skills and qualifications in JSON format with these categories:
    - programming_languages (array)
    - frameworks (array)
    - tools (array)
    - certifications (array)
    - education (array of degrees)
    - experience_years (integer)
    
    Resume text: {text}
    
    Return ONLY valid JSON, no commentary. Use null for missing categories."""

    response = client.messages.create(
        model="claude-3-sonnet-20240229",
        system="You are a skilled resume parser. Extract and categorize technical information.",
        messages=[{
            "role": "user",
            "content": prompt.format(text=text[:3000])
        }],
        max_tokens=2000,
        temperature=0.1
    )
    
    try:
        return json.loads(response.content[0].text)
    except json.JSONDecodeError:
        return {"error": "Failed to parse Claude response"}

def compare_skills(resume_data, jd_data):
    """Compare resume skills with JD requirements using structured scoring"""
    client = Anthropic(api_key=apiK)
    
    scoring_rubric = """Technical Skills Match (0-35):
    - 30-35: All key skills present + 5+ bonus skills
    - 25-29: All key skills present + 1-4 bonus skills
    - 20-24: Missing 1 key skill but strong bonus skills
    - 15-19: Missing 2 key skills
    
    Experience Evaluation (0-30):
    - 25-30: Meets or exceeds required experience
    - 20-24: Close to requirement (≥75%)
    - 15-19: Some relevant experience (50-75%)
    - 10-14: Limited experience (<50%)
    
    Education/Certifications (0-25):
    - 20-25: All requirements met + relevant extras
    - 15-19: Meets basic requirements
    - 10-14: Partial requirements met
    - 5-9: Minimal relevant qualifications
    
    Overall Potential (0-10):
    - 9-10: Exceptional candidate
    - 7-8: Strong potential
    - 5-6: Average fit
    - 3-4: Below average"""
    
    prompt = f"""RESUME DATA:
    {json.dumps(resume_data, indent=2)}
    
    JOB DESCRIPTION REQUIREMENTS:
    {json.dumps(jd_data, indent=2)}
    
    {scoring_rubric}
    
    Return JSON with: breakdown (object with category scores), total_score (sum of scores), 
    match_strengths (array), improvement_areas (array), and hiring_recommendation (string)"""

    response = client.messages.create(
        model="claude-3-opus-20240229",
        system="Act as a senior technical recruiter with 15+ years experience.",
        messages=[{
            "role": "user",
            "content": prompt
        }],
        max_tokens=4000,
        temperature=0.0
    )
    
    try:
        raw_response = response.content[0].text
        parsed = json.loads(raw_response)
        parsed['model_processing'] = {
            'model': 'claude-3-opus',
            'response_raw': raw_response
        }
        return parsed
    except json.JSONDecodeError:
        return {
            "error": "Failed to parse analysis response",
            "raw_response": raw_response
        }

def analyze_resume(jd_requirements, resume_text):
    """End-to-end analysis pipeline"""
    cleaned_text = clean_resume_text(resume_text)
    resume_data = extract_skills_with_openai(cleaned_text)
    comparison = compare_skills(resume_data, jd_requirements)
    return comparison

def main():
    parser = argparse.ArgumentParser(description='Skills Comparator')
    parser.add_argument('resume_path', help='Path to PDF/DOCX resume file')
    parser.add_argument('job_description_path', help='Path to PDF/DOCX job description file')
    
    args = parser.parse_args()
    
    # Validate both files exist
    for path in [args.resume_path, args.job_description_path]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File {path} not found")

    def process_file(file_path):
        """Process either resume or JD file"""
        if file_path.lower().endswith('.pdf'):
            return extract_text_from_pdf(file_path)
        elif file_path.lower().endswith('.docx'):
            return extract_text_from_docx(file_path)
        raise ValueError("Unsupported file format")

    # Process both documents
    resume_text = process_file(args.resume_path)
    jd_text = process_file(args.job_description_path)

    # Extract skills from both documents
    resume_skills = extract_skills_with_openai(resume_text)
    jd_requirements = extract_skills_with_openai(jd_text)

    # Display results
    def display_results(data, title):
        print(f"\n{title}:")
        for category in ['technical_skills', 'qualifications', 'certifications']:
            if data.get(category):
                print(f"\n{category.replace('_', ' ').title()}:")
                print('\n'.join(f'- {item}' for item in data[category]))

    display_results(resume_skills, "RESUME SKILLS")
    display_results(jd_requirements, "JOB DESCRIPTION REQUIREMENTS")

    # Add comparison and scoring
    comparison = compare_skills(resume_skills, jd_requirements)
    
    print("\n\nMATCH ANALYSIS:")
    print(f"Overall Match Score: {comparison['overall_score']}%")
    
    # Updated score breakdown handling with safe access
    print("\nScore Breakdown:")
    if 'score_breakdown' in comparison:
        for category, score in comparison['score_breakdown'].items():
            print(f"- {category.replace('_', ' ').title()}: {score}%")
    else:
        print("- No score breakdown available")
    
    # Consolidated missing requirements
    if comparison['missing_requirements']:
        print("\nMISSING REQUIREMENTS:")
        print('\n'.join(f'- {item}' for item in comparison['missing_requirements']))
    else:
        print("\nALL REQUIREMENTS MET!")

    # Display matched requirements
    if comparison['matched_requirements']:
        print("\nMATCHED REQUIREMENTS:")
        print('\n'.join(f'- {item}' for item in comparison['matched_requirements']))

    # Add error checking before display
    if 'error' in comparison:
        print(f"\nERROR: {comparison['error']}")
        return

if __name__ == "__main__":
    main()