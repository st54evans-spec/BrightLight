# Cato Ledger: the STOiiiC FiT finance desk

A Grok-powered accountant that lives inside BrightLight. He keeps the financial calendar, runs every number through real calculators, and fills paperwork to the signature line. You sign.

Rename him with `FINANCE_BOT_NAME`.

## What he does

| Area | How | Where |
|---|---|---|
| Calendar: taxes, bills, invoices | Seeds federal + NJ deadlines (1040/NJ-1040, 1040-ES, ST-50 sales tax, W-2/1099, extensions) plus bill-pay and invoice cadence; weekend dates roll to the next business day. Tax year 2026 1040-ES is Apr 15 2026, Jun 15 2026, Sep 15 2026, Jan 15 2027; the 2026 return is due Apr 15 2027 | `finance/calendar.js`, `POST /api/finance/calendar/seed/:year` |
| NJ + federal taxes (family + Schedule C) | 2026 federal brackets, standard deduction, child credit, SE tax, QBI; NJ gross income tax brackets and exemptions; quarterly estimates | `finance/taxTables.js`, `calculators.taxEstimate` |
| Business loan: high value, low year-one payments, best interest | Lender catalog (SBA 7(a), 504, NJEDA, credit union, online, LOC) scored on year-one cash outlay, total interest, max size; interest-only and stepped first-year structures | `finance/lenders.js`, `calculators.compareLoans` |
| HELOC on 2034 Lambert Ave | Sizes the line to clear every liability account plus the renovation budget, checks CLTV, compares blended rates, shows payment during draw vs repay, lists NJ HELOC lenders | `calculators.helocRefinance`, `POST /api/finance/heloc` |
| Credit reports | Pulls through any JSON credit provider with explicit consent, or accepts an uploaded annualcreditreport.com summary; tells you what lenders will see and what to fix | `finance/integrations/credit.js` |
| Paperwork to signature | Field maps for 1040, Schedule C, NJ-1040, SBA 1919, HELOC application, life insurance application; lists blank fields and the signature lines left for you; fills the official AcroForm PDF with pdf-lib | `finance/integrations/forms.js` |
| All financial data | Accounts + transactions (manual or Plaid sync); pie, line, bar chart data | `finance/reports.js`, `GET /api/finance/reports/summary` |
| STOiiiC FiT move readiness | GO / NOT YET / NO on margin, runway after the move, DSCR, payback, cash | `calculators.moveReadiness` |
| Top dollar when it must sell | List, floor, break-even, and a dated drop schedule | `calculators.pricingPlan` |
| Investing, retirement, Brynlee's 529 | Projections, gap, extra monthly needed, allocation by horizon, NJBEST note | `calculators.retirementProjection`, `educationProjection` |
| Life insurance | DIME sizing, term vs whole guidance, riders to ask for | `calculators.lifeInsuranceNeeds` |

The bot calls these as tools (`finance/tools.js`), so his answers are computed, not guessed. He is told to be optimistic on marketing and returns and strict on the math, and to flag anything a licensed CPA, EA, or advisor should review.

## Run it

```bash
cp .env.example .env            # add XAI_API_KEY at minimum
npm install
npm run migrate                 # builds the SQLite database from the knex migrations
npm start                       # API on :3111

cd clientLight && npm install
REACT_APP_API_URL=http://localhost:3111 npm start
```

Register, log in, open **Finance** in the nav bar (`/finance`). First click **Load tax + bill dates** on the calendar, then add accounts and a few transactions under **Charts** so the move-readiness and HELOC tools have real numbers.

```bash
npm test                        # 27 tests: calculators, calendar, forms, PDF fill, Grok request shape, full API smoke
```

## Database

`database/*.db3` is gitignored. `database/auth.db3` is a local SQLite file and is not part of the repo.

`npm run migrate` runs `knex migrate:latest`. On a missing database it builds every table from scratch:

1. `database/migrations/20190920152428_bootstrap.js` creates `users`.
2. `database/migrations/20261014120000_finance.js` creates the finance tables: profile, calendar events, accounts, transactions, goals, documents, messages, integrations, and credit reports.

Development points at `./database/auth.db3` (`knexfile.js`). Production uses Postgres via `DATABASE_URL` and the same migration files. To rebuild a local database, delete `database/auth.db3` and run `npm run migrate` again.

## Connect the data sources

- **Grok**: `XAI_API_KEY` from console.x.ai. Chat goes to the Responses API (`/v1/responses`). `XAI_AGENT_TOOLS=on` (the default) adds the server-side `web_search` and `x_search` tools so he can look up current lender rates. The deprecated Live Search field `search_parameters` is not sent. `XAI_LIVE_SEARCH` is still accepted as an alias when `XAI_AGENT_TOOLS` is unset.
- **Bank, card, investment accounts**: Plaid. Set `PLAID_CLIENT_ID`/`PLAID_SECRET`, open Plaid Link on the client with `POST /api/finance/plaid/link-token`, send the public token to `POST /api/finance/plaid/exchange`, then `POST /api/finance/plaid/sync` on a schedule.
- **Credit reports**: any provider that accepts `POST {consumer, consent}` and returns `{bureau, score, report}` (Array, CRS, Experian Connect all need a signed agreement). Set `CREDIT_API_URL`/`CREDIT_API_KEY`. Without one, upload the free weekly report summary to `POST /api/finance/credit/upload`.
- **Brokerage**: not wired. Add an investment account manually or through Plaid; trading stays in your broker.

## API

All routes are under `/api/finance` and need the JWT from `/api/auth/login` in the `Authorization` header.

```
GET  /persona                      who he is, what is connected
POST /chat {message}               talk to him; runs tools; history kept per user
GET  /messages  DELETE /messages
POST /tools/:name {...args}        call any tool without the LLM
GET  /calendar?from&to&category&status   POST /calendar   PATCH /calendar/:id   DELETE /calendar/:id
POST /calendar/seed/:year          GET /calendar/preview/:year
GET/POST /accounts  PATCH/DELETE /accounts/:id
GET/POST /transactions (array ok)
GET/POST /goals  PATCH /goals/:id
GET  /reports/summary              pie, line, bar data + business snapshot
GET  /lenders   POST /loans/compare {amount, termMonths, customLenders[]}   POST /loans/amortize
POST /heloc {homeValue, firstMortgageBalance?, renovationBudget, helocRate, maxCLTV, debts?}
POST /tax/estimate  POST /insurance/needs  POST /retirement  POST /education
POST /move-readiness  POST /pricing
GET  /documents/templates  GET/POST /documents(/prepare)  PATCH /documents/:id  POST /documents/:id/fill-pdf {pdfBase64, fieldMap?}
GET  /credit   POST /credit/pull {consent:true}   POST /credit/upload {bureau, score, report}
POST /plaid/link-token  /plaid/exchange  /plaid/sync
```

## Keep honest

- Tax tables are for tax year 2026. Update `finance/taxTables.js` every January.
- Lender and HELOC rates in `finance/lenders.js` are indicative (prime 6.75%, Oct 2026). Real offers go in as `customLenders` or get pasted to the bot.
- He prepares returns and applications; a human signs and files. Anything he flags for CPA/EA review should get it.
- Investment and insurance output is planning math, not licensed advice.
