# StudyAI — Exam Evaluator, Study Coach & Academic Analytics Platform

An AI-powered platform where students upload their textbook, exam paper, and answers — and AI agents evaluate performance, identify weak topics, and generate a personalised study plan.

---

## Architecture

```
studyAi/
├── frontend/          # Angular 16 SPA
├── backend/           # FastAPI + Google ADK agents
├── docker-compose.yml # Full stack orchestration
└── README.md
```

### Stack

| Layer            | Technology                        |
|------------------|-----------------------------------|
| Frontend         | Angular 16, Angular Material, Chart.js |
| Backend API      | FastAPI (Python 3.11)             |
| AI Agents        | Google ADK + Gemini 1.5 Flash     |
| Relational DB    | PostgreSQL 16                     |
| Vector DB (RAG)  | ChromaDB                          |
| Object Storage   | Local filesystem (MVP)            |
| Migrations       | Alembic                           |

---

## Workflow

```
Student → Upload textbook PDF   → Indexed into ChromaDB (RAG)
        → Upload exam paper      → Stored on disk + DB
        → Upload answers         → Stored on disk + DB
        → POST /evaluate         → EvaluationAgent runs (Gemini + RAG)
                                 → Report persisted to PostgreSQL
                                 → StudyPlanAgent generates plan
        → GET /report/{examId}   → View scores, weak topics, feedback
        → GET /study-plan/{id}   → View personalised study plan
```

---

## Quick Start

### 1. Prerequisites

- Docker Desktop (recommended)  **or** Node 20+, Python 3.11+, PostgreSQL 16

### 2. Configure environment

```bash
cp backend/.env.example backend/.env
# Edit backend/.env and set your GOOGLE_API_KEY
```

### 3. Run with Docker Compose

```bash
docker-compose up --build
```

- Frontend: http://localhost:4200  
- Backend API: http://localhost:8000  
- API Docs: http://localhost:8000/docs

### 4. Run locally (without Docker)

**Backend:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
# Start PostgreSQL and update DATABASE_URL in .env
uvicorn app.main:app --reload
```

**Database migrations (Alembic):**
```bash
cd backend
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

**Frontend:**
```bash
cd frontend
npm install
ng serve
```

---

## API Endpoints

| Method | Endpoint                    | Description                        |
|--------|-----------------------------|------------------------------------|
| POST   | `/students`                 | Register a new student             |
| GET    | `/students/{id}`            | Get student profile                |
| POST   | `/upload/textbook`          | Upload & index textbook PDF        |
| POST   | `/upload/exam`              | Upload exam paper (PDF or text)    |
| POST   | `/upload/answers`           | Upload answer sheet (PDF or text)  |
| POST   | `/evaluate`                 | Start AI evaluation (async)        |
| GET    | `/report/{examId}`          | Get evaluation report              |
| GET    | `/study-plan/{studentId}`   | Get latest study plan              |
| GET    | `/health`                   | Health check                       |

Interactive docs: **http://localhost:8000/docs**

---

## Frontend Pages

### `/upload` — Upload Wizard
A 5-step stepper:
1. Register student (name + email)
2. Upload textbook PDF (indexed into ChromaDB)
3. Upload exam paper (PDF or paste text)
4. Upload answer sheet (PDF or type answers)
5. Trigger AI evaluation → redirects to dashboard

### `/dashboard/:studentId` — Analytics Dashboard
- **Overview cards**: overall score, weak topics, strong topics
- **Analytics tab**: Radar chart + Bar chart of topic scores
- **Feedback tab**: Per-question AI feedback with model answers
- **Study Plan tab**: Week-by-week personalised study plan

---

## AI Agents (Google ADK)

### EvaluationAgent
- Retrieves relevant textbook chunks via ChromaDB (RAG)
- Sends exam + answers + context to Gemini 1.5 Flash
- Returns structured JSON: per-question scores, feedback, topic analysis

### StudyPlanAgent
- Receives the evaluation report
- Generates a multi-week, day-by-day study plan via Gemini
- Includes resource recommendations and study tips

### AgentOrchestrator
- Coordinates the full pipeline
- Runs asynchronously via FastAPI BackgroundTasks
- Persists results to PostgreSQL
