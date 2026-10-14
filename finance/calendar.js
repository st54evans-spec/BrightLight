// Financial calendar: federal + NJ deadlines, bill pay, invoice delivery.
// Recurring events are expanded for a given year. Dates that fall on a weekend
// are pushed to the next business day (IRS/NJ rule).

function nextBusinessDay(d) {
  const day = d.getDay();
  if (day === 6) d.setDate(d.getDate() + 2);
  else if (day === 0) d.setDate(d.getDate() + 1);
  return d;
}

function iso(y, m, d) {
  return nextBusinessDay(new Date(Date.UTC(y, m - 1, d, 12))).toISOString().slice(0, 10);
}

/**
 * 1040-ES installments and the income-tax return for one tax year.
 * Installments are Apr 15, Jun 15, and Sep 15 of the tax year, then Jan 15 of the next year.
 * The Form 1040 for that tax year is due Apr 15 of the next year (tax year 2026: Apr 15, 2027).
 * A pass-through business return is due Mar 15 of the next year.
 * Dates that fall on a weekend are rolled to the next business day.
 */
function taxYearDeadlines(taxYear, entity = "sole proprietorship") {
  const year = Number(taxYear);
  const isPassThroughEntity = /s-?corp|partnership|llc.*partner|multi/i.test(entity || "");
  const estimates = [
    [1, year, 4, 15],
    [2, year, 6, 15],
    [3, year, 9, 15],
    [4, year + 1, 1, 15],
  ].map(([quarter, y, m, d]) => ({
    date: iso(y, m, d),
    title: `Q${quarter} estimated tax for tax year ${year} - federal 1040-ES + NJ-1040-ES`,
    category: "tax",
    jurisdiction: "federal+nj",
    form: "1040-ES / NJ-1040-ES",
    taxYear: year,
    quarter,
    kind: "1040-ES",
  }));
  const deadlines = [...estimates];
  if (isPassThroughEntity) {
    deadlines.push({
      date: iso(year + 1, 3, 15),
      title: `Business return for tax year ${year} due (1120-S / 1065 + NJ CBT/NJ-1065)`,
      category: "tax",
      jurisdiction: "federal+nj",
      form: "1120-S or 1065",
      taxYear: year,
      kind: "business-return",
    });
  }
  deadlines.push({
    date: iso(year + 1, 4, 15),
    title: isPassThroughEntity
      ? `Federal 1040 + NJ-1040 for tax year ${year} due (or file extension 4868 / NJ-630)`
      : `Federal 1040 + NJ-1040 for tax year ${year} due (Schedule C files with the 1040; or file extension 4868 / NJ-630)`,
    category: "tax",
    jurisdiction: "federal+nj",
    form: "1040, NJ-1040",
    taxYear: year,
    kind: "return",
  });
  return deadlines;
}

/** Standard tax deadlines that fall in a calendar year. `entity` affects the business return date. */
function taxDeadlines(year, entity = "sole proprietorship") {
  const inYear = (e) => String(e.date).startsWith(String(year) + "-");
  const fromTaxYears = [...taxYearDeadlines(year - 1, entity), ...taxYearDeadlines(year, entity)].filter(inYear);
  return [
    ...fromTaxYears,
    { date: iso(year, 1, 20), title: "NJ sales tax ST-50 Q4 (prior year)", category: "tax", jurisdiction: "nj", form: "ST-50" },
    { date: iso(year, 1, 31), title: "W-2 / 1099-NEC to workers and IRS; NJ-W-3", category: "tax", jurisdiction: "federal+nj", form: "W-2, 1099-NEC, NJ-W-3" },
    { date: iso(year, 4, 15), title: "IRA / HSA contribution deadline (prior year)", category: "tax", jurisdiction: "federal", form: "" },
    { date: iso(year, 4, 20), title: "NJ sales tax ST-50 Q1", category: "tax", jurisdiction: "nj", form: "ST-50" },
    { date: iso(year, 7, 20), title: "NJ sales tax ST-50 Q2", category: "tax", jurisdiction: "nj", form: "ST-50" },
    { date: iso(year, 9, 15), title: "Extended business returns due", category: "tax", jurisdiction: "federal+nj", form: "" },
    { date: iso(year, 10, 15), title: "Extended 1040 + NJ-1040 due", category: "tax", jurisdiction: "federal+nj", form: "1040, NJ-1040" },
    { date: iso(year, 10, 20), title: "NJ sales tax ST-50 Q3", category: "tax", jurisdiction: "nj", form: "ST-50" },
    { date: iso(year, 12, 31), title: "Last day for deductible business purchases, Solo 401k setup, charitable gifts", category: "tax", jurisdiction: "federal+nj", form: "" },
    { date: iso(year, 12, 1), title: "Year-end tax planning review with " + (process.env.FINANCE_BOT_NAME || "Cato Ledger"), category: "planning", jurisdiction: "", form: "" },
  ];
}

/** Expand recurring bill-pay and invoice rules into dated events for a year. */
function recurringEvents(year, rules) {
  const out = [];
  for (const r of rules) {
    if (r.frequency === "monthly") {
      for (let m = 1; m <= 12; m++) {
        out.push({ date: iso(year, m, Math.min(r.dayOfMonth || 1, 28)), title: r.title, category: r.category, amount: r.amount || null, jurisdiction: "", form: "" });
      }
    } else if (r.frequency === "weekly") {
      const d = new Date(Date.UTC(year, 0, 1, 12));
      while (d.getUTCDay() !== (r.weekday == null ? 5 : r.weekday)) d.setUTCDate(d.getUTCDate() + 1);
      while (d.getUTCFullYear() === year) {
        out.push({ date: d.toISOString().slice(0, 10), title: r.title, category: r.category, amount: r.amount || null, jurisdiction: "", form: "" });
        d.setUTCDate(d.getUTCDate() + 7);
      }
    } else if (r.frequency === "quarterly") {
      for (const m of [1, 4, 7, 10]) {
        out.push({ date: iso(year, m, Math.min(r.dayOfMonth || 1, 28)), title: r.title, category: r.category, amount: r.amount || null, jurisdiction: "", form: "" });
      }
    } else if (r.frequency === "yearly") {
      out.push({ date: iso(year, r.month || 1, r.dayOfMonth || 1), title: r.title, category: r.category, amount: r.amount || null, jurisdiction: "", form: "" });
    }
  }
  return out;
}

const defaultRules = [
  { title: "Pay rent / mortgage", frequency: "monthly", dayOfMonth: 1, category: "bill" },
  { title: "Pay business credit card", frequency: "monthly", dayOfMonth: 20, category: "bill" },
  { title: "Pay utilities + internet", frequency: "monthly", dayOfMonth: 15, category: "bill" },
  { title: "Send wholesale / custom invoices", frequency: "monthly", dayOfMonth: 1, category: "invoice" },
  { title: "Chase unpaid invoices (net-30 check)", frequency: "monthly", dayOfMonth: 25, category: "invoice" },
  { title: "Reconcile bank + card, update inventory count", frequency: "weekly", weekday: 5, category: "bookkeeping" },
  { title: "Life insurance premium", frequency: "monthly", dayOfMonth: 5, category: "bill" },
  { title: "Review investment contributions + 529 for Brynlee", frequency: "quarterly", dayOfMonth: 10, category: "planning" },
  { title: "NJ annual report (LLC/corp) - due end of anniversary month", frequency: "yearly", month: Number(process.env.FINANCE_NJ_ANNIVERSARY_MONTH || 12), dayOfMonth: 28, category: "compliance" },
];

function buildYear(year, { entity, rules = defaultRules } = {}) {
  return [...taxDeadlines(year, entity), ...recurringEvents(year, rules)].sort((a, b) => a.date.localeCompare(b.date));
}

module.exports = { taxDeadlines, taxYearDeadlines, recurringEvents, defaultRules, buildYear, iso };
