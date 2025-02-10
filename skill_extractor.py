import re
import pdfplumber
from transformers import pipeline

# Initialize the NER pipeline.
# Note: The model used here is generic. For better results on resumes, consider a domain-specific or fine-tuned model.
ner_pipeline = pipeline(
    "ner",
    model="dslim/bert-base-NER",
    aggregation_strategy="simple"
)

# A sample set of known skills. You can expand or load these from an external resource.
KNOWN_SKILLS = {
    # Expanded Technical Skills
    # Programming Languages
    'python', 'java', 'javascript', 'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin', 'go', 'rust',
    'typescript', 'scala', 'perl', 'r', 'matlab', 'bash', 'shell', 'powershell', 'sql', 'nosql',
    'haskell', 'lua', 'assembly', 'fortran', 'cobol', 'dart', 'elixir', 'clojure', 'f#',
    
    # Expanded AI/ML
    'llama', 'mistral', 'gemini', 'claude', 'diffusion models', 'attention mechanisms',
    'reinforcement learning', 'supervised learning', 'unsupervised learning', 'semi-supervised learning',
    'time series analysis', 'predictive modeling', 'anomaly detection', 'recommender systems',
    
    # Cloud & DevOps Expanded
    'serverless architecture', 'lambda functions', 'cloud formation', 'azure functions',
    'google cloud functions', 'cloud storage', 'vpc', 'cdn', 'load balancing', 'auto-scaling',
    'istio', 'helm charts', 'argo cd', 'github actions', 'circleci', 'travis ci',
    
    # New: Testing Frameworks
    'jest', 'mocha', 'junit', 'pytest', 'selenium', 'cypress', 'postman', 'soapui',
    'loadrunner', 'jmeter', 'k6', 'chaos engineering',
    
    # New: Academic Qualifications
    'bachelor of science', 'bsc', 'bachelor of arts', 'ba', 'master of science', 'msc',
    'master of business administration', 'mba', 'doctor of philosophy', 'phd',
    'postdoctoral research', 'thesis defense', 'peer-reviewed publications',
    'research methodology', 'academic writing', 'literature review',
    
    # New: Certifications
    'aws certified', 'azure certification', 'google cloud certified', 'cisco certified',
    'pmp', 'scrum master', 'six sigma', 'comptia security+', 'ceh', 'cissp',
    'cfa', 'cpa', 'frm', 'garp', 'nclex', 'bar exam',
    
    # Expanded Soft Skills
    'cross-cultural communication', 'active listening', 'mentorship', 'decision-making',
    'strategic planning', 'change management', 'conflict resolution', 'emotional intelligence',
    'adaptability', 'creativity', 'work ethic', 'professionalism', 'attention to detail',
    'resourcefulness', 'diplomacy', 'networking', 'cultural awareness',
    
    # New: Academic Disciplines
    'computer science', 'electrical engineering', 'mechanical engineering', 'physics',
    'mathematics', 'statistics', 'biology', 'chemistry', 'psychology', 'economics',
    'business administration', 'finance', 'accounting', 'political science',
    
    # Databases
    'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'oracle', 'sql server', 'dynamodb',
    'cassandra', 'neo4j', 'firebase',
    
    # Project Management & Methodologies
    'agile', 'scrum', 'kanban', 'waterfall', 'prince2', 'pmp', 'lean', 'six sigma',
    'project management', 'risk management', 'stakeholder management',
    
    # Soft Skills
    'leadership', 'communication', 'problem solving', 'team management', 'critical thinking',
    'time management', 'collaboration', 'presentation skills', 'negotiation', 'conflict resolution',
    
    # Design & UI/UX
    'ui design', 'ux design', 'user research', 'wireframing', 'prototyping', 'figma',
    'adobe photoshop', 'adobe illustrator', 'sketch', 'invision',
    
    # Security
    'cybersecurity', 'penetration testing', 'security auditing', 'encryption', 'oauth',
    'authentication', 'authorization', 'security protocols', 'network security',
    
    # Mobile Development
    'android', 'ios', 'react native', 'flutter', 'xamarin', 'mobile app development',
    'responsive design', 'progressive web apps',
}

def extract_text(pdf_path):
    """
    Extract text from a PDF file using pdfplumber.
    
    Args:
        pdf_path (str): Path to the PDF file.
    
    Returns:
        str: The full extracted text.
    """
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
    return text

def extract_section(text, section_header):
    """
    Extract a section from the text that starts with the given section header.
    
    This function searches for a header (e.g., 'Skills') and returns the content
    until the next header (assumed to be in all-caps or formatted similarly) or the end of the text.
    
    Args:
        text (str): The full text extracted from the document.
        section_header (str): The header indicating the section to extract.
    
    Returns:
        str: The extracted section text, or an empty string if not found.
    """
    # This regex looks for the header and captures text until the next header or end of text.
    pattern = rf'(?i){section_header}\s*[:\n]+(.*?)(?=\n[A-Z\s]{{2,}}[:\n]|$)'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""

def dictionary_skill_extraction(text):
    """Extract skills by matching known skills in the text."""
    extracted = set()
    lower_text = text.lower()
    
    # Add acronym handling
    acronyms = {
        'llm': 'large language model',
        'nlp': 'natural language processing',
        'ml': 'machine learning',
        'ai': 'artificial intelligence',
        'rag': 'retrieval augmented generation',
        # Academic acronyms
        'bsc': 'bachelor of science',
        'msc': 'master of science',
        'phd': 'doctor of philosophy',
        'mba': 'master of business administration',
        'cfa': 'chartered financial analyst',
        'cpa': 'certified public accountant',
        # Tech acronyms
        'ci/cd': 'continuous integration/continuous deployment',
        'tls': 'transport layer security',
        'ssl': 'secure sockets layer',
    }
    # Single word and phrase skill matching
    for skill in KNOWN_SKILLS:
        # Handle both singular and plural forms
        patterns = [
            r'\b' + re.escape(skill.lower()) + r'\b',
            r'\b' + re.escape(skill.lower()) + 's\b',  # plural form
            r'\b' + re.escape(skill.lower()) + 'es\b',  # plural form
        ]
        
        for pattern in patterns:
            if re.search(pattern, lower_text):
                # If it's an acronym, add both the acronym and its full form
                if skill.lower() in acronyms:
                    extracted.add(skill.upper())  # Add uppercase acronym
                    extracted.add(acronyms[skill.lower()])  # Add full form
                else:
                    extracted.add(skill)
    
    return extracted

def ner_skill_extraction(text):
    """
    Use the NER pipeline to extract potential skills and qualifications.
    
    Args:
        text (str): Text in which to perform NER.
    
    Returns:
        set: A set of entities extracted that might correspond to skills.
    """
    extracted = set()
    ner_results = ner_pipeline(text)
    for entity in ner_results:
        # Depending on your model, adjust the condition to capture the desired labels.
        if entity.get('entity_group', '') in {'MISC', 'SKILL'}:
            extracted.add(entity['word'].strip())
    return extracted

def improved_extract_skills(text):
    """
    Combine both dictionary matching and NER to extract skills.
    If a dedicated "Skills" section is found, focus the extraction there but also check other sections.
    
    Args:
        text (str): Full text from the document.
    
    Returns:
        list: A list of unique extracted skills and qualifications.
    """
    extracted_skills = set()
    
    # Check common section headers for skills
    sections_to_check = [
        'Skills', 'Technical Skills', 'Core Competencies', 'Qualifications',
        'Technologies', 'Tools', 'Expertise', 'Professional Skills'
    ]
    
    found_sections = False
    for section in sections_to_check:
        section_text = extract_section(text, section)
        if section_text:
            found_sections = True
            print(f"Analyzing '{section}' section...")
            extracted_skills.update(dictionary_skill_extraction(section_text))
            extracted_skills.update(ner_skill_extraction(section_text))
    
    # Always analyze the full text to catch skills mentioned in experience/projects
    if not found_sections:
        print("No dedicated skills sections found; analyzing the full text.")
    else:
        print("Additionally analyzing full text for context-based skills...")
    
    extracted_skills.update(dictionary_skill_extraction(text))
    extracted_skills.update(ner_skill_extraction(text))
    
    return sorted(list(extracted_skills))

def analyze_pdf(pdf_path):
    """
    Analyze a PDF file by extracting its text and identifying skills/qualifications.
    
    Args:
        pdf_path (str): Path to the PDF file.
    
    Returns:
        list: Extracted skills and qualifications.
    """
    print(f"\nAnalyzing PDF: {pdf_path}")
    text = extract_text(pdf_path)
    
    # Display a sample of the extracted text for verification.
    print("\nRaw text sample:")
    print(text[:500] + "...\n")
    
    skills = improved_extract_skills(text)
    
    print("Extracted skills and qualifications:")
    for i, skill in enumerate(skills, 1):
        print(f"{i}. {skill}")
    
    return skills

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Extract skills from PDF resumes')
    parser.add_argument('pdf_path', help='Path to the PDF file to analyze')
    args = parser.parse_args()
    
    analyze_pdf(args.pdf_path)
