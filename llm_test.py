import re
import pdfplumber
from openai import OpenAI
import os
from typing import List, Set

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
    and extract ALL relevant skills, qualifications, and competencies. Include:
    
    1. Technical skills and tools
    2. Programming languages
    3. Frameworks and libraries
    4. Soft skills
    5. Domain knowledge
    6. Certifications
    7. Academic qualifications
    
    Format the output as a simple comma-separated list of skills.
    
    Resume text:
    {text}
    """.format(text=text[:4000])  # Limit text length to avoid token limits

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
        skills = {skill.strip().lower() for skill in skills_text.split(',') if skill.strip()}
        return skills
    
    except Exception as e:
        print(f"Error in LLM processing: {e}")
        return set()

def validate_skills(llm_skills: Set[str], known_skills: Set[str]) -> Set[str]:
    """
    Validate and combine skills from LLM with known skills.
    
    Args:
        llm_skills (Set[str]): Skills extracted by LLM
        known_skills (Set[str]): Known skills from our database
    
    Returns:
        Set[str]: Validated and combined skills
    """
    validated_skills = set()
    
    for skill in llm_skills:
        # Add skills that are in our known list
        if skill.lower() in {k.lower() for k in known_skills}:
            validated_skills.add(skill)
        # Add skills that look like valid technical terms or certifications
        elif (
            any(char.isdigit() for char in skill) or  # Contains numbers (e.g., "python3", "aws s3")
            re.search(r'^[A-Za-z+#.]+$', skill) or    # Looks like a programming language or framework
            re.search(r'^[A-Z]+$', skill) or          # All caps (likely an acronym)
            len(skill.split()) >= 2                    # Multi-word skills are likely valid
        ):
            validated_skills.add(skill)
    
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
        """Compare resume and job description."""
        resume_skills = set(self.extract_skills(resume_text))
        jd_skills = set(self.extract_skills(jd_text))
        
        # Calculate match metrics
        matched_skills = resume_skills & jd_skills
        missing_skills = jd_skills - resume_skills
        additional_skills = resume_skills - jd_skills
        match_percentage = (len(matched_skills) / len(jd_skills) * 100) if jd_skills else 0
        
        # Generate AI explanation
        explanation = self._generate_comparison_explanation(
            resume_text, jd_text, matched_skills, missing_skills
        )
        
        return {
            'score': match_percentage,
            'matched': sorted(matched_skills),
            'missing': sorted(missing_skills),
            'additional': sorted(additional_skills),
            'explanation': explanation
        }
    
    def _generate_comparison_explanation(self, resume: str, jd: str, 
                                         matched: Set[str], missing: Set[str]) -> str:
        """Generate a natural language explanation of the comparison."""
        prompt = f"""
        Analyze this job description and resume comparison:
        
        Job Description Requirements:
        {jd[:3000]}
        
        Resume Content:
        {resume[:3000]}
        
        Matched Skills: {', '.join(matched)}
        Missing Skills: {', '.join(missing)}
        
        Write a detailed analysis that:
        1. Explains the candidate's suitability based on skill matches
        2. Highlights critical missing requirements
        3. Notes any exceptional additional qualifications
        4. Provides overall hiring recommendation
        5. Suggests areas for resume improvement
        
        Structure the analysis with clear sections and bullet points.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{
                    "role": "system",
                    "content": "You are an experienced HR analyst providing detailed candidate assessments."
                }, {
                    "role": "user",
                    "content": prompt
                }],
                temperature=0.4,
                max_tokens=1500
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error generating explanation: {e}")
            return "Could not generate analysis"

def analyze_resume_vs_jd(resume_path: str, jd_path: str) -> dict:
    """Main analysis workflow."""
    analyzer = SkillAnalyzer()
    
    # Extract texts
    resume_text = extract_text(resume_path)
    jd_text = extract_text(jd_path)
    
    if not resume_text or not jd_text:
        raise ValueError("Could not extract text from one or both documents")
    
    # Perform comparison
    report = analyzer.compare_documents(resume_text, jd_text)
    
    # Print results
    print(f"\nMatch Score: {report['score']:.1f}%")
    print("\nMatched Skills:")
    print('\n'.join(f"- {s}" for s in report['matched']))
    print("\nMissing Skills:")
    print('\n'.join(f"- {s}" for s in report['missing']))
    print("\nAnalysis:")
    print(report['explanation'])
    
    return report

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Compare resume against job description')
    parser.add_argument('resume_path', help='Path to resume PDF')
    parser.add_argument('jd_path', help='Path to job description PDF')
    args = parser.parse_args()
    
    analyze_resume_vs_jd(args.resume_path, args.jd_path)