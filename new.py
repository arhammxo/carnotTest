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
              Normalize degree names, for example:
              - "B.Tech" -> "Bachelor's"
              - "B.Eng" -> "Bachelor's"
              - "BS" -> "Bachelor's"
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
    """Compare resume skills with JD requirements using LLM scoring"""
    client = OpenAI(api_key=apiK)
    
    scoring_rubric = """Scoring Criteria:
    1. Technical Skills (50% weight):
       - Award FULL category score if ANY skill matches the category
       - No partial deductions for multiple missing skills in same category
    2. Qualifications (30% weight):
       - Consider equivalent degrees (B.Tech = Bachelor's)
    3. Certifications (20% weight):
       - Only penalize for certifications EXPLICITLY required in JD
    4. Bonus:
       - Extra relevant skills: +2% whenever we have a relevant skill (max +10%)
    
    Required EXAMPLE Response Format:
    {
        "overall_score": 85.5,
        "score_breakdown": {
            "technical_skills": 45,
            "qualifications": 20,
            "certifications": 15,
            "bonuses": 5
        },
        "missing_requirements": [
            "Cloud Computing Certification",
            "5 years experience in AI"
        ],
        "matched_requirements": [
            "Python Programming",
            "Computer Science Degree"
        ]
    }
    """
    
    prompt = f"""Act as an expert HR manager with 10+ years experience in technical recruitment. 
    Analyze and compare these resume qualifications with job requirements:

    Key Analysis Requirements:
    1. Match SPECIFIC resume items to BROAD JD categories:
       - Programming Languages: Any specific language match
       - Cloud Computing: Any cloud platform experience
       - ML Frameworks: Framework-to-framework matches
       - DevOps: Toolchain compatibility
       - Data Technologies: Database/processing system matches
       - AI Domains: Domain-specific expertise
    2. Identify STRICT category matches - award category score only if:
       - Resume has at least one matching item in the category
       - Match must be direct or clearly equivalent
    3. Flag requirements as MISSING only when:
       - JD explicitly requires them AND
       - Resume shows no comparable equivalent
    4. Bonus points should be conservative:
       - Only award for directly relevant extra skills
       - Max +2% per relevant skill (cap at 10%)

    Resume Data:
    {json.dumps(resume_data, indent=2)}

    Job Description Requirements:
    {json.dumps(jd_data, indent=2)}

    {scoring_rubric}

    Required Response Format:
    {{
        "overall_score": [0-100 score with decimal precision],
        "score_breakdown": {{
            "technical_skills": [0-50],
            "qualifications": [0-30],
            "certifications": [0-20],
            "bonuses": [0-10]
        }},
        "missing_requirements": [
            "Specific missing JD requirements with reason"
        ],
        "matched_requirements": [
            "Specific matches between resume and JD"
        ]
    }}
    """
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{
            "role": "user",
            "content": prompt
        }],
        temperature=0.0
    )
    
    try:
        result = json.loads(response.choices[0].message.content)
        # Add default values for all expected keys
        result.setdefault('score_breakdown', {
            'technical_skills': 0,
            'qualifications': 0,
            'certifications': 0,
            'bonuses': 0
        })
        result.setdefault('missing_requirements', [])
        result.setdefault('matched_requirements', [])
        result['overall_score'] = min(max(float(result.get('overall_score', 0)), 0), 100)
        return result
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Error parsing response: {str(e)}")  # Add error logging
        print(f"Raw API response: {response.choices[0].message.content}")  # Log raw response
        return {
            "error": "Scoring failed",
            "overall_score": 0,
            "score_breakdown": {
                'technical_skills': 0,
                'qualifications': 0,
                'certifications': 0,
                'bonuses': 0
            },
            "missing_requirements": [],
            "matched_requirements": []
        }

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
