// Pure math. No I/O. Every tool the bot can call lives here so it is testable.
const { FEDERAL, NJ, taxFromBrackets } = require("./taxTables");

const round = (n, d = 2) => Math.round(n * 10 ** d) / 10 ** d;

// ---------- Loans ----------

function monthlyPayment(principal, annualRate, months) {
  const r = annualRate / 12;
  if (months <= 0) return principal;
  if (r === 0) return principal / months;
  return (principal * r) / (1 - Math.pow(1 + r, -months));
}

/**
 * Amortization with optional interest-only or stepped first year.
 * structure: "standard" | "interest_only" | "stepped"
 *  - interest_only: pay interest only for `introMonths`, then amortize remainder.
 *  - stepped: pay `introPaymentPct` of the full payment for `introMonths` (shortfall accrues to principal), then amortize.
 */
function amortize({
  principal,
  annualRate,
  termMonths,
  structure = "standard",
  introMonths = 0,
  introPaymentPct = 0.5,
  originationFeePct = 0,
}) {
  const r = annualRate / 12;
  let balance = principal;
  const schedule = [];
  const fullPayment = monthlyPayment(principal, annualRate, termMonths);
  let totalInterest = 0;
  let firstYearOutlay = 0;
  let remainingPayment = null;

  for (let m = 1; m <= termMonths; m++) {
    const interest = balance * r;
    let payment;
    if (structure === "interest_only" && m <= introMonths) {
      payment = interest;
    } else if (structure === "stepped" && m <= introMonths) {
      payment = fullPayment * introPaymentPct;
    } else {
      if (remainingPayment === null) {
        remainingPayment = monthlyPayment(balance, annualRate, termMonths - m + 1);
      }
      payment = Math.min(remainingPayment, balance + interest);
    }
    const principalPaid = payment - interest;
    balance = balance - principalPaid;
    totalInterest += interest;
    if (m <= 12) firstYearOutlay += payment;
    schedule.push({
      month: m,
      payment: round(payment),
      interest: round(interest),
      principal: round(principalPaid),
      balance: round(Math.max(balance, 0)),
    });
  }
  const fees = principal * originationFeePct;
  return {
    principal,
    annualRate,
    termMonths,
    structure,
    introMonths,
    fullPayment: round(fullPayment),
    firstYearMonthly: round(firstYearOutlay / 12),
    firstYearOutlay: round(firstYearOutlay),
    afterIntroPayment: round(remainingPayment || fullPayment),
    totalInterest: round(totalInterest),
    originationFees: round(fees),
    totalCost: round(totalInterest + fees),
    schedule,
  };
}

/**
 * Rank lenders for: high value, low first-year payments, best total interest.
 * weights can be tuned; defaults favor year-one cash flow then total cost.
 */
function compareLoans({ amount, termMonths, lenders, weights = { firstYear: 0.5, totalCost: 0.35, maxAmount: 0.15 } }) {
  const rows = lenders
    .filter((l) => amount <= l.maxAmount && amount >= (l.minAmount || 0))
    .map((l) => {
      const term = Math.min(termMonths, l.maxTermMonths);
      const a = amortize({
        principal: amount,
        annualRate: l.rate,
        termMonths: term,
        structure: l.structure || "standard",
        introMonths: l.introMonths || 0,
        introPaymentPct: l.introPaymentPct || 0.5,
        originationFeePct: l.originationFeePct || 0,
      });
      return {
        lender: l.name,
        product: l.product,
        rate: l.rate,
        rateNote: l.rateNote,
        termMonths: term,
        maxAmount: l.maxAmount,
        structure: a.structure,
        firstYearMonthly: a.firstYearMonthly,
        firstYearOutlay: a.firstYearOutlay,
        afterIntroPayment: a.afterIntroPayment,
        totalInterest: a.totalInterest,
        totalCost: a.totalCost,
        requirements: l.requirements,
        url: l.url,
      };
    });
  if (!rows.length) return { amount, termMonths, ranked: [], note: "No lender in the catalog covers this amount." };
  const min = (k) => Math.min(...rows.map((r) => r[k]));
  const max = (k) => Math.max(...rows.map((r) => r[k]));
  const norm = (v, lo, hi) => (hi === lo ? 1 : 1 - (v - lo) / (hi - lo));
  rows.forEach((r) => {
    r.score = round(
      100 *
        (weights.firstYear * norm(r.firstYearOutlay, min("firstYearOutlay"), max("firstYearOutlay")) +
          weights.totalCost * norm(r.totalCost, min("totalCost"), max("totalCost")) +
          weights.maxAmount * (1 - norm(r.maxAmount, min("maxAmount"), max("maxAmount")))),
      1
    );
  });
  rows.sort((a, b) => b.score - a.score);
  return { amount, termMonths, ranked: rows, best: rows[0] };
}

// ---------- HELOC ----------

function helocRefinance({
  homeValue,
  firstMortgageBalance = 0,
  debts = [], // [{name, balance, rate, payment}]
  renovationBudget = 0,
  helocRate = 0.0675,
  drawMonths = 120,
  repayMonths = 240,
  maxCLTV = 0.85,
  closingCosts = 0,
}) {
  const debtTotal = debts.reduce((s, d) => s + d.balance, 0);
  const currentDebtPayments = debts.reduce((s, d) => s + (d.payment || 0), 0);
  const weightedDebtRate = debtTotal ? debts.reduce((s, d) => s + d.balance * d.rate, 0) / debtTotal : 0;
  const needed = debtTotal + renovationBudget + closingCosts;
  const maxLine = Math.max(homeValue * maxCLTV - firstMortgageBalance, 0);
  const lineSize = Math.min(needed, maxLine);
  const shortfall = Math.max(needed - maxLine, 0);
  const cltv = homeValue ? (firstMortgageBalance + lineSize) / homeValue : 0;
  const interestOnlyPayment = (lineSize * helocRate) / 12;
  const repayPayment = monthlyPayment(lineSize, helocRate, repayMonths);
  const interestOnlyTotal = interestOnlyPayment * drawMonths;
  const repay = amortize({ principal: lineSize, annualRate: helocRate, termMonths: repayMonths });
  return {
    homeValue,
    firstMortgageBalance,
    debtTotal: round(debtTotal),
    weightedDebtRate: round(weightedDebtRate, 4),
    currentDebtPayments: round(currentDebtPayments),
    renovationBudget,
    needed: round(needed),
    maxLine: round(maxLine),
    lineSize: round(lineSize),
    shortfall: round(shortfall),
    cltv: round(cltv, 3),
    helocRate,
    interestOnlyPayment: round(interestOnlyPayment),
    monthlyCashFlowChange: round(currentDebtPayments - interestOnlyPayment),
    repayPayment: round(repayPayment),
    interestDuringDraw: round(interestOnlyTotal),
    interestDuringRepay: repay.totalInterest,
    totalInterestIfHeldFull: round(interestOnlyTotal + repay.totalInterest),
    verdict:
      shortfall > 0
        ? `Line covers ${round((lineSize / needed) * 100, 1)}% of need. Short ${round(shortfall)} at ${maxCLTV * 100}% CLTV.`
        : helocRate < weightedDebtRate
        ? "Covers all debt and renovation at a lower blended rate. Proceed to lender quotes."
        : "Covers the need but the HELOC rate is not below the debt it replaces. Only worth it for the renovation cash or payment relief.",
  };
}

// ---------- Taxes ----------

function taxEstimate({
  year = 2026,
  filingStatus = "mfj",
  w2Wages = 0,
  businessNetProfit = 0,
  otherIncome = 0,
  dependentsUnder17 = 0,
  otherDependents = 0,
  itemizedDeductions = 0,
  federalWithheld = 0,
  njWithheld = 0,
  estimatesPaid = 0,
}) {
  const F = FEDERAL[year] || FEDERAL[2026];
  const seTaxBase = businessNetProfit * 0.9235;
  const seTax =
    businessNetProfit > 0
      ? Math.min(seTaxBase, F.ssWageBase) * 0.124 + seTaxBase * F.medicareRate
      : 0;
  const halfSE = seTax / 2;
  const agi = w2Wages + businessNetProfit + otherIncome - halfSE;
  const qbi = Math.max(businessNetProfit - halfSE, 0) * F.qbiDeductionRate;
  const deduction = Math.max(F.standardDeduction[filingStatus], itemizedDeductions);
  const taxable = Math.max(agi - deduction - qbi, 0);
  const incomeTax = taxFromBrackets(taxable, F.brackets[filingStatus]);
  const ctc = dependentsUnder17 * F.childTaxCredit + otherDependents * 500;
  const federalTax = Math.max(incomeTax - ctc, 0) + seTax;
  const federalDue = federalTax - federalWithheld - estimatesPaid;

  const njGross = w2Wages + businessNetProfit + otherIncome;
  const njExemptions =
    NJ.exemptions.personal * (filingStatus === "mfj" ? 2 : 1) +
    NJ.exemptions.dependent * (dependentsUnder17 + otherDependents);
  const njTaxable = Math.max(njGross - njExemptions, 0);
  const njTax = taxFromBrackets(njTaxable, NJ.brackets[filingStatus]);
  const njDue = njTax - njWithheld;

  const totalTax = federalTax + njTax;
  return {
    year,
    filingStatus,
    federal: {
      agi: round(agi),
      selfEmploymentTax: round(seTax),
      deductionUsed: round(deduction),
      qbiDeduction: round(qbi),
      taxableIncome: round(taxable),
      incomeTax: round(incomeTax),
      credits: round(ctc),
      totalTax: round(federalTax),
      balanceDue: round(federalDue),
      effectiveRate: njGross ? round(federalTax / njGross, 4) : 0,
    },
    nj: {
      grossIncome: round(njGross),
      exemptions: njExemptions,
      taxableIncome: round(njTaxable),
      tax: round(njTax),
      balanceDue: round(njDue),
    },
    totalTax: round(totalTax),
    quarterlyEstimate: round(Math.max(federalTax - federalWithheld, 0) / 4),
    njQuarterlyEstimate: round(Math.max(njTax - njWithheld, 0) / 4),
    note: "Estimate only. Tables are for tax year " + year + "; have a CPA/EA review before filing.",
  };
}

// ---------- Insurance ----------

/** DIME method: Debt + Income replacement + Mortgage + Education, less existing coverage/assets. */
function lifeInsuranceNeeds({
  debts = 0,
  annualIncome = 0,
  yearsToReplace = 15,
  mortgageBalance = 0,
  educationPerChild = 120000,
  children = 1,
  finalExpenses = 15000,
  existingCoverage = 0,
  liquidAssets = 0,
}) {
  const need =
    debts + annualIncome * yearsToReplace + mortgageBalance + educationPerChild * children + finalExpenses;
  const gap = Math.max(need - existingCoverage - liquidAssets, 0);
  const recommended = Math.ceil(gap / 50000) * 50000;
  return {
    breakdown: {
      debts,
      incomeReplacement: annualIncome * yearsToReplace,
      mortgage: mortgageBalance,
      education: educationPerChild * children,
      finalExpenses,
    },
    totalNeed: round(need),
    existingCoverage,
    liquidAssets,
    gap: round(gap),
    recommendedFaceAmount: recommended,
    suggestedTerm: Math.max(yearsToReplace, 20),
    guidance: [
      "Term life covers the gap cheapest; a 20 or 30 year level term is the default.",
      "Buy from a carrier rated A or better (AM Best).",
      "Check: convertible to permanent, no exclusion for the business, and a waiver of premium rider.",
      "Business: consider key-person coverage and a buy-sell policy if there is a partner.",
      "Whole/universal life only makes sense once retirement accounts are maxed and the goal is estate or cash value.",
    ],
  };
}

// ---------- Investing / goals ----------

function futureValue({ present = 0, monthly = 0, annualReturn = 0.07, years = 20 }) {
  const r = annualReturn / 12;
  const n = years * 12;
  const fvLump = present * Math.pow(1 + r, n);
  const fvSeries = r === 0 ? monthly * n : monthly * ((Math.pow(1 + r, n) - 1) / r);
  return fvLump + fvSeries;
}

function retirementProjection({
  currentAge,
  retireAge = 65,
  currentSavings = 0,
  monthlyContribution = 0,
  annualReturn = 0.07,
  inflation = 0.03,
  desiredAnnualIncome = 80000,
  withdrawalRate = 0.04,
}) {
  const years = Math.max(retireAge - currentAge, 0);
  const nominal = futureValue({ present: currentSavings, monthly: monthlyContribution, annualReturn, years });
  const real = nominal / Math.pow(1 + inflation, years);
  const targetNominal = (desiredAnnualIncome * Math.pow(1 + inflation, years)) / withdrawalRate;
  const gap = Math.max(targetNominal - nominal, 0);
  // Solve monthly needed for the gap.
  const r = annualReturn / 12;
  const n = years * 12;
  const extraMonthly = n && r ? gap / ((Math.pow(1 + r, n) - 1) / r) : 0;
  const path = [];
  for (let y = 0; y <= years; y += Math.max(1, Math.floor(years / 10) || 1)) {
    path.push({ age: currentAge + y, balance: round(futureValue({ present: currentSavings, monthly: monthlyContribution, annualReturn, years: y })) });
  }
  return {
    yearsToRetire: years,
    projectedNominal: round(nominal),
    projectedInTodaysDollars: round(real),
    targetNominal: round(targetNominal),
    gap: round(gap),
    extraMonthlyNeeded: round(extraMonthly),
    sustainableIncomeTodaysDollars: round(real * withdrawalRate),
    path,
    allocationIdea:
      years > 20
        ? "90/10 stocks/bonds, broad index funds, max tax-advantaged accounts (Solo 401k/SEP for the business, Roth IRA)."
        : years > 10
        ? "75/25 stocks/bonds, shift 1% a year toward bonds."
        : "60/40, build a 2 year cash cushion before retirement.",
  };
}

function educationProjection({ childAge = 0, startAge = 18, currentSavings = 0, monthlyContribution = 0, annualReturn = 0.06, targetToday = 120000, costInflation = 0.05 }) {
  const years = Math.max(startAge - childAge, 0);
  const projected = futureValue({ present: currentSavings, monthly: monthlyContribution, annualReturn, years });
  const target = targetToday * Math.pow(1 + costInflation, years);
  const gap = Math.max(target - projected, 0);
  const r = annualReturn / 12;
  const n = years * 12;
  const extraMonthly = n && r ? gap / ((Math.pow(1 + r, n) - 1) / r) : 0;
  return {
    years,
    projected: round(projected),
    targetAtStart: round(target),
    gap: round(gap),
    extraMonthlyNeeded: round(extraMonthly),
    vehicle: "NJBEST 529 (NJ plan) or any low-cost 529; NJ allows a deduction up to $10,000 for income under $200,000.",
  };
}

// ---------- STOiiiC FiT move readiness ----------

/**
 * Can the financials back a move? Looks at runway, gross margin, debt coverage, and the payback of the move.
 */
function moveReadiness({
  cash = 0,
  monthlyRevenue = 0,
  monthlyCOGS = 0,
  monthlyOpex = 0,
  monthlyDebtService = 0,
  moveCost = 0,
  expectedMonthlyLiftRevenue = 0,
  liftMarginPct = null,
  rampMonths = 3,
  minRunwayMonths = 6,
}) {
  const grossMargin = monthlyRevenue ? (monthlyRevenue - monthlyCOGS) / monthlyRevenue : 0;
  const operatingCash = monthlyRevenue - monthlyCOGS - monthlyOpex;
  const freeCash = operatingCash - monthlyDebtService;
  const burn = freeCash < 0 ? -freeCash : 0;
  const runway = burn ? cash / burn : Infinity;
  const dscr = monthlyDebtService ? operatingCash / monthlyDebtService : Infinity;
  const liftMargin = liftMarginPct == null ? grossMargin : liftMarginPct;
  const monthlyLiftProfit = expectedMonthlyLiftRevenue * liftMargin;
  const cashAfterMove = cash - moveCost;
  const runwayAfterMove = burn ? cashAfterMove / burn : Infinity;
  const paybackMonths = monthlyLiftProfit > 0 ? rampMonths + moveCost / monthlyLiftProfit : Infinity;

  const checks = [
    { name: "Gross margin >= 45%", pass: grossMargin >= 0.45, value: round(grossMargin * 100, 1) + "%" },
    { name: `Runway after move >= ${minRunwayMonths} mo`, pass: runwayAfterMove >= minRunwayMonths, value: Number.isFinite(runwayAfterMove) ? round(runwayAfterMove, 1) + " mo" : "cash-flow positive" },
    { name: "DSCR >= 1.25", pass: dscr >= 1.25, value: Number.isFinite(dscr) ? round(dscr, 2) : "no debt" },
    { name: "Payback <= 12 mo", pass: paybackMonths <= 12, value: Number.isFinite(paybackMonths) ? round(paybackMonths, 1) + " mo" : "never" },
    { name: "Cash after move > 0", pass: cashAfterMove > 0, value: round(cashAfterMove) },
  ];
  const passed = checks.filter((c) => c.pass).length;
  const verdict = passed === checks.length ? "GO" : passed >= 3 ? "NOT YET" : "NO";
  return {
    grossMargin: round(grossMargin, 3),
    operatingCash: round(operatingCash),
    freeCash: round(freeCash),
    runwayMonths: Number.isFinite(runway) ? round(runway, 1) : null,
    dscr: Number.isFinite(dscr) ? round(dscr, 2) : null,
    cashAfterMove: round(cashAfterMove),
    runwayAfterMove: Number.isFinite(runwayAfterMove) ? round(runwayAfterMove, 1) : null,
    monthlyLiftProfit: round(monthlyLiftProfit),
    paybackMonths: Number.isFinite(paybackMonths) ? round(paybackMonths, 1) : null,
    checks,
    verdict,
    whatWouldMakeItGo: checks.filter((c) => !c.pass).map((c) => c.name),
  };
}

// ---------- Top dollar pricing ----------

function pricingPlan({ unitCost = 0, targetMarginPct = 0.55, marketLow = null, marketHigh = null, units = 1, mustSellByDays = 30, fees = 0.03 }) {
  const list = marketHigh != null ? marketHigh : unitCost / (1 - targetMarginPct);
  const breakEven = unitCost / (1 - fees);
  const floor = Math.max(marketLow != null ? marketLow : unitCost / (1 - 0.25), breakEven);
  const steps = 3;
  const schedule = [];
  for (let i = 0; i < steps; i++) {
    const day = Math.round((mustSellByDays / steps) * i);
    const price = list - ((list - floor) / (steps - 1)) * i;
    schedule.push({ day, price: round(price), marginPct: round((price * (1 - fees) - unitCost) / price, 3) });
  }
  return {
    unitCost,
    listPrice: round(list),
    floorPrice: round(floor),
    breakEven: round(breakEven),
    revenueAtList: round(list * units),
    revenueAtFloor: round(floor * units),
    dropSchedule: schedule,
    plays: [
      "List at the top of the market comps, with the story (memento mori, Philly) in the listing.",
      "Bundle slow movers with best sellers before dropping price.",
      "Drop on the schedule, not on feel. Never below floor.",
      "Email list and local pickup first; marketplaces last (fees).",
    ],
  };
}

module.exports = {
  monthlyPayment,
  amortize,
  compareLoans,
  helocRefinance,
  taxEstimate,
  lifeInsuranceNeeds,
  futureValue,
  retirementProjection,
  educationProjection,
  moveReadiness,
  pricingPlan,
};
