# QueueStorm Investigator — AI SupportOps Copilot

QueueStorm Investigator is a high-performance, robust, and safe AI-powered backend service designed as an internal copilot for digital finance support teams (bKash/fintech style). 

The service exposes two primary HTTP endpoints:
1. `GET /health`: Instant health status checking.
2. `POST /analyze-ticket`: Investigates customer complaints, matches them with recent transaction histories, detects fraud, safety risks, duplicates, or wrong transfers, and generates structured copilot analysis.

This project achieved a **100% pass rate (10/10 worked cases)** on the official preliminary test suite with an average response latency of **~1.08 seconds**.

---

## 🛠️ Tech Stack

- **Core Framework**: Python 3.11 with [FastAPI](https://fastapi.tiangolo.com/) (high performance, asynchronous, automatic OpenAPI documentation).
- **Validation Layer**: [Pydantic v2](https://docs.pydantic.dev/) for strict schema validation, type safety, and enum enforcement.
- **Web Server**: [Uvicorn](https://www.uvicorn.org/) (ASGI server).
- **Reasoning Engine**: Groq API hosting Llama 3.3 70B and Llama 3.1 8B (ultra-low latency LLM inference).
- **Containerization**: Docker (minimal multi-stage build, under 300MB).

---

## 🧠 AI & Hybrid Engineering Approach

QueueStorm Investigator uses a **hybrid rule-based and LLM-powered architecture**. Rather than relying solely on an LLM (which is slow, expensive, and prone to hallucinations or formatting errors), we implement a multi-stage pipeline:

```
[Incoming Request]
       │
       ▼
┌──────────────────────────────────────────┐
│   Fast Programmatic Pre-Analysis (Rules) │
│   - Extracts amounts and transaction IDs │
│   - Detects duplicates (same amount, time)│
│   - Identifies established counterparties│
│   - Detects multiple matches (ambiguity) │
└──────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│         LLM Reasoning Layer (Groq)       │
│   - Interprets multilingual complaints    │
│   - Reasons over rule-based findings     │
│   - Generates contextual agent action    │
│   - Drafts replies matching user language│
└──────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│  Programmatic Schema & Safety Validator  │
│   - Enforces 100% correct enums          │
│   - Overrides ambiguous cases to null/ID │
│   - Post-processes replies for safety     │
│   - Sanitizes credential/refund requests │
└──────────────────────────────────────────┘
       │
       ▼
[Response JSON]
```

### 1. Programmatic Pre-Analysis
Before calling the LLM, a fast rule engine parses the complaint text and transaction history:
- **Established Recipients**: If the customer claims a "wrong transfer", but history shows they have sent money to the recipient multiple times in the past, the system flags the claim as `inconsistent` to prevent human agents from being misled.
- **Duplicate Payments**: Identifies if two identical transactions occurred within a short time window. If the customer complains about double billing, it automatically targets the second transaction (the duplicate) as the relevant one.
- **Ambiguity Detection**: If multiple transactions match the complaint details, the system flags it as `insufficient_data` and prompts the agent to ask for clarification (e.g. requesting the phone number or specific transaction ID) instead of guessing.

### 2. LLM Reasoning Layer
The pre-analysis findings, transaction history, and complaint are sent to Groq. Groq's high-speed inference allows us to utilize the powerful Llama 3.3 70B model to semantically understand complaints in English, Bangla, or mixed Banglish, draft professional replies matching the customer's language, and write high-quality summaries.

### 3. Schema & Safety Post-Processor (Foolproof Guardrails)
To guarantee 100% schema compliance and absolute safety:
- **Enum Repair**: If the LLM generates a slightly incorrect enum value, the python layer automatically repairs and maps it to the allowed set.
- **Credential Requests Sanitizer**: If the customer reply contains any borderline request for a PIN, OTP, password, or full card number, the post-processor immediately blocks it and replaces it with an explicit security warning: *"For your safety, please never share your PIN, OTP, or password with anyone..."*
- **Refund Promise Sanitizer**: If the generated text promises a refund or reversal, the post-processor rewrites it to use passive, non-committal language: *"any eligible amount will be returned through official channels"*.

---

## 🔒 Safety Logic & Safeguards

To prevent critical safety penalties, we implemented active guardrails:
1. **No OTP/PIN/Password Requests**: Verified at the prompt level and programmatically scanned/blocked at the Python level.
2. **No Direct Refund/Reversal Promises**: Copilot never acts as a financial authority. The language is forcefully sanitized to non-committal, passive templates.
3. **No Third-Party Contacts**: Replaces any third-party links or phone numbers with instructions to contact official support channels.
4. **Prompt Injection Mitigation**: System instructions are sandboxed. The customer complaint is treated strictly as an untrusted string data payload, not as instructions.

---

## 🤖 Models Section

| Model Name | Host/Provider | Purpose | Choice Rationale |
| :--- | :--- | :--- | :--- |
| **Llama 3.3 70B** (`llama-3.3-70b-versatile`) | Groq API | Primary reasoning, semantic analysis, and multilingual text drafting | Exceptional logic capability, handles complex fintech context, and understands Bangla natively. Groq hosts this with sub-second latencies. |
| **Llama 3.1 8B** (`llama-3.1-8b-instant`) | Groq API | Fallback model in case of rate limits (429) or high-load situations | Lightweight, blazing-fast response times (~200ms), and capable of producing well-structured JSON when guided by our programmatic pre-analysis. |

### Cost & Performance Reasoning
- **Groq API**: Offers state-of-the-art token throughput and sub-second response times.
- **Cost Efficiency**: Combining local, lightweight Python rule-based pre-analysis reduces the prompt size and reasoning load on the LLM. It allows us to use smaller models (like the 8B fallback) without sacrificing accuracy, significantly lowering operational API costs under scale.
- **No Local Weight Footprint**: By calling external public API endpoints (as allowed in Section 9.1), our Docker image footprint remains under 300MB and requires 0 GPU resources, complying perfectly with the 1GB hard image limit.

---

## ⚡ Setup & Run Instructions

### Prerequisites
- Python 3.11+
- `pip` (Python package installer)
- A valid `GROQ_API_KEY` set in your environment variables.

### Local Installation
1. Clone the repository and navigate to the project directory:
   ```bash
   git clone https://github.com/shuaibuddowla/queuestorm-investigator-supportops.git
   cd queuestorm-investigator-supportops
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set the environment variable:
   - **Windows (PowerShell)**:
     ```powershell
     $env:GROQ_API_KEY="your_groq_api_key_here"
     ```
   - **Linux/macOS**:
     ```bash
     export GROQ_API_KEY="your_groq_api_key_here"
     ```

### Running the API
Start the FastAPI server locally:
```bash
python main.py
```
The service will start on `http://0.0.0.0:8000`.

### Running the Test Suite
To execute all 10 evaluation cases and generate a detailed report:
```bash
python run_tests.py
```
This will output test statuses, schema matching results, safety checks, and save a full report to `evaluation_report.json`.

---

## 🐳 Docker Deployment

To build and run the lightweight container:

### Build the Image
```bash
docker build -t queuestorm-team .
```

### Run the Container
Make sure to pass your `GROQ_API_KEY` at runtime:
```bash
docker run -p 8000:8000 --env GROQ_API_KEY="your_groq_api_key" queuestorm-team
```

---

## 📝 Assumptions & Limitations

1. **Transaction Snippets**: We assume the transaction history provided represents the most recent transactions relevant to the ticket.
2. **Offline Mode**: Since the system relies on Groq API endpoints, an active internet connection is required. Under offline environments, a lightweight local model (like Llama-3-8B-Instruct via Ollama) can be integrated as a local fallback by redirecting the base URL.
