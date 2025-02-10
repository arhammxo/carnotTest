import re
import pdfplumber
from openai import OpenAI
import os
from typing import List, Set
import json
import time
from collections import Counter

# Initialize OpenAI client
client = OpenAI(api_key='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')

# Comprehensive set of known skills for validation
KNOWN_SKILLS = {
    # Programming Languages
    'python', 'java', 'javascript', 'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin', 'go',
    'rust', 'typescript', 'scala', 'r', 'matlab', 'perl', 'haskell', 'lua', 'dart',
    
    # Web Technologies
    'html', 'css', 'react', 'angular', 'vue.js', 'node.js', 'django', 'flask',
    'spring boot', 'asp.net', 'express.js', 'jquery', 'bootstrap', 'tailwind css',
    'webpack', 'sass', 'less', 'graphql', 'rest api', 'soap',
    
    # Databases
    'sql', 'mysql', 'postgresql', 'mongodb', 'oracle', 'sqlite', 'redis', 'cassandra',
    'elasticsearch', 'dynamodb', 'mariadb', 'neo4j', 'couchbase', 'firebase',
    
    # Cloud Platforms
    'aws', 'azure', 'google cloud', 'heroku', 'digitalocean', 'kubernetes', 'docker',
    'terraform', 'jenkins', 'gitlab ci', 'github actions', 'circleci',
    
    # AI/ML
    'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'keras', 'scikit-learn',
    'pandas', 'numpy', 'opencv', 'nltk', 'spacy', 'computer vision', 'nlp',
    
    # Big Data
    'hadoop', 'spark', 'kafka', 'hive', 'pig', 'storm', 'flink', 'airflow',
    'databricks', 'snowflake',
    
    # Mobile Development
    'android', 'ios', 'react native', 'flutter', 'xamarin', 'ionic', 'swift ui',
    'kotlin multiplatform',
    
    # Version Control
    'git', 'svn', 'mercurial', 'github', 'gitlab', 'bitbucket',
    
    # Testing
    'junit', 'selenium', 'jest', 'pytest', 'mocha', 'cypress', 'testng',
    'cucumber', 'postman',
    
    # Project Management
    'agile', 'scrum', 'kanban', 'jira', 'trello', 'confluence', 'asana',
    'microsoft project',
    
    # Operating Systems
    'linux', 'unix', 'windows', 'macos', 'ubuntu', 'centos', 'red hat',
    
    # Security
    'cybersecurity', 'encryption', 'oauth', 'jwt', 'ssl/tls', 'penetration testing',
    'ethical hacking',
    
    # Soft Skills
    'leadership', 'communication', 'problem solving', 'teamwork', 'time management',
    'critical thinking', 'project management', 'analytical skills',
    
    # Design
    'ui/ux', 'figma', 'sketch', 'adobe xd', 'photoshop', 'illustrator',
    'indesign', 'after effects',
    
    # DevOps
    'devops', 'ci/cd', 'ansible', 'puppet', 'chef', 'nagios', 'prometheus',
    'grafana', 'elk stack',
    
    # Certifications
    'aws certified', 'microsoft certified', 'cisco certified', 'pmp', 'scrum master',
    'comptia', 'ceh', 'cissp'
}

def extract_text(pdf_path: str) -> str:
    """
    Extract text from a PDF file using pdfplumber.
    
    Args:
        pdf_path (str): Path to the PDF file
    
    Returns:
        str: Extracted text from the PDF
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ''
            for page in pdf.pages:
                text += page.extract_text() or ''
        return text.lower()
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ''

def get_skills_from_llm(text: str) -> Set[str]:
    """
    Use LLM to extract skills from text.
    
    Args:
        text (str): Resume text to analyze
    
    Returns:
        Set[str]: Set of extracted skills
    """
    prompt = """
    You are a skilled HR professional and technical recruiter. Analyze the following resume text 
    and extract RELEVANT TECHNICAL SKILLS AND COMPETENCIES. Follow these rules:
    
    1. Extract ONLY technical/professional skills (no certifications/degrees)
    2. Split compound terms (e.g., "AI/ML" → "AI", "Machine Learning")
    3. Use standardized names (e.g., "OpenCV" not "CV2")
    4. Exclude experience levels (e.g., "5 years experience")
    5. Normalize framework names (e.g., "React.js" → "React")
    
    Examples of GOOD output:
    python, machine learning, react, computer vision, opencv
    
    Examples of BAD output:
    - Generative AI\n- Certifications: AWS Certified
    - 5 years experience in Python
    - B.Tech in Computer Science
    
    Format output as a simple comma-separated list of skills ONLY.
    
    Resume text:
    {text}
    """.format(text=text[:4000])

    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",  # Can be replaced with other models
            messages=[
                {"role": "system", "content": "You are a skilled technical recruiter who extracts skills from resumes."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Lower temperature for more consistent outputs
            max_tokens=1000
        )
        
        # Extract skills from response and clean them
        skills_text = response.choices[0].message.content
        # Enhanced cleaning pattern
        skills_text = re.sub(
            r"(?i)(certifications?:|degrees?:|years? experience|\(.*?\)|"
            r"\b(?:and|or|proficient|experienced|strong)\b.+|"
            r"\b[0-9+]+\+?\s*(?:years?|yrs?)\b|[:.-]$)",
            "", 
            skills_text
        )
        # Split and normalize
        skills = set()
        for item in re.split(r'[,/\n]', skills_text):
            skill = re.sub(
                r'^\W+|\W+$|^(?:skill|technolog)(?:y|ies)\s*:?\s*', 
                '', 
                item.strip(), 
                flags=re.IGNORECASE
            )
            if skill and len(skill) <= 40:  # Prevent long phrases
                skills.add(skill.lower())
        return skills
    
    except Exception as e:
        print(f"Error in LLM processing: {e}")
        return set()

def validate_skills(llm_skills: Set[str], known_skills: Set[str]) -> Set[str]:
    # Normalize all skills to lowercase with consistent formatting
    normalized_known = {k.lower().replace(' ', '_') for k in known_skills}
    
    validated_skills = set()
    for raw_skill in llm_skills:
        # Create normalized versions for matching
        skill = raw_skill.lower().strip()
        skill_underscore = skill.replace(' ', '_')
        
        # Check multiple representations
        if (skill in normalized_known or 
            skill_underscore in normalized_known or
            any(skill in ks for ks in normalized_known)):
            validated_skills.add(raw_skill)
            continue
            
        # Check for special cases
        if re.search(r'(?:^|\b)(ai|ml|nlp|cv)(?:$|\b)', skill):
            validated_skills.add(raw_skill)
    
    # Add special handling for combined terms
    combined_terms = {
        'ai/ml': {'ai', 'machine learning'},
        'generative ai': {'ai', 'deep learning'}
    }
    
    for term, expansions in combined_terms.items():
        if term in llm_skills:
            validated_skills.update(expansions)
            validated_skills.discard(term)
            
    # Use LLM to validate ambiguous skills
    ambiguous = [s for s in llm_skills if s not in validated_skills]
    if ambiguous:
        validation_prompt = f"""
        Classify these skills as VALID or INVALID. Consider:
        - Standard technical terms
        - Common industry terminology
        - Specific tools/technologies
        
        Skills: {', '.join(ambiguous)}
        
        Respond ONLY in format: "skill:VALID|INVALID,skill:VALID|INVALID..."
        """
        
        try:
            validation_resp = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{
                    "role": "system", 
                    "content": "You are a technical validator. Classify skills as VALID or INVALID."
                }, {
                    "role": "user", 
                    "content": validation_prompt
                }],
                temperature=0.2,
                max_tokens=500
            )
            
            for pair in validation_resp.choices[0].message.content.split(','):
                skill, status = pair.split(':')
                if status.strip().lower() == 'valid':
                    validated_skills.add(skill.strip().lower())
                    
        except Exception as e:
            print(f"Skill validation error: {e}")
    
    return validated_skills

def improved_extract_skills(text: str) -> List[str]:
    """
    Extract skills using LLM and validate them against known skills.
    
    Args:
        text (str): Full text from the document
    
    Returns:
        List[str]: A sorted list of unique extracted skills
    """
    # Get skills from LLM
    llm_skills = get_skills_from_llm(text)
    
    # Validate and combine skills
    validated_skills = validate_skills(llm_skills, KNOWN_SKILLS)
    
    # Sort and return as list
    return sorted(list(validated_skills))

def analyze_pdf(pdf_path: str) -> List[str]:
    """
    Analyze a PDF file by extracting its text and identifying skills/qualifications.
    
    Args:
        pdf_path (str): Path to the PDF file
    
    Returns:
        List[str]: Extracted skills and qualifications
    """
    print(f"\nAnalyzing PDF: {pdf_path}")
    text = extract_text(pdf_path)
    
    if not text:
        print("Error: Could not extract text from PDF")
        return []
    
    print("\nExtracting skills using LLM...")
    skills = improved_extract_skills(text)
    
    print("\nExtracted skills and qualifications:")
    for i, skill in enumerate(skills, 1):
        print(f"{i}. {skill}")
    
    return skills

class SkillAnalyzer:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    def _get_skills_from_llm(self, text: str) -> Set[str]:
        """Wrapper for the global get_skills_from_llm function."""
        return get_skills_from_llm(text)
    
    def _validate_skills(self, llm_skills: Set[str]) -> List[str]:
        """Wrapper for the global validate_skills function."""
        return sorted(list(validate_skills(llm_skills, KNOWN_SKILLS)))
    
    def extract_skills(self, text: str) -> List[str]:
        """Extract and validate skills from any given text."""
        llm_skills = self._get_skills_from_llm(text)
        return self._validate_skills(llm_skills)
    
    def compare_documents(self, resume_text: str, jd_text: str) -> dict:
        """Compare resume and job description with enhanced scoring."""
        resume_skills = set(self.extract_skills(resume_text))
        jd_skills = set(self.extract_skills(jd_text))
        
        # Dynamic scoring based on JD emphasis
        jd_skill_counts = Counter(jd_skills)
        total_jd_mentions = sum(jd_skill_counts.values())
        jd_weights = {
            skill: (count/total_jd_mentions) * 3.0  # Weight based on JD frequency
            for skill, count in jd_skill_counts.items()
        }
        
        # Enhanced matching with semantic similarity
        matched_skills = set()
        for jd_skill in jd_skills:
            jd_lower = jd_skill.lower()
            # Check for direct matches
            if any(jd_lower == rs.lower() for rs in resume_skills):
                matched_skills.add(jd_skill)
                continue
            
            # Check for partial matches using LLM
            for resume_skill in resume_skills:
                similarity_prompt = f"""
                Do these skills describe the same technical capability?
                1. {jd_skill}
                2. {resume_skill}
                
                Answer ONLY 'yes' or 'no'
                """
                # Implement actual LLM call here
        
        # Calculate weighted score
        total_weight = sum(jd_weights.values())
        matched_weight = sum(jd_weights.get(skill, 0) for skill in matched_skills)
        score = (matched_weight / total_weight * 100) if total_weight > 0 else 0

        return {
            "matched": list(matched_skills),
            "missing": list(jd_skills - matched_skills),
            "score": min(round(score, 2), 100),  # Ensure max 100
            "explanation": f"Score based on weighted match of {len(matched_skills)}/{len(jd_skills)} JD skills"
        }

def analyze_resume_vs_jd(resume_path: str, jd_path: str) -> dict:
    """Main analysis workflow."""
    start_time = time.time()
    
    analyzer = SkillAnalyzer()
    
    # Extract texts
    resume_text = extract_text(resume_path)
    jd_text = extract_text(jd_path)
    
    if not resume_text or not jd_text:
        raise ValueError("Could not extract text from one or both documents")
    
    # Perform comparison
    report = analyzer.compare_documents(resume_text, jd_text)
    
    # Export scoring metrics as JSON
    scoring_report = {
        "matched_skills": report.get("matched", []),
        "missing_skills": report.get("missing", []),
        "score": report.get("score", 0),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Append to existing file instead of overwriting
    try:
        with open("score_report.json", "r+") as f:
            try:
                existing = json.load(f) if os.path.getsize("score_report.json") > 0 else []
                # Check last 3 entries for duplicates
                if any(scoring_report['score'] == entry['score'] and 
                       set(scoring_report['missing_skills']) == set(entry['missing_skills'])
                       for entry in existing[-3:]):
                    print("Duplicate entry detected, skipping save")
                else:
                    existing.append(scoring_report)
                    f.seek(0)
                    f.truncate()
                    json.dump(existing, f, indent=4)
            except json.JSONDecodeError:
                existing = []
                existing.append(scoring_report)
                f.seek(0)
                f.truncate()
                json.dump(existing, f, indent=4)
    except FileNotFoundError:
        with open("score_report.json", "w") as f:
            json.dump([scoring_report], f, indent=4)
            
    print("\nExported scoring metrics to 'score_report.json'")
    
    # Print results including detailed analysis
    print(f"\nMatch Score: {report['score']:.2f}%")
    print("\nMatched Skills:")
    print('\n'.join(f"- {s}" for s in report['matched']))
    print("\nMissing Skills:")
    print('\n'.join(f"- {s}" for s in report['missing']))
    print("\nDetailed Analysis:")
    print(report['explanation'])
    
    # Add time taken output
    elapsed = time.time() - start_time
    print(f"\nTime taken: {elapsed:.2f} seconds")
    
    return report

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Compare resume against job description')
    parser.add_argument('resume_path', help='Path to resume PDF')
    parser.add_argument('jd_path', help='Path to job description PDF')
    args = parser.parse_args()
    
    analyze_resume_vs_jd(args.resume_path, args.jd_path)