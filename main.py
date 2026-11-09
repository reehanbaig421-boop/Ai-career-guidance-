import re
import io
import math
import sqlite3
from typing import List, Dict, Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader
from docx import Document

# Initialize FastAPI App
app = FastAPI(
    title="AI Career Guidance System API",
    description="Backend API for Resume Parsing, ATS Scoring, Career Matching, and Mock Interviews",
    version="1.0.0"
)

# Enable CORS for Frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# DATABASE INITIALIZATION (SQLite)
# -------------------------------------------------------------
DB_PATH = "career_database.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            target_career TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            ats_score INTEGER,
            top_career TEXT,
            detected_skills TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# -------------------------------------------------------------
# KNOWLEDGE BASE: SKILLS TAXONOMY & CAREER BENCHMARKS
# -------------------------------------------------------------
SKILLS_TAXONOMY = {
    "languages": ["python", "javascript", "typescript", "java", "c++", "c#", "go", "ruby", "php", "sql", "r", "html", "css"],
    "frameworks": ["react", "vue", "angular", "node.js", "express", "fastapi", "django", "flask", "spring boot", "next.js", "tailwind"],
    "ai_data": ["machine learning", "deep learning", "nlp", "tensorflow", "pytorch", "pandas", "numpy", "scikit-learn", "data visualization", "opencv", "power bi", "tableau"],
    "cloud_devops": ["docker", "kubernetes", "aws", "azure", "gcp", "git", "ci/cd", "linux", "terraform", "jenkins"],
    "databases": ["postgresql", "mysql", "mongodb", "redis", "sqlite", "oracle"]
}

CAREER_PROFILES = {
    "AI / Machine Learning Engineer": {
        "required_skills": ["python", "machine learning", "deep learning", "pytorch", "tensorflow", "pandas", "numpy", "sql", "docker", "git"],
        "min_skills_expected": 6,
        "avg_salary": "$115,000 - $160,000",
        "description": "Designs and builds intelligent machine learning models, training pipelines, and generative AI systems."
    },
    "Full-Stack Web Developer": {
        "required_skills": ["javascript", "react", "html", "css", "node.js", "sql", "git", "docker", "express", "typescript"],
        "min_skills_expected": 6,
        "avg_salary": "$90,000 - $135,000",
        "description": "Builds both client-facing web interfaces and robust server-side APIs and database architectures."
    },
    "Data Scientist / Analyst": {
        "required_skills": ["python", "sql", "pandas", "numpy", "data visualization", "tableau", "power bi", "scikit-learn", "r", "machine learning"],
        "min_skills_expected": 5,
        "avg_salary": "$95,000 - $140,000",
        "description": "Extracts actionable business insights from structured and unstructured data using statistics and modeling."
    },
    "Cloud & DevOps Engineer": {
        "required_skills": ["linux", "docker", "kubernetes", "aws", "azure", "ci/cd", "git", "terraform", "python", "jenkins"],
        "min_skills_expected": 5,
        "avg_salary": "$105,000 - $150,000",
        "description": "Automates deployment pipelines, ensures cloud security, and maintains continuous system uptime."
    }
}

ACTION_VERBS = [
    "developed", "engineered", "designed", "architected", "implemented",
    "optimized", "scaled", "automated", "spearheaded", "accelerated",
    "improved", "reduced", "led", "managed", "deployed"
]

# -------------------------------------------------------------
# HELPER FUNCTIONS: TEXT EXTRACTION & NLP
# -------------------------------------------------------------
def extract_text_from_pdf(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text

def extract_text_from_docx(content: bytes) -> str:
    doc = Document(io.BytesIO(content))
    return "\n".join([para.text for para in doc.paragraphs if para.text])

def extract_skills(text: str) -> List[str]:
    lowered = text.lower()
    found = set()
    for category, skill_list in SKILLS_TAXONOMY.items():
        for skill in skill_list:
            # Word boundary regex for exact term matching
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, lowered):
                found.add(skill.title())
    return sorted(list(found))

def calculate_ats_score(text: str, skills: List[str]) -> Dict:
    lowered = text.lower()
    score = 0
    feedback = []

    # 1. Contact Information Check (20 points)
    has_email = bool(re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text))
    has_phone = bool(re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text))
    has_links = ("github.com" in lowered) or ("linkedin.com" in lowered)
    
    contact_score = 0
    if has_email: contact_score += 8
    if has_phone: contact_score += 7
    if has_links: contact_score += 5
    score += contact_score
    if contact_score < 20:
        feedback.append("Add your LinkedIn or GitHub profile link and complete contact details.")

    # 2. Key Sections Detection (30 points)
    sections = ["experience", "education", "skills", "projects"]
    section_score = sum(7.5 for s in sections if s in lowered)
    score += int(section_score)
    if section_score < 30:
        feedback.append("Ensure your resume has standard headings: Experience, Education, Skills, and Projects.")

    # 3. Skill Density (30 points)
    skill_score = min(30, len(skills) * 3)
    score += skill_score
    if len(skills) < 8:
        feedback.append(f"Detected only {len(skills)} technical skills. Aim for at least 8-12 industry keywords.")

    # 4. Action Verbs & Metrics (20 points)
    verbs_found = [v for v in ACTION_VERBS if re.search(r'\b' + v + r'\b', lowered)]
    has_metrics = bool(re.search(r'\b\d+([.,]\d+)?%?\b', text))
    
    impact_score = min(12, len(verbs_found) * 2) + (8 if has_metrics else 0)
    score += impact_score
    if not has_metrics:
        feedback.append("Quantify your achievements using percentages, time saved, or numbers (e.g., 'improved query speed by 30%').")

    return {
        "ats_score": min(100, score),
        "contact_score": contact_score,
        "section_score": int(section_score),
        "skill_score": skill_score,
        "impact_score": impact_score,
        "action_verbs_found": verbs_found,
        "recommendations": feedback if feedback else ["Excellent resume structure! Your resume complies with ATS guidelines."]
    }

def match_careers(candidate_skills: List[str]) -> List[Dict]:
    cand_set = set([s.lower() for s in candidate_skills])
    results = []

    for role, data in CAREER_PROFILES.items():
        req_set = set(data["required_skills"])
        matched = cand_set.intersection(req_set)
        missing = req_set - cand_set
        
        # Jaccard / Percentage calculation
        match_pct = int((len(matched) / len(req_set)) * 100) if req_set else 0

        results.append({
            "role": role,
            "match_percentage": match_pct,
            "description": data["description"],
            "avg_salary": data["avg_salary"],
            "matched_skills": [s.title() for s in matched],
            "missing_skills": [s.title() for s in missing],
            "is_ready": match_pct >= 60
        })

    # Sort descending by match percentage
    results.sort(key=lambda x: x["match_percentage"], reverse=True)
    return results

# -------------------------------------------------------------
# API ROUTES
# -------------------------------------------------------------
@app.get("/")
def root():
    return {"message": "AI Career Guidance API is running. Access docs at /docs"}

@app.post("/api/resume/parse")
async def parse_resume(file: UploadFile = File(...)):
    """Accepts PDF, DOCX, or TXT file and returns full ATS and career match analysis."""
    filename = file.filename.lower()
    content = await file.read()

    try:
        if filename.endswith(".pdf"):
            text = extract_text_from_pdf(content)
        elif filename.endswith(".docx"):
            text = extract_text_from_docx(content)
        elif filename.endswith(".txt"):
            text = content.decode("utf-8", errors="ignore")
        else:
            raise HTTPException(status_code=400, detail="Unsupported format. Upload PDF, DOCX, or TXT.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")

    if not text.strip():
        raise HTTPException(status_code=400, detail="The file is empty or readable text could not be extracted.")

    # Execute AI Analytics pipeline
    detected_skills = extract_skills(text)
    ats_results = calculate_ats_score(text, detected_skills)
    career_matches = match_careers(detected_skills)

    return {
        "filename": file.filename,
        "text_preview": text[:350] + "...",
        "detected_skills": detected_skills,
        "ats_analysis": ats_results,
        "career_matches": career_matches
    }

class InterviewEvaluationRequest(BaseModel):
    role: str
    question: str
    user_answer: str

@app.post("/api/interview/evaluate")
def evaluate_interview_response(data: InterviewEvaluationRequest):
    """Evaluates an interview answer using keyword density, STAR methodology, and length."""
    answer = data.user_answer.strip().lower()
    words = answer.split()
    word_count = len(words)

    if word_count < 10:
        return {
            "score": 30,
            "feedback": "Your answer is too short. Structure your response with context, actions taken, and results.",
            "star_breakdown": {"situation": False, "task": False, "action": False, "result": False}
        }

    # Check for STAR methodology keywords
    has_situation = any(k in answer for k in ["when", "during", "project", "problem", "challenge", "scenario"])
    has_action = any(k in answer for k in ["i implemented", "i built", "i designed", "i created", "i used", "i led"])
    has_result = any(k in answer for k in ["resulted", "improved", "learned", "achieved", "reduced", "delivered"])

    base_score = 50
    if word_count >= 40: base_score += 15
    if has_situation: base_score += 10
    if has_action: base_score += 15
    if has_result: base_score += 10

    feedback = []
    if not has_situation: feedback.append("Start by giving the context or background of the situation.")
    if not has_action: feedback.append("Specify clearly what action YOU took using strong technical verbs.")
    if not has_result: feedback.append("End with the positive outcome or measurable result.")
    if not feedback: feedback.append("Strong response! You clearly structured your answer with context, execution, and outcomes.")

    return {
        "score": min(100, base_score),
        "word_count": word_count,
        "feedback": " ".join(feedback),
        "star_breakdown": {
            "context_provided": has_situation,
            "action_described": has_action,
            "result_shared": has_result
        }
    }
