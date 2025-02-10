import argparse
import os
import PyPDF2
from docx import Document
from openai import OpenAI
import json

apiK = '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'

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

def extract_skills_with_openai(text):
    """Use OpenAI API to extract skills and qualifications"""
    client = OpenAI(api_key=apiK)
    
    prompt = """Analyze this resume text and extract technical skills, qualifications,
              and certifications. Generalize terms to broader categories (e.g., 
              "Python" -> "Programming Languages", "AWS" -> "Cloud Computing").
              Return JSON format with:
              - technical_skills: array of generalized technical capabilities
              - qualifications: array of educational/professional qualifications
              - certifications: array of professional certifications
              Resume text: {text}
              Required categories:
              - Programming Languages (Python, Java, etc)
              - Cloud Computing (AWS, Azure, etc)
              - ML Frameworks (TensorFlow, PyTorch, etc)
              - DevOps (Docker, Kubernetes, CI/CD)
              - Data Technologies (SQL, Spark, etc)
              - AI Domains (Computer Vision, NLP, etc)
              ..."""
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{
            "role": "user",
            "content": prompt.format(text=text[:3000])
        }],
        temperature=0.1  # Lower temperature for more consistent outputs
    )
    
    try:
        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        return {"error": "Failed to parse OpenAI response"}

def compare_skills(resume_data, jd_data):
    """Compare resume skills with JD requirements and calculate match score"""
    scores = {}
    total_score = 0
    comparable_categories = 0
    
    for category in ['technical_skills', 'qualifications', 'certifications']:
        # Handle qualifications differently
        if category == 'qualifications':
            # Extract keywords from both qualifications
            jd_keywords = set()
            for q in jd_data.get(category, []):
                jd_keywords.update(q.lower().split())
                
            resume_keywords = set()
            for q in resume_data.get(category, []):
                resume_keywords.update(q.lower().split())
                
            matching = jd_keywords & resume_keywords
            match_percent = (len(matching) / len(jd_keywords)) * 100 if jd_keywords else 0
            
        else:
            resume_items = set(resume_data.get(category, []))
            jd_items = set(jd_data.get(category, []))
            
            # Skip categories not present in JD requirements
            if not jd_items:
                continue
            
            matching = resume_items.intersection(jd_items)
            match_percent = (len(matching) / len(jd_items)) * 100
            scores[category] = {
                'match_percent': round(match_percent, 1),
                'matched': list(matching),
                'missing': list(jd_items - matching)
            }
            total_score += match_percent
            comparable_categories += 1
    
    # Modified scoring calculation
    total_jd_items = sum(len(jd_data.get(cat, [])) for cat in ['technical_skills', 'qualifications', 'certifications'])
    total_matched = sum(len(details['matched']) for details in scores.values())
    
    overall_score = round((total_matched / total_jd_items) * 100, 1) if total_jd_items else 0
    return {'overall_score': overall_score, 'category_scores': scores}

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
    
    # Collect all missing items across categories
    all_missing = []
    
    for category, details in comparison['category_scores'].items():
        print(f"\n{category.replace('_', ' ').title()}:")
        print(f"Match: {details['match_percent']}%")
        print("Matched Items:")
        print('\n'.join(f'- {item}' for item in details['matched']))
        if details['missing']:
            print("Missing Items:")
            print('\n'.join(f'- {item}' for item in details['missing']))
            all_missing.extend(details['missing'])
    
    # Add consolidated missing fields section
    if all_missing:
        print("\n\nTOTAL MISSING REQUIREMENTS:")
        print('\n'.join(f'- {item}' for item in all_missing))
    else:
        print("\n\nALL REQUIREMENTS MET!")

if __name__ == "__main__":
    main()
