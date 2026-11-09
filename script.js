// Backend API Endpoint
const API_BASE_URL = "http://127.0.0.1:8000";

// DOM Elements
const resumeFileInput = document.getElementById("resumeFileInput");
const browseBtn = document.getElementById("browseBtn");
const dropZone = document.getElementById("dropZone");
const selectedFileName = document.getElementById("selectedFileName");
const analyzeBtn = document.getElementById("analyzeBtn");
const loadingIndicator = document.getElementById("loadingIndicator");
const resultsSection = document.getElementById("results");

let selectedFile = null;
let skillsRadarChart = null;

// File Upload Handlers
browseBtn.addEventListener("click", () => resumeFileInput.click());
dropZone.addEventListener("click", (e) => {
  if (e.target !== analyzeBtn) resumeFileInput.click();
});

dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.style.borderColor = "#2563eb";
});

dropZone.addEventListener("dragleave", () => {
  dropZone.style.borderColor = "#cbd5e1";
});

dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.style.borderColor = "#cbd5e1";
  if (e.dataTransfer.files.length > 0) {
    handleFileSelected(e.dataTransfer.files[0]);
  }
});

resumeFileInput.addEventListener("change", (e) => {
  if (e.target.files.length > 0) {
    handleFileSelected(e.target.files[0]);
  }
});

function handleFileSelected(file) {
  selectedFile = file;
  selectedFileName.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
  analyzeBtn.disabled = false;
}

// Call FastAPI Backend
analyzeBtn.addEventListener("click", async (e) => {
  e.stopPropagation();
  if (!selectedFile) return;

  const formData = new FormData();
  formData.append("file", selectedFile);

  loadingIndicator.style.display = "block";
  resultsSection.style.display = "none";
  analyzeBtn.disabled = true;

  try {
    const res = await fetch(`${API_BASE_URL}/api/resume/parse`, {
      method: "POST",
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Server failed to process resume");
    }

    const data = await res.json();
    renderAnalysisResults(data);
  } catch (error) {
    alert("Analysis Error: " + error.message + "\nMake sure the Python backend is running at " + API_BASE_URL);
  } finally {
    loadingIndicator.style.display = "none";
    analyzeBtn.disabled = false;
  }
});

// Render UI with Backend Data
function renderAnalysisResults(data) {
  resultsSection.style.display = "grid";

  // 1. Populate ATS Score
  const ats = data.ats_analysis;
  document.getElementById("atsScoreValue").textContent = ats.ats_score;
  document.getElementById("contactScore").textContent = `${ats.contact_score}/20`;
  document.getElementById("sectionScore").textContent = `${ats.section_score}/30`;
  document.getElementById("skillScore").textContent = `${ats.skill_score}/30`;
  document.getElementById("impactScore").textContent = `${ats.impact_score}/20`;

  // 2. Populate Detected Skills
  const pillsContainer = document.getElementById("skillsPillsContainer");
  pillsContainer.innerHTML = "";
  if (data.detected_skills.length === 0) {
    pillsContainer.innerHTML = "<em>No standardized technical skills detected.</em>";
  } else {
    data.detected_skills.forEach(skill => {
      const pill = document.createElement("span");
      pill.className = "pill";
      pill.textContent = skill;
      pillsContainer.appendChild(pill);
    });
  }

  // 3. Render Career Cards
  const careerContainer = document.getElementById("careerCardsContainer");
  careerContainer.innerHTML = "";
  data.career_matches.forEach(career => {
    const card = document.createElement("div");
    card.className = `career-card ${career.is_ready ? "high-match" : ""}`;
    card.innerHTML = `
      <h4>${career.role}</h4>
      <div class="career-pct">${career.match_percentage}% Match</div>
      <p style="font-size: 0.85rem; color: #64748b; margin-bottom: 0.5rem;">${career.description}</p>
      <div style="font-size: 0.85rem;"><strong>Est. Salary:</strong> ${career.avg_salary}</div>
      <div style="margin-top: 0.5rem;">
        <span style="font-size: 0.8rem; font-weight: bold; color: #166534;">Matched:</span>
        <div class="pills-container" style="margin: 0.2rem 0;">
          ${career.matched_skills.map(s => `<span class="pill" style="font-size: 0.75rem;">${s}</span>`).join("") || "<em>None</em>"}
        </div>
      </div>
      <div style="margin-top: 0.5rem;">
        <span style="font-size: 0.8rem; font-weight: bold; color: #991b1b;">Missing (Skill Gap):</span>
        <div class="pills-container" style="margin: 0.2rem 0;">
          ${career.missing_skills.map(s => `<span class="pill missing" style="font-size: 0.75rem;">${s}</span>`).join("") || "<em>No gaps detected!</em>"}
        </div>
      </div>
    `;
    careerContainer.appendChild(card);
  });

  // 4. Render Recommendations
  const recList = document.getElementById("recommendationsList");
  recList.innerHTML = "";
  ats.recommendations.forEach(rec => {
    const li = document.createElement("li");
    li.textContent = rec;
    recList.appendChild(li);
  });

  // Smooth scroll to results
  resultsSection.scrollIntoView({ behavior: "smooth" });
}

// -------------------------------------------------------------
// MOCK INTERVIEW MODULE
// -------------------------------------------------------------
const interviewQuestions = {
  "AI / Machine Learning Engineer": [
    "Explain how you would handle imbalanced data when training a machine learning classifier.",
    "Describe the difference between fine-tuning a model and Retrieval-Augmented Generation (RAG).",
    "How do you evaluate model drift in a production environment?"
  ],
  "Full-Stack Web Developer": [
    "Explain how asynchronous event loops work in JavaScript and Node.js.",
    "How do you protect a modern REST or GraphQL API from unauthorized access and SQL injection?",
    "Describe your approach to state management in large-scale frontend applications."
  ],
  "Data Scientist / Analyst": [
    "How do you identify outliers in a dataset and decide whether to impute or drop them?",
    "Walk me through an A/B testing scenario you set up and how you measured significance.",
    "What is the difference between supervised and unsupervised learning with real-world examples?"
  ],
  "Cloud & DevOps Engineer": [
    "How do you design an automated zero-downtime CI/CD deployment pipeline?",
    "Describe how Docker containers communicate across a Kubernetes cluster.",
    "What strategies do you use for cloud infrastructure cost optimization?"
  ]
};

const roleSelect = document.getElementById("interviewRoleSelect");
const qText = document.getElementById("currentQuestionText");
const nextQBtn = document.getElementById("nextQuestionBtn");
const userAnswerInput = document.getElementById("userAnswerInput");
const submitAnswerBtn = document.getElementById("submitAnswerBtn");
const feedbackBox = document.getElementById("interviewFeedbackBox");

function updateQuestion() {
  const role = roleSelect.value;
  const questions = interviewQuestions[role] || interviewQuestions["Full-Stack Web Developer"];
  const randomQ = questions[Math.floor(Math.random() * questions.length)];
  qText.textContent = randomQ;
  feedbackBox.style.display = "none";
  userAnswerInput.value = "";
}

roleSelect.addEventListener("change", updateQuestion);
nextQBtn.addEventListener("click", updateQuestion);

submitAnswerBtn.addEventListener("click", async () => {
  const answer = userAnswerInput.value.trim();
  if (!answer) {
    alert("Please write an answer before submitting.");
    return;
  }

  submitAnswerBtn.disabled = true;
  submitAnswerBtn.textContent = "Grading Answer...";

  try {
    const res = await fetch(`${API_BASE_URL}/api/interview/evaluate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        role: roleSelect.value,
        question: qText.textContent,
        user_answer: answer
      })
    });

    const data = await res.json();
    document.getElementById("evalScore").textContent = data.score;
    document.getElementById("evalWords").textContent = data.word_count;
    document.getElementById("evalFeedbackText").textContent = data.feedback;
    feedbackBox.style.display = "block";
  } catch (err) {
    alert("Could not evaluate answer. Make sure backend is running: " + err.message);
  } finally {
    submitAnswerBtn.disabled = false;
    submitAnswerBtn.textContent = "Evaluate My Answer";
  }
});
