# CryptoAI: AI-Powered Crypto Trading Intelligence Platform

**A secure, intelligent platform for analyzing crypto portfolios and market conditions through natural-language AI assistance.**

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Tech Stack](#tech-stack)
3. [Analysis Context & Data Requirements](#analysis-context--data-requirements)
4. [Functional Requirements](#functional-requirements)
5. [API Endpoints](#api-endpoints)
6. [Frontend Architecture](#frontend-architecture)
7. [Security & Compliance](#security--compliance)
8. [Non-Functional Requirements](#non-functional-requirements)
9. [Acceptance Criteria](#acceptance-criteria)
10. [Stretch Goals](#stretch-goals)

---

## 🎯 Project Overview

### Core Concept

Users securely connect their crypto exchange accounts (e.g., Binance) and ask natural-language questions about their portfolio and market conditions. The system intelligently understands the question, retrieves live market and portfolio data, performs technical analysis, and returns actionable insights with supporting visualizations.

**Key Philosophy:** Build a decision-support workflow (understand → retrieve → analyze → reason → explain → visualize), not a simple chatbot answering from a fixed knowledge base.

### Example User Questions

The AI should handle informal, multilingual, and vague queries:

- "Should I buy more BTC?"
- "I bought ETH at a higher price. Should I hold or sell?"
- "Is SOL a good investment right now?"
- "Mera BTC ka kya karun?" (Roman Urdu: "What should I do with my BTC?")
- "Is this a good entry point?"
- "Should I take profit or wait?"

### Scope & Constraints

- **Initial Scope:** Read-only intelligence and analysis platform
- **Out of Scope (v1):** Automatic buying/selling (planned for future, post-security audit)
- **Language Support:** English, Roman Urdu, mixed-language queries, abbreviations, spelling variations
- **Query Handling:** No rigid prompt templates—system normalizes vague or unstructured questions

---

## 🛠 Tech Stack

| Layer | Technology | Role |
|-------|-----------|------|
| **Frontend** | Next.js + React + JavaScript | Login, dashboard, AI assistant, portfolio & market pages |
| **Styling** | Tailwind CSS + shadcn/ui | Responsive, reusable component library |
| **Data Fetching** | TanStack Query | API caching, server-state handling, errors & loading |
| **State Management** | Zustand | Lightweight client-side application state |
| **Charts** | TradingView Lightweight Charts | Candlestick, price, volume & technical-analysis visualizations |
| **Backend** | FastAPI (async) | Auth, exchange integration, AI orchestration, APIs |
| **Database** | PostgreSQL | Users, exchanges, portfolios, chats, analyses, alerts, complaints |
| **Auth** | JWT (access + refresh tokens) | Protects user data and sensitive endpoints |
| **ORM** | SQLAlchemy | Database access and models |
| **Migrations** | Alembic | Schema version control |
| **AI Orchestration** | LangGraph | Query routing, tool selection, multi-step workflows |
| **AI Framework** | LangChain (selective) | Tool integration & supporting utilities |
| **Vector Search** | pgvector | Semantic retrieval and embeddings |
| **Technical Analysis** | Pandas + NumPy + pandas-ta / TA-Lib | RSI, MACD, moving averages, indicators |
| **Caching** | Redis | Market-data caching & background-task state |
| **Background Tasks** | FastAPI BackgroundTasks or queue worker | Sync, alerts, retries, long-running operations |
| **Real-Time** | WebSockets (where required) | Live updates & streaming data |
| **Deployment** | Docker + managed cloud services | Consistent, scalable deployment |

---

## 📊 Analysis Context & Data Requirements

### Required Analysis Context (Structured)

Define precisely what information the AI uses. The system should use available context without inventing missing data.

| Context | Source | Required? | Example |
|---------|--------|-----------|---------|
| **asset_symbol** | User question or AI resolution | Usually Yes | BTC |
| **user_intent** | Query-understanding layer | Yes | buy_more, hold, sell_partial |
| **current_market_price** | Market data service | Yes (for current analysis) | $95,000 |
| **timeframe** | User question or default | No | 1D, 4H, 1H |
| **portfolio_holding** | Connected exchange | No | 0.35 BTC |
| **average_entry_price** | Exchange/history | No | $82,000 |
| **portfolio_exposure** | Calculated | No | 28% |
| **risk_profile** | User preferences | No | Conservative, Moderate, Aggressive |
| **technical_indicators** | Analysis engine | Depends on request | RSI, MACD, EMA, Bollinger Bands |

### Context Rules

- ✅ Do not reject a valid question simply because optional context is unavailable
- ✅ Use all available context before asking the user for additional information
- ✅ Answer market-data-only questions without requiring portfolio information
- ✅ Resolve common names and symbols (Bitcoin → BTC, Ethereum → ETH)
- ✅ Support English, Roman Urdu, mixed-language, abbreviations, spelling mistakes
- ✅ Use previous conversation context for follow-up questions
- ❌ Never expose exchange credentials or secrets to the AI layer
- ❌ If personalized assessment depends heavily on missing entry price, ask concise follow-up only

---

## ✅ Functional Requirements

### Authentication & Authorization

- Users can register and log in; backend issues JWT access + refresh tokens
- JWT tokens authorize all protected requests
- Logged-in users can securely connect supported crypto exchanges with minimum required permissions
- Exchange integration is read-only (v1)
- Users can disconnect exchange accounts and revoke application access

### Portfolio & Data Integration

- System retrieves permitted portfolio information: balances, holdings, asset allocation, transaction history
- Exchange credentials are encrypted and stored securely; never returned to frontend after storage
- Each user can only view/act on their own data (enforced at query level)

### AI Trading Assistant

- Users ask natural-language questions without rigid templates
- Backend analyzes questions to identify intent, assets, available context, and appropriate tools
- Workflow retrieves information from portfolio tools, market tools, technical-analysis tools, and semantic search
- Live prices and portfolio data come from authoritative sources; embeddings never treated as market truth
- Technical indicators are calculated (never invented by LLM)
- AI generates structured assessments: **Buy Gradually**, **Hold**, **Consider Selling**, **Insufficient Context**
- Responses are descriptive with reasoning, risk level, and key price levels
- AI distinguishes between factual retrieved data and generated interpretation

### User Features

- View connected portfolio, asset allocation, portfolio-level insights
- Maintain watchlists of selected crypto assets
- Save and revisit previous AI analyses and chat sessions
- Create alerts for selected assets/conditions
- Submit complaints through dedicated portal and track status
- View interactive charts supporting analysis
- Profile/security page for preferences, risk profile, connected exchanges, sessions

### Administrative Features

- Manage users, complaints, and application-level records (role-based)
- Audit sensitive operations (account connections, security settings, credential management)

---

## 🔌 API Endpoints

### Authentication

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/auth/register` | None | Create new user account |
| POST | `/auth/login` | None | Authenticate and return JWT tokens |
| POST | `/auth/refresh` | Refresh token | Issue new access token |
| GET | `/auth/me` | JWT | Return current user information |

### Exchange Integration

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/exchanges/connect` | JWT | Connect supported exchange account |
| DELETE | `/exchanges/{id}` | JWT | Remove connected exchange |
| POST | `/exchanges/{id}/sync` | JWT | Refresh permitted exchange data |

### Portfolio & Market

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/portfolio` | JWT | Portfolio summary |
| GET | `/portfolio/assets` | JWT | Asset details |
| GET | `/market/{symbol}` | JWT | Market summary |
| GET | `/market/{symbol}/chart` | JWT | Historical/chart data |

### AI & Analysis

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/ai/chat` | JWT | Process natural-language question |
| GET | `/ai/sessions` | JWT | List user's chat sessions |
| GET | `/ai/sessions/{id}` | JWT | Return one chat session + messages |
| GET | `/analyses` | JWT | List saved analysis reports |
| GET | `/analyses/{id}` | JWT | Return one analysis report |

### Watchlists & Alerts

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/watchlists` | JWT | List user's watchlists |
| POST | `/watchlists` | JWT | Create watchlist |
| POST | `/alerts` | JWT | Create alert |
| GET | `/alerts` | JWT | List user's alerts |

### Support & Complaints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/complaints` | JWT | Submit complaint |
| GET | `/complaints` | JWT | List user's complaints |
| GET | `/complaints/{id}` | JWT | View complaint & messages |

**Note:** Admin endpoints protected separately through role-based authorization.

---

## 🎨 Frontend Architecture

### Page Structure

1. **Login / Register Page**
   - Authentication flow with secure session establishment

2. **Dashboard**
   - Portfolio summary, market overview
   - Important alerts, recent analyses
   - Quick access to AI assistant

3. **Connect Exchange Page**
   - Explain required permissions
   - Read-only integration flow
   - Clear communication of security model

4. **Portfolio Page**
   - Holdings and asset allocation
   - Portfolio value and trends
   - Portfolio-level insights and composition

5. **AI Trading Assistant**
   - Natural-language input
   - Descriptive answers with analysis cards
   - Supporting charts and visualizations

6. **Market Explorer**
   - Search and inspect supported crypto assets
   - Market overview and trends

7. **Asset Detail Page**
   - Price information and candlestick charts
   - Volume and technical indicators
   - AI analysis actions

8. **Watchlist Page**
   - Monitor selected assets
   - Custom alerts and notifications

9. **Analysis History Page**
   - Previous AI reports
   - Saved analyses and sessions

10. **Alerts Page**
    - Configured alerts and status
    - Alert management and history

11. **Complaint Portal**
    - Submit complaints
    - Track status and view responses

12. **Profile / Security Page**
    - User preferences and risk profile
    - Connected exchanges management
    - Session management
    - Security-related actions

13. **Admin Pages**
    - User management
    - Complaint management
    - Application analytics (stretch goal)

---

## 🔒 Security & Compliance

### Credential Management

- ✅ Exchange credentials encrypted before storage
- ✅ Decrypted only when required by backend integration
- ✅ Never stored in frontend state, localStorage, browser logs, or AI conversation content
- ✅ Initial exchange integration requests minimum required permissions
- ✅ Never expose credentials in API responses, logs, or prompts

### Authentication & Access Control

- ✅ Passwords hashed; never stored or logged in plain text
- ✅ JWT access tokens have reasonable expiry (not long-lived)
- ✅ Refresh-token flow for session management
- ✅ Each user can only view/act on their own data (enforced at query level)
- ✅ External API failures handled gracefully without exposing credentials

### Audit & Logging

- ✅ Sensitive actions logged without logging secrets or credentials
- ✅ Audit trail for account connections, security settings, credential management
- ✅ Rate limiting protects authentication, AI, and exchange-related endpoints
- ✅ HTTPS enforced for all production traffic

---

## ⚙️ Non-Functional Requirements

### Performance & Reliability

- External API failures must not crash application; return clear errors with retry logic
- Frequently requested market data cached to reduce API calls and rate-limit issues
- Technical indicators calculated from data, not fabricated by LLM
- Long-running tasks (sync, alerts) run asynchronously where appropriate
- System fails safely when market/exchange data unavailable rather than inventing confident answers

### AI & Data Quality

- AI handles vague/poorly formatted questions gracefully by normalizing query and resolving context
- System asks follow-up only when necessary; selects correct tools intelligently
- AI distinguishes clearly between factual retrieved data and generated interpretation
- AI output includes appropriate uncertainty and risk communication
- Market predictions never presented as guaranteed

---

## ✔️ Acceptance Criteria

- ✅ User can register, log in, and access protected pages
- ✅ User can securely connect primary supported exchange with restricted permissions
- ✅ Exchange credentials never exposed in frontend or normal API responses
- ✅ Application retrieves and displays user's permitted portfolio information
- ✅ User can ask crypto questions without rigid prompt templates
- ✅ System correctly routes questions to relevant tools (portfolio, market, technical-analysis, retrieval)
- ✅ Live market data and portfolio info retrieved from authoritative sources, not invented
- ✅ Application calculates and displays relevant technical indicators
- ✅ Every AI assessment includes clear conclusion, reasoning, risk info, and uncertainty
- ✅ Supporting charts correctly reflect analysis data
- ✅ Users can view previous analyses and chat history
- ✅ Users can create and manage watchlists and alerts
- ✅ Users can submit and track complaints
- ✅ Users cannot view/act on other users' data, even by guessing IDs
- ✅ External API failures handled gracefully without exposing credentials

---

## 🚀 Stretch Goals

### Enhanced Features

- Multi-exchange support through unified exchange-integration interface
- Advanced portfolio analytics: diversification scoring, concentration-risk analysis
- Market news and sentiment analysis as additional context source
- Scheduled portfolio synchronization
- Price and technical-condition alerts
- Richer AI-generated market reports
- Provider router: select different LLMs by task complexity, speed, cost
- Retry handling for temporary exchange/market-data failures
- Two-factor authentication and stronger security features
- Downloadable analysis reports (PDF/Excel)
- Advanced admin analytics for application usage and support trends

### Future Capabilities (Phase 2+)

- **Trade Execution** (separately secured after core read-only platform is fully tested)
  - Requires advanced authorization and risk controls
  - Phased rollout with strict security audit

---

## 📝 Implementation Notes

> **Before implementation:** Confirm expected exchange permissions, market-data provider, recommendation boundaries, and security requirements rather than guessing and rebuilding later.

### Key Design Principles

1. **Security-First:** Credentials encrypted, never exposed, minimal permissions granted
2. **Data-Driven:** Live data from authoritative sources, not LLM invention
3. **User-Centric:** Natural language, mixed-language support, no rigid templates
4. **Fail-Safe:** Graceful degradation, clear error communication, no silent failures
5. **Auditable:** All sensitive operations logged without exposing secrets

---

## 📞 Contact & Questions

For clarifications on requirements, exchange permissions, market-data providers, or recommendation boundaries, confirm expectations before implementation to avoid costly rebuilds.

---

**Project Structure:** FastAPI + PostgreSQL backend | Next.js + React frontend | LangGraph AI orchestration | Real-time WebSockets | Docker deployment
