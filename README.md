# AI-Powered Resume Screening Solution Report  
**Automated Candidate Evaluation System**  

---

## 1. Solution Overview  
An end-to-end AI system for resume screening that:  
- Extracts skills from resumes and job descriptions (JDs)  
- Generates match scores with detailed explanations  
- Provides visual analytics and improvement recommendations  

---

## 2. Key Features  

| Component                | Description                                                                 |
|--------------------------|-----------------------------------------------------------------------------|
| Multi-Format Support      | Processes PDF/DOCX files                                                    |
| Contextual Skill Mapping  | Recognizes implied skills (e.g., "Hackathon Winner" → "Competitive Coding") |
| Dynamic Scoring           | Adaptive weights based on JD priorities                                     |
| Bias Mitigation           | Standardized evaluation framework                                           |
| Deployment-Ready          | Streamlit web app with one-click execution                                  |

---

## 3. Technology Stack  

**AI Components**  
- OpenAI GPT-4o (Skill extraction/analysis)  
- LangChain (RAG pipeline)  
- ChromaDB (Vector database)  

**Document Processing**  
- PyMuPDF (PDF parsing)  
- python-docx (DOCX parsing)  

**Frontend**  
```python
streamlit run app.py  # Launch command
```

## 4.  System Architecture

```
User Upload → Text Extraction → AI Analysis → Score Generation → Visual Dashboard  
```

## 5. Scoring Methodology

**Formula:**
```python
overall_score = (  
    Technical_Skills * 0.6 +  
    Qualifications * 0.4 +  
    Certifications_Bonus +  
    Experience_Bonus  
)
```

**Weight Adjustment Logic:**
```python
if JD_requires_certifications:  
    technical_weight = 50  
else:  
    technical_weight = 60  
```

## 6. Innovation Highlights

**✅ Project-to-Skill Mapping**
- "Chatbot development" → NLP
- "Smart India Hackathon" → Competitive Coding

**✅ Experience Validation**
- 2 years at FAANG = 10% bonus
- Research internships = Published papers

**✅ Explainable AI**
- GPT-generated score breakdown
- Actionable candidate feedback

## 7. Deployment Guide

**1. Install dependencies:**

```bash
pip install -r requirements.txt
```

**2. Configure OpenAI API key in Streamlit secrets**

**3. Launch app:**
```bash
streamlit run app.py
```