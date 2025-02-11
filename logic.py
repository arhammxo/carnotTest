import argparse
import os
from docx import Document
from openai import OpenAI
import json
import re
import streamlit as st 
import fitz  # PyMuPDF
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

apiK = st.secrets['openai']['api_key'] 

# RAG Configuration
SKILL_KNOWLEDGE_BASE = [
    "Standardized skill taxonomies (e.g., NIST NICE Framework, ESCO)",
    "Common certification requirements by industry",
    "Degree equivalency frameworks (Bologna Process, ABET standards)",
    "Emerging technology skill definitions",
    "Industry-specific competency models"
]

def create_skill_vector_store():
    """Create vector store for skill knowledge base"""
    embeddings = OpenAIEmbeddings(api_key=apiK)
    return Chroma.from_texts(
        texts=SKILL_KNOWLEDGE_BASE,
        embedding=embeddings,
        collection_metadata={"hnsw:space": "cosine"},
        persist_directory=None  # Disable persistent storage
    )

def retrieve_rag_context(query: str, vector_store, k=3):
    """Retrieve relevant context from knowledge base"""
    results = vector_store.similarity_search(query, k=k)
    return "\n".join([doc.page_content for doc in results])

def extract_text_from_pdf(file_stream):
    """Extract text from PDF resume using file stream"""
    doc = fitz.open(stream=file_stream.read(), filetype="pdf")
    return '\n'.join([page.get_text() for page in doc])

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
              
              Required technical categories:
              - AI Domains: Explicitly list Computer Vision, NLP, or Generative AI when mentioned
              - Hackathon Experience: Include any competition participation
              - Technical Projects: List projects indicating NLP usage
              
              Normalization rules:
              - "Hackathon Winner" -> "Hackathon Experience"
              - Projects using chatbots/OCR/text-processing -> "Natural Language Processing"
              - Research internships -> "Published Research"
              - GitHub portfolio -> "Open-source Contributions"
              
              Special handling:
              - Convert "B.Tech" to "Bachelor's"
              - Treat hackathon wins as qualifications
              - Map project descriptions to technical skills"""
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user", 
            "content": prompt.format(text=text[:10000])
        }],
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    
    try:
        raw_response = response.choices[0].message.content
        json_str = re.search(r'```json\n(.*?)\n```', raw_response, re.DOTALL)
        if json_str:
            return json.loads(json_str.group(1))
        return json.loads(raw_response)
    except Exception as e:
        print(f"Error parsing response: {str(e)}")
        print(f"Raw API response: {raw_response}")
        return {
            "error": "Failed to parse OpenAI response",
            "details": str(e),
            "raw_response": raw_response
        }

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
       - Max +10%
       
    Add these matching rules:
    1. NLP Recognition:
       - Accept projects using: chatbots, text processing, OCR, speech systems
       - Count LLM implementations as NLP experience
       
    2. Hackathon Validation:
       - Consider competition wins as hackathon experience
       - Treat school-level competitions as valid
       
    3. Research Recognition:
       - Count research internships as published research
       - Accept technical reports as research equivalents"""
    
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

    5. Contextual Skill Mapping:
       - Check project descriptions for implied skills
       - Match 'conversational chatbot' -> NLP
       - Map 'Smart India Hackathon Winner' -> Hackathon Experience
       - Interpret 'research internship' -> Published Research
       
    6. GitHub Validation:
       - Consider GitHub portfolio as open-source contribution
       - Count organizational projects as open-source

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
        "matched_requirements": ["list specific matches with evidence"],
        "strength_analysis": ["list of 3 key strengths"],
        "improvement_areas": ["list of 3 key gaps"],
        "hiring_recommendation": "concise hiring verdict",
        "next_steps": ["3 actionable next steps"]
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
        raw_response = response.choices[0].message.content
        json_str = re.search(r'```json\n(.*?)\n```', raw_response, re.DOTALL).group(1)
        
        result = json.loads(json_str)
        for key in ['technical_skills', 'qualifications', 'certifications', 'bonuses']:
            result['score_breakdown'][key] = float(result['score_breakdown'].get(key, 0))
        
        result['overall_score'] = min(max(float(result.get('overall_score', 0)), 0), 100)
        return result
    except (json.JSONDecodeError, KeyError, ValueError, AttributeError) as e:
        print(f"Error parsing response: {str(e)}")
        print(f"Raw API response: {raw_response}")
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
            "matched_requirements": [],
            "strength_analysis": [],
            "improvement_areas": [],
            "hiring_recommendation": "",
            "next_steps": []
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
    
    for path in [args.resume_path, args.job_description_path]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File {path} not found")

    def process_file(file_path):
        if file_path.lower().endswith('.pdf'):
            return extract_text_from_pdf(open(file_path, 'rb'))
        elif file_path.lower().endswith('.docx'):
            return extract_text_from_docx(open(file_path, 'rb'))
        raise ValueError("Unsupported file format")

    resume_text = process_file(args.resume_path)
    jd_text = process_file(args.job_description_path)

    resume_skills = extract_skills_with_openai(resume_text)
    jd_requirements = extract_skills_with_openai(jd_text)

    def display_results(data, title):
        print(f"\n{title}:")
        for category in ['technical_skills', 'qualifications', 'certifications']:
            if data.get(category):
                print(f"\n{category.replace('_', ' ').title()}:")
                print('\n'.join(f'- {item}' for item in data[category]))

    display_results(resume_skills, "RESUME SKILLS")
    display_results(jd_requirements, "JOB DESCRIPTION REQUIREMENTS")

    comparison = compare_skills(resume_skills, jd_requirements)
    
    print("\n\nMATCH ANALYSIS:")
    print(f"Overall Match Score: {comparison['overall_score']}%")
    
    print("\nScore Breakdown:")
    if 'score_breakdown' in comparison:
        for category, score in comparison['score_breakdown'].items():
            print(f"- {category.replace('_', ' ').title()}: {score}%")
    
    if comparison['missing_requirements']:
        print("\nMISSING REQUIREMENTS:")
        print('\n'.join(f'- {item}' for item in comparison['missing_requirements']))

    if comparison['matched_requirements']:
        print("\nMATCHED REQUIREMENTS:")
        print('\n'.join(f'- {item}' for item in comparison['matched_requirements']))

    score_explanation = generate_score_explanation(resume_skills, jd_requirements, comparison)
    print("\nSCORE EXPLANATION:")
    print(score_explanation)

if __name__ == "__main__":
    main()