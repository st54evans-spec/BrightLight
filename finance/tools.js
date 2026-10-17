// Tools the Grok bot can call. Each has a JSON schema (OpenAI-compatible) and a handler
// that receives (args, ctx) where ctx = { userId }.
const calc = require("./calculators");
const models = require("./models");
const reports = require("./reports");
const { businessLenders, helocLenders, PRIME } = require("./lenders");
const forms = require("./integrations/forms");
const credit = require("./integrations/credit");
const calendar = require("./calendar");

const num = (d) => ({ type: "number", description: d });
const str = (d) => ({ type: "string", description: d });

const tools = {
  get_financial_snapshot: {
    description: "Accounts, cash, net worth, last-3-month business averages (revenue, COGS, opex, debt service, gross margin), spending by category.",
    parameters: { type: "object", properties: {} },
    handler: async (_, ctx) => {
      const accounts = await models.listAccounts(ctx.userId);
      const transactions = await models.listTransactions(ctx.userId);
      const s = reports.summary({ accounts, transactions });
      return { accounts, cash: s.cash, netWorth: s.netWorth, business: s.business, spendingPie: s.spendingPie, months: s.cashFlowBar.labels.length };
    },
  },
  get_tax_deadlines: {
    description: "Authoritative federal + NJ tax due dates for a tax year. 1040-ES installments and the return date come only from this tool (weekend dates already rolled to the next business day). Never invent a due date.",
    parameters: { type: "object", required: ["year"], properties: { year: num("Tax year, e.g. 2026") } },
    handler: async ({ year }, ctx) => {
      const profile = await models.getProfile(ctx.userId);
      return { taxYear: Number(year), deadlines: calendar.taxYearDeadlines(year, profile.entity) };
    },
  },
  get_upcoming_events: {
    description: "Financial calendar: taxes, bills, invoices, bookkeeping. Defaults to the next 45 days. Due dates already stored here are authoritative; do not replace them with a guess.",
    parameters: { type: "object", properties: { days: num("Look-ahead window in days"), category: str("tax|bill|invoice|bookkeeping|planning|compliance|loan|insurance") } },
    handler: async ({ days = 45, category }, ctx) => {
      const from = new Date().toISOString().slice(0, 10);
      const to = new Date(Date.now() + days * 864e5).toISOString().slice(0, 10);
      return models.listEvents(ctx.userId, { from, to, category, status: "pending" });
    },
  },
  add_calendar_event: {
    description: "Add a financial event (deadline, bill, invoice, follow-up) to the calendar.",
    parameters: { type: "object", required: ["date", "title"], properties: { date: str("YYYY-MM-DD"), title: str("What"), category: str("tax|bill|invoice|bookkeeping|planning|compliance|loan|insurance"), amount: num("Amount if any"), notes: str("Notes") } },
    handler: (a, ctx) => models.addEvent(ctx.userId, { ...a, category: a.category || "planning", source: "bot" }),
  },
  complete_calendar_event: {
    description: "Mark a calendar event done.",
    parameters: { type: "object", required: ["id"], properties: { id: num("Event id") } },
    handler: ({ id }, ctx) => models.updateEvent(ctx.userId, id, { status: "done" }),
  },
  seed_tax_calendar: {
    description: "Load federal + NJ tax deadlines that fall in a calendar year, plus the default bill/invoice cadence. 1040-ES and the return use the tax-year schedule (weekend-adjusted). Q4 and the Form 1040 for a tax year fall in the next calendar year. For the full tax-year list, call get_tax_deadlines.",
    parameters: { type: "object", required: ["year"], properties: { year: num("Calendar year") } },
    handler: async ({ year }, ctx) => {
      const profile = await models.getProfile(ctx.userId);
      const events = calendar.buildYear(year, { entity: profile.entity }).map((e) => ({ ...e, source: "seed" }));
      const added = await models.addEvents(ctx.userId, events);
      return { year, added };
    },
  },
  list_lenders: {
    description: "Business loan and HELOC lender catalogs with indicative rates and year-one structures.",
    parameters: { type: "object", properties: { kind: str("business|heloc") } },
    handler: ({ kind = "business" }) => ({ prime: PRIME, lenders: kind === "heloc" ? helocLenders : businessLenders }),
  },
  compare_loans: {
    description: "Rank business lenders for an amount/term on year-one cash outlay, total interest, and max loan size. Supports interest-only and stepped first year.",
    parameters: { type: "object", required: ["amount"], properties: { amount: num("Loan amount"), termMonths: num("Term in months, default 120"), customLenders: { type: "array", description: "Optional lender quotes to include: [{name, product, rate, maxAmount, maxTermMonths, structure, introMonths, originationFeePct}]", items: { type: "object" } } } },
    handler: ({ amount, termMonths = 120, customLenders = [] }) => calc.compareLoans({ amount, termMonths, lenders: [...businessLenders, ...customLenders] }),
  },
  amortize: {
    description: "Full payment schedule for one loan.",
    parameters: { type: "object", required: ["principal", "annualRate", "termMonths"], properties: { principal: num(""), annualRate: num("e.g. 0.095"), termMonths: num(""), structure: str("standard|interest_only|stepped"), introMonths: num("Months of intro structure"), introPaymentPct: num("Stepped: fraction of full payment in intro"), originationFeePct: num("") } },
    handler: (a) => {
      const r = calc.amortize(a);
      return { ...r, schedule: r.schedule.filter((s) => s.month <= 12 || s.month % 12 === 0) };
    },
  },
  heloc_refinance: {
    description: "Size a HELOC on 2034 Lambert Ave to clear listed debts plus renovation; checks CLTV and compares blended rates. If debts omitted, uses stored liability accounts.",
    parameters: { type: "object", required: ["homeValue"], properties: { homeValue: num(""), firstMortgageBalance: num(""), renovationBudget: num(""), helocRate: num("default 0.0675"), drawMonths: num("default 120"), repayMonths: num("default 240"), maxCLTV: num("default 0.85"), closingCosts: num(""), debts: { type: "array", items: { type: "object", properties: { name: str(""), balance: num(""), rate: num(""), payment: num("") } } } } },
    handler: async (a, ctx) => {
      let debts = a.debts;
      if (!debts) {
        const accounts = await models.listAccounts(ctx.userId);
        debts = accounts.filter((x) => ["credit", "loan", "heloc"].includes(x.type)).map((x) => ({ name: x.name, balance: Math.abs(Number(x.balance)), rate: Number(x.rate) || 0.2, payment: Number(x.payment) || 0 }));
        if (a.firstMortgageBalance == null) {
          const m = accounts.find((x) => x.type === "mortgage");
          if (m) a.firstMortgageBalance = Math.abs(Number(m.balance));
        }
      }
      return { ...calc.helocRefinance({ ...a, debts }), lenders: helocLenders };
    },
  },
  tax_estimate: {
    description: "Federal + NJ income tax estimate for the family and the Schedule C business, with quarterly estimates.",
    parameters: { type: "object", properties: { year: num("default 2026"), filingStatus: str("single|mfj|hoh|mfs"), w2Wages: num(""), businessNetProfit: num("STOiiiC FiT net profit"), otherIncome: num(""), dependentsUnder17: num(""), otherDependents: num(""), itemizedDeductions: num(""), federalWithheld: num(""), njWithheld: num(""), estimatesPaid: num("") } },
    handler: (a) => calc.taxEstimate(a),
  },
  life_insurance_needs: {
    description: "DIME life insurance sizing with policy guidance.",
    parameters: { type: "object", properties: { debts: num(""), annualIncome: num(""), yearsToReplace: num("default 15"), mortgageBalance: num(""), educationPerChild: num("default 120000"), children: num("default 1"), finalExpenses: num(""), existingCoverage: num(""), liquidAssets: num("") } },
    handler: (a) => calc.lifeInsuranceNeeds(a),
  },
  retirement_projection: {
    description: "Retirement projection and the extra monthly needed to hit a target income.",
    parameters: { type: "object", required: ["currentAge"], properties: { currentAge: num(""), retireAge: num("default 65"), currentSavings: num(""), monthlyContribution: num(""), annualReturn: num("default 0.07"), inflation: num("default 0.03"), desiredAnnualIncome: num("default 80000"), withdrawalRate: num("default 0.04") } },
    handler: (a) => calc.retirementProjection(a),
  },
  education_projection: {
    description: "529 / education fund projection for Brynlee.",
    parameters: { type: "object", properties: { childAge: num(""), startAge: num("default 18"), currentSavings: num(""), monthlyContribution: num(""), annualReturn: num("default 0.06"), targetToday: num("default 120000"), costInflation: num("default 0.05") } },
    handler: (a) => calc.educationProjection(a),
  },
  move_readiness: {
    description: "Can the financials back a STOiiiC FiT move (new line, store, inventory buy, ad push)? GO / NOT YET / NO with the checks. Omitted business numbers come from the snapshot.",
    parameters: { type: "object", required: ["moveCost"], properties: { moveCost: num(""), expectedMonthlyLiftRevenue: num(""), liftMarginPct: num(""), rampMonths: num("default 3"), cash: num(""), monthlyRevenue: num(""), monthlyCOGS: num(""), monthlyOpex: num(""), monthlyDebtService: num(""), minRunwayMonths: num("default 6") } },
    handler: async (a, ctx) => {
      const accounts = await models.listAccounts(ctx.userId);
      const transactions = await models.listTransactions(ctx.userId, { is_business: true });
      const s = reports.summary({ accounts, transactions });
      return calc.moveReadiness({ cash: s.cash, ...s.business, ...a });
    },
  },
  unit_economics: {
    description: "Small-business break-even and unit economics. Break-even units = fixed costs / contribution margin per unit. Also compares a lower price against the extra volume it needs, and shows where marketing spend saturates. Explain the returned explanation in plain, optimistic language. Do not invent costs the owner did not give.",
    parameters: {
      type: "object",
      required: ["price"],
      properties: {
        price: num("Current selling price per unit"),
        unitCost: num("Variable cost to make one unit, before fees"),
        feePct: num("Marketplace or payment fee as a fraction of price, e.g. 0.03"),
        fixedCosts: num("Fixed costs for the period (rent, software, base payroll)"),
        units: num("Units expected or already selling in that period"),
        alternatePrice: num("A lower price to test, such as a discounted T-shirt"),
        alternateUnits: num("Units expected at the lower price. Omit to get the volume required to match current profit."),
        marketingSpend: num("Extra marketing spend in the period"),
        saturationUnits: num("Max extra units marketing can add before demand flattens"),
        saturationSpend: num("Spend at which most of those extra units have already been reached"),
      },
    },
    handler: (a) => calc.unitEconomics(a),
  },
  pricing_plan: {
    description: "Top-dollar pricing: list price, floor, break-even after fees, and a drop schedule to sell by a date. For fixed-cost break-even and price or marketing tradeoffs, use unit_economics.",
    parameters: { type: "object", required: ["unitCost"], properties: { unitCost: num(""), targetMarginPct: num("default 0.55"), marketLow: num(""), marketHigh: num(""), units: num(""), mustSellByDays: num("default 30"), fees: num("marketplace/payment fees, default 0.03") } },
    handler: (a) => calc.pricingPlan(a),
  },
  prepare_document: {
    description: "Fill a form to the signature line. kinds: federal_1040, schedule_c, nj_1040, sba_1919, heloc_application, life_insurance_application. Returns filled fields, missing fields, and signature lines left for the owner.",
    parameters: { type: "object", required: ["kind"], properties: { kind: str(""), data: { type: "object", description: "Field values" } } },
    handler: async ({ kind, data = {} }, ctx) => {
      const prepared = forms.prepare(kind, data);
      const doc = await models.addDocument(ctx.userId, prepared);
      return { ...prepared, id: doc.id };
    },
  },
  pull_credit_report: {
    description: "Pull the owner's credit report through the connected provider. Requires explicit consent=true from the owner in this conversation.",
    parameters: { type: "object", required: ["consent"], properties: { consent: { type: "boolean" }, consumer: { type: "object", description: "name, dob, ssnLast4, address" } } },
    handler: async ({ consent, consumer = {} }, ctx) => {
      const r = await credit.pull({ consent, consumer });
      if (r.status === "ok") await models.addCreditReport(ctx.userId, { bureau: r.bureau, score: r.score, consent: true, data: r.report });
      const latest = (await models.listCreditReports(ctx.userId))[0];
      return { ...r, latest: latest ? { bureau: latest.bureau, score: latest.score, pulled_at: latest.pulled_at, analysis: credit.analyze({ score: latest.score, ...(latest.data ? JSON.parse(latest.data) : {}) }) } : null };
    },
  },
  save_profile_facts: {
    description: "Remember facts about the owner, family, home, or business (entity type, ages, income, home value, mortgage, goals).",
    parameters: { type: "object", required: ["facts"], properties: { facts: { type: "object" } } },
    handler: ({ facts }, ctx) => models.saveProfile(ctx.userId, facts),
  },
};

function openAiToolDefs() {
  return Object.entries(tools).map(([name, t]) => ({ type: "function", function: { name, description: t.description, parameters: t.parameters } }));
}

/** Flat function tools for the xAI Responses API (name sits on the tool, not under function). */
function responsesToolDefs() {
  return Object.entries(tools).map(([name, t]) => ({ type: "function", name, description: t.description, parameters: t.parameters }));
}

async function run(name, args, ctx) {
  const t = tools[name];
  if (!t) throw new Error("Unknown tool " + name);
  return t.handler(args || {}, ctx);
}

module.exports = { tools, openAiToolDefs, responsesToolDefs, run };
