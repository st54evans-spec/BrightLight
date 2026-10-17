const test = require("node:test");
const assert = require("node:assert/strict");
const calc = require("../calculators");
const { businessLenders } = require("../lenders");

test("monthlyPayment matches a known mortgage figure", () => {
  // $200k, 6%, 30y -> $1,199.10
  assert.equal(Math.round(calc.monthlyPayment(200000, 0.06, 360) * 100) / 100, 1199.1);
});

test("amortize standard pays off to zero and interest-only year one is cheaper up front", () => {
  const std = calc.amortize({ principal: 250000, annualRate: 0.095, termMonths: 120 });
  assert.equal(std.schedule[119].balance, 0);
  assert.ok(std.totalInterest > 0);
  const io = calc.amortize({ principal: 250000, annualRate: 0.095, termMonths: 120, structure: "interest_only", introMonths: 12 });
  assert.ok(io.firstYearOutlay < std.firstYearOutlay, "interest-only year one should cost less cash");
  assert.ok(io.totalInterest > std.totalInterest, "but more interest over the life");
  assert.equal(io.schedule[119].balance, 0);
  assert.equal(io.firstYearMonthly, Math.round(((250000 * 0.095) / 12) * 100) / 100);
});

test("stepped structure accrues shortfall and still pays off", () => {
  const s = calc.amortize({ principal: 100000, annualRate: 0.08, termMonths: 60, structure: "stepped", introMonths: 12, introPaymentPct: 0.5 });
  assert.ok(s.schedule[11].balance > 100000 * 0.9, "balance barely moves in year one");
  assert.equal(s.schedule[59].balance, 0);
});

test("compareLoans ranks and respects max amount", () => {
  const r = calc.compareLoans({ amount: 300000, termMonths: 120, lenders: businessLenders });
  assert.ok(r.ranked.length >= 3);
  assert.ok(r.best.score >= r.ranked[r.ranked.length - 1].score);
  assert.ok(r.ranked.every((l) => l.maxAmount >= 300000));
  const big = calc.compareLoans({ amount: 10000000, termMonths: 120, lenders: businessLenders });
  assert.equal(big.ranked.length, 0);
});

test("helocRefinance sizes line, flags shortfall, compares blended rate", () => {
  const ok = calc.helocRefinance({
    homeValue: 500000,
    firstMortgageBalance: 250000,
    debts: [
      { name: "Visa", balance: 15000, rate: 0.24, payment: 450 },
      { name: "Auto", balance: 20000, rate: 0.07, payment: 400 },
    ],
    renovationBudget: 60000,
    helocRate: 0.0675,
  });
  assert.equal(ok.needed, 95000);
  assert.equal(ok.maxLine, 175000);
  assert.equal(ok.lineSize, 95000);
  assert.equal(ok.shortfall, 0);
  assert.ok(ok.weightedDebtRate > ok.helocRate);
  assert.match(ok.verdict, /Proceed/);
  const short = calc.helocRefinance({ homeValue: 300000, firstMortgageBalance: 240000, debts: [{ name: "x", balance: 30000, rate: 0.2 }], renovationBudget: 50000 });
  assert.ok(short.shortfall > 0);
  assert.match(short.verdict, /Short/);
});

test("taxEstimate: MFJ family with Schedule C profit", () => {
  const t = calc.taxEstimate({ filingStatus: "mfj", w2Wages: 60000, businessNetProfit: 80000, dependentsUnder17: 1 });
  assert.ok(t.federal.selfEmploymentTax > 11000 && t.federal.selfEmploymentTax < 11400);
  assert.ok(t.federal.qbiDeduction > 0);
  assert.equal(t.federal.deductionUsed, 32200);
  assert.ok(t.nj.tax > 0);
  assert.equal(t.nj.exemptions, 3500);
  assert.ok(t.federal.totalTax > t.nj.tax);
  assert.ok(t.quarterlyEstimate > 0);
  const zero = calc.taxEstimate({ filingStatus: "single" });
  assert.equal(zero.totalTax, 0);
});

test("lifeInsuranceNeeds rounds up to 50k", () => {
  const n = calc.lifeInsuranceNeeds({ debts: 20000, annualIncome: 90000, yearsToReplace: 15, mortgageBalance: 250000, children: 1, existingCoverage: 100000 });
  assert.equal(n.totalNeed, 20000 + 1350000 + 250000 + 120000 + 15000);
  assert.equal(n.recommendedFaceAmount % 50000, 0);
  assert.ok(n.recommendedFaceAmount >= n.gap);
});

test("retirement and education projections compute gaps", () => {
  const r = calc.retirementProjection({ currentAge: 35, retireAge: 65, currentSavings: 50000, monthlyContribution: 500 });
  assert.ok(r.projectedNominal > 500000);
  assert.ok(r.path.length > 2);
  assert.ok(r.extraMonthlyNeeded >= 0);
  const e = calc.educationProjection({ childAge: 3, monthlyContribution: 200 });
  assert.equal(e.years, 15);
  assert.ok(e.targetAtStart > 120000);
});

test("moveReadiness gives GO when numbers back it and NO when they do not", () => {
  const go = calc.moveReadiness({ cash: 80000, monthlyRevenue: 40000, monthlyCOGS: 16000, monthlyOpex: 12000, monthlyDebtService: 3000, moveCost: 25000, expectedMonthlyLiftRevenue: 10000 });
  assert.equal(go.verdict, "GO");
  const no = calc.moveReadiness({ cash: 5000, monthlyRevenue: 8000, monthlyCOGS: 6000, monthlyOpex: 4000, monthlyDebtService: 1000, moveCost: 20000, expectedMonthlyLiftRevenue: 1000 });
  assert.equal(no.verdict, "NO");
  assert.ok(no.whatWouldMakeItGo.length >= 3);
});

test("unit economics: break-even, a cheaper price, and marketing saturation", () => {
  const base = calc.unitEconomics({ price: 40, unitCost: 18, fixedCosts: 2200, units: 200 });
  assert.equal(base.contributionMarginPerUnit, 22);
  assert.equal(base.breakEvenUnits, 100);
  assert.equal(base.breakEvenRevenue, 4000);
  assert.equal(base.profit, 2200);
  assert.ok(base.explanation.some((line) => /contribution margin/.test(line)));

  const cut = calc.unitEconomics({ price: 40, unitCost: 18, fixedCosts: 2200, units: 200, alternatePrice: 32, alternateUnits: 300 });
  assert.equal(cut.priceCut.contributionMarginPerUnit, 14);
  assert.equal(cut.priceCut.unitsToMatchCurrentProfit, 314.29);
  assert.equal(cut.priceCut.paysOff, false);
  const enough = calc.unitEconomics({ price: 40, unitCost: 18, fixedCosts: 2200, units: 200, alternatePrice: 32, alternateUnits: 320 });
  assert.equal(enough.priceCut.paysOff, true);

  const ads = calc.unitEconomics({
    price: 40,
    unitCost: 18,
    fixedCosts: 2200,
    marketingSpend: 500,
    saturationUnits: 100,
    saturationSpend: 500,
  });
  const extra = 100 * (1 - Math.exp(-1));
  assert.equal(ads.marketing.extraUnitsAtSpend, Math.round(extra * 100) / 100);
  assert.equal(ads.marketing.paysOff, extra * 22 >= 500);
  assert.ok(ads.marketing.spendWhereNextDollarStopsPaying > 500);
  assert.equal(calc.unitEconomics({ price: 10, unitCost: 12 }).ok, false);
});

test("pricingPlan never drops below floor and starts at list", () => {
  const p = calc.pricingPlan({ unitCost: 18, marketLow: 30, marketHigh: 48, units: 40, mustSellByDays: 30 });
  assert.equal(p.listPrice, 48);
  assert.equal(p.floorPrice, 30);
  assert.equal(p.dropSchedule[0].price, 48);
  assert.ok(p.dropSchedule.every((s) => s.price >= 30));
});
