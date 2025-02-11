import argparse
import os
import PyPDF2
from docx import Document
from openai import OpenAI
import json
import re

apiK = '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'

def extract_text_from_pdf(file_stream):
    """Extract text from PDF resume using file stream"""
    reader = PyPDF2.PdfReader(file_stream)
    return '\n'.join([page.extract_text() for page in reader.pages])

def extract_text_from_docx(file_stream):
    """Extract text from DOCX resume using file bytes"""
    doc = Document(file_stream)
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
    """Compare resume skills with JD requirements using structured scoring"""
    client = OpenAI(api_key=apiK)
    
    scoring_rubric = """Scoring Methodology:
    1. Technical Skills Analysis (50% base weight):
       - Calculate skill coverage ratio: (resume_skills_matched / jd_skills_required)
       - Base score = (matched_skills_count / required_skills_count) * base_weight
       - If certifications not required, use adjusted_weight = base_weight + 10
       - Handle zero division: If JD requires 0 skills, full base weight awarded
    
    2. Qualifications Evaluation (30% base weight):
       - Degree Level Match (20%):
         * Full 20% if resume meets/exceeds JD's required degree level
         * 10% if one level below JD requirement (e.g. JD requires Master's - resume has Bachelor's)
         * 0% if two+ levels below
       - Field Relevance (10%):
         * 10% if exact field match with JD requirements
         * 5% if related field (e.g. Computer Engineering vs Computer Science)
         * 0% for unrelated fields
       - Only apply these scores if candidate has at least the minimum required degree type
       - Complete mismatch (e.g. JD requires CS degree - resume has unrelated degree) = 0% overall
    
    3. Certification Verification (20% conditional):
       - ONLY APPLY IF JD REQUIRES SPECIFIC CERTS
       - If no certs required in JD, redistribute:
         - Technical Skills: +10% (total 60%)
         - Qualifications: +10% (total 40%)
       - Required certs: 15%
       - Bonus certs: 5%
    
    4. Experience Bonus (0-10%):
       - +2% per year over JD's minimum requirement
       - Max +10%"""
    
    prompt = f"""Act as a senior technical recruiter with 15+ years experience. Conduct a rigorous, 
    quantitative analysis following these steps:

    1. Skill Category Analysis:
    - Map resume skills to these JD categories:
      [Programming, Cloud, ML, DevOps, Data, AI]
    - Compare specificity levels (e.g., "Python" vs "Programming Languages")
    - Award category credit for any direct/implied match

    2. Qualifications Assessment:
    - Evaluate degree LEVEL (PhD/Masters/Bachelors) against JD requirements
    - Analyze degree FIELD relevance (CS vs IT vs unrelated)
    - Consider course projects/thesis topics for field relevance

    3. Certification Verification:
    - Match exact cert names where required
    - Accept equivalent certs (AWS vs Azure vs GCP)
    - Award partial credit for in-progress certifications

    4. Experience Scoring:
    - Compare years of experience in key areas
    - Verify project depth and complexity
    - Award bonus for leadership experience

    Resume Data:
    {json.dumps(resume_data, indent=2)}

    Job Description Requirements:
    {json.dumps(jd_data, indent=2)}

    {scoring_rubric}

    Final Response Format:
    {{
        "certifications_required": [true/false],
        "overall_score": [0-100 score with one decimal],
        "score_breakdown": {{
            "technical_skills": [0-50/60],
            "qualifications": [0-30/40],
            "certifications": [0-20],
            "bonuses": [0-10]
        }},
        "missing_requirements": ["list specific gaps with JD requirements"],
        "matched_requirements": ["list specific matches with evidence"]
    }}"""
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": prompt
        }],
        temperature=0.0
    )
    
    try:
        # Extract JSON from markdown response
        raw_response = response.choices[0].message.content
        json_str = re.search(r'```json\n(.*?)\n```', raw_response, re.DOTALL).group(1)
        
        result = json.loads(json_str)
        # Add validation for numerical values
        for key in ['technical_skills', 'qualifications', 'certifications', 'bonuses']:
            result['score_breakdown'][key] = float(result['score_breakdown'].get(key, 0))
        
        result['overall_score'] = min(max(float(result.get('overall_score', 0)), 0), 100)
        return result
    except (json.JSONDecodeError, KeyError, ValueError, AttributeError) as e:
        print(f"Error parsing response: {str(e)}")
        print(f"Raw API response: {raw_response}")  # Show actual problematic response
        return {
            "error": f"Scoring failed: {str(e)}",
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

def generate_score_explanation(resume_data, jd_data, comparison_result):
    """Generate natural language explanation of scoring results using LLM"""
    client = OpenAI(api_key=apiK)
    
    prompt = f"""Act as a senior technical recruiter. Analyze this candidate evaluation and provide a detailed, 
    professional explanation of the scoring results. Follow these guidelines:
    1. Remember the exact scoring breakdown and comparison context from the analysis
    2. Cross-reference specific requirements from the JD with resume details
    3. Explain technical skill adjacencies that could compensate for gaps
    4. Highlight patterns in qualifications/certifications
    5. Maintain professional tone but add contextual insights
    
    Resume Summary:
    {json.dumps(resume_data, indent=2)}
    
    Job Description Requirements:
    {json.dumps(jd_data, indent=2)}
    
    Scoring Results:
    {json.dumps(comparison_result, indent=2)}
    
    Structure your response with these sections (use markdown):
    ## Overall Assessment
    - Start with score interpretation
    - Key comparative strengths/weaknesses
    - High-level match summary
    
    ## Technical Competency Analysis
    - Skill category comparisons with JD requirements
    - Notable matches/mismatches with specific examples
    - Contextual analysis of skill depth
    
    ## Qualifications Evaluation 
    - Degree level/field alignment analysis
    - Coursework/project relevance to JD
    - Gap impact assessment
    
    ## Certification Alignment
    - Direct/indirect certification matches
    - Weight of missing certs in context
    - Equivalent certifications analysis
    
    ## Experience Relevance
    - Years experience vs requirements
    - Project complexity comparison
    - Leadership experience evaluation
    
    ## Final Recommendation
    - Strong/Moderate/Weak fit conclusion *REFER TO THE SCORING RESULTS FOR THE CONCLUSION*
    - Hiring consideration with context
    - Suggested next steps"""
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": prompt
        }],
        temperature=0.3
    )
    
    return response.choices[0].message.content

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

    # Store explanation
    score_explanation = generate_score_explanation(resume_skills, jd_requirements, comparison)
    
    # Add explanation output
    print("\nSCORE EXPLANATION:")
    print(score_explanation)

if __name__ == "__main__":
    main()