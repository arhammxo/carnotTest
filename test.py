import pdfplumber
from docx import Document
from transformers import pipeline
from sentence_transformers import SentenceTransformer, util
import numpy as np
from flask import Flask, request, jsonify
import os
import re
from skill_extractor import improved_extract_skills

# Initialize models
ner_pipeline = pipeline("ner", 
                       model="dslim/bert-base-NER",
                       aggregation_strategy="simple")
sbert_model = SentenceTransformer('all-MiniLM-L6-v2')


app = Flask(__name__)

def extract_text(file_path):
    if file_path.endswith('.pdf'):
        with pdfplumber.open(file_path) as pdf:
            return "".join(page.extract_text() for page in pdf.pages)
    elif file_path.endswith('.docx'):
        return "\n".join(para.text for para in Document(file_path).paragraphs)
    else:
        with open(file_path, 'r') as f:
            return f.read()

def calculate_similarity(jd_skills, resume_skills, threshold=0.7):
    if not jd_skills:
        return [], []
    
    jd_emb = sbert_model.encode(jd_skills, convert_to_tensor=True)
    resume_emb = sbert_model.encode(resume_skills, convert_to_tensor=True)
    
    similarities = util.cos_sim(jd_emb, resume_emb)
    matches = []
    missing = []
    
    for i, jd_skill in enumerate(jd_skills):
        max_score = similarities[i].max().item()  # Changed from np.max to PyTorch's max()
        if max_score >= threshold:
            match_idx = similarities[i].argmax().item()  # Changed from np.argmax to PyTorch's argmax()
            matches.append((jd_skill, resume_skills[match_idx], float(max_score)))
        else:
            missing.append(jd_skill)
    
    return matches, missing

@app.route('/evaluate', methods=['POST'])
def evaluate():
    # Add validation
    if 'jd' not in request.files or 'resume' not in request.files:
        return jsonify({'error': 'Missing jd or resume in form-data'}), 400
        
    jd_file = request.files['jd']
    resume_file = request.files['resume']
    
    # Add file validation
    if jd_file.filename == '' or resume_file.filename == '':
        return jsonify({'error': 'Empty file submission'}), 400
    
    # Save files with original extensions
    jd_ext = os.path.splitext(jd_file.filename)[1]
    resume_ext = os.path.splitext(resume_file.filename)[1]
    jd_path = f'temp_jd{jd_ext}'
    resume_path = f'temp_resume{resume_ext}'
    
    jd_file.save(jd_path)
    resume_file.save(resume_path)
    
    try:
        jd_text = extract_text(jd_path)
        resume_text = extract_text(resume_path)
        
        jd_skills = improved_extract_skills(jd_text)
        resume_skills = improved_extract_skills(resume_text)
        
        matches, missing = calculate_similarity(jd_skills, resume_skills)
        score = (len(matches) / len(jd_skills)) * 100 if jd_skills else 0
        
        explanation = {
            'score': round(score, 2),
            'matched_skills': [f"{m[0]} (Match: {m[1]}, Confidence: {m[2]:.2f})" for m in matches],
            'missing_skills': missing
        }
        
        return jsonify(explanation)
    except Exception as e:
        return jsonify({'error': str(e)})
    finally:
        if os.path.exists(jd_path):
            os.remove(jd_path)
        if os.path.exists(resume_path):
            os.remove(resume_path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)