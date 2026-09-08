# CAM AI Platform — Flask Backend + Next.js Frontend

Bank of Baroda styled CAM proof-of-concept with a general-purpose Loan Summary CAM Assistant.

## Loan Summary CAM Assistant

The active chatbot on **Loan Summary** no longer follows a fixed Loan Type → Amount → Purpose → Tenure → Interest → Repayment questionnaire.

It now supports free-form questions and combines:

1. **Active borrower/CAM context**
2. **Uploaded borrower-document evidence** through the existing document RAG retriever
3. **MCA data** already fetched by the application
4. **Google web search** for public/current information
5. **Groq LLM** for the final response

Examples:

- `Give me the latest information about this borrower`
- `Search the web for recent news about this company`
- `What are the key business risks?`
- `What is the latest revenue?`
- `Summarize the uploaded financial statements`
- `Explain the company's business model`
- `What is the current industry outlook?`
- `What is RBI repo rate?`

The assistant can also opportunistically capture proposal fields when the user mentions a loan type, amount, tenure, interest rate or repayment structure. It never blocks the user waiting for a particular field.

## Configure backend

```powershell
cd backend
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set these values in `backend/.env`:

```text
GROQ_API_KEY=gsk_...
GROQ_MODEL=openai/gpt-oss-120b
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CSE_ID=your_programmable_search_engine_id
```

`GROQ_API_KEY`, `GOOGLE_API_KEY` and `GOOGLE_CSE_ID` are backend-only. Do not put them in Next.js `.env.local`.

Then start Flask:

```powershell
python app.py
```

Backend: `http://localhost:8000`

## Configure frontend

```powershell
cd frontend
npm install
Copy-Item .env.local.example .env.local
npm run dev
```

Frontend: `http://localhost:3000`

## Google setup

Create a Google Programmable Search Engine configured for web search and enable the **Custom Search JSON API** for the Google Cloud project. Put the resulting API key in `GOOGLE_API_KEY` and search engine ID in `GOOGLE_CSE_ID`.

If Google search is not configured, the Loan Summary assistant will report the search configuration problem instead of pretending that it has current web evidence.

## Security

The final answer is generated server-side. Search and Groq credentials are never sent to the browser. Public web information is presented separately from internal CAM/document evidence, and the assistant is instructed not to fabricate missing financial, policy or borrower facts.

## POC login

The login endpoint is `/api/auth/login`. The default POC credentials are controlled by backend `.env`:

```text
DEMO_EMPLOYEE_ID=BOB001
DEMO_PASSWORD=ChangeMe123!
DEMO_EMPLOYEE_NAME=Credit Officer
```

Change these values before sharing the POC. For production, replace this endpoint with Bank SSO + MFA.

## v6 Loan Summary POC integration
See `LOAN_SUMMARY_INTEGRATION.md`. The project now includes a dedicated Step-5 context pipeline, five packaged synthetic companies, mock/live external-data switching, mock/Google public enrichment, and a bounded Groq Loan Summary narrative.
