// End-to-end smoke test against the real Express server on a temp SQLite DB.
const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("path");
const fs = require("fs");

const tmpDb = path.join(__dirname, "..", "..", "database", "test-" + process.pid + ".db3");
process.env.FINANCE_TEST_DB = tmpDb;
process.env.XAI_API_KEY = ""; // force offline reply

const knexfile = require("../../knexfile");
knexfile.development.connection.filename = tmpDb;

const server = require("../../api/server");
const db = require("../../database/dbConfig");

let base;
let srv;
let token;
const api = async (method, url, body) => {
  const res = await fetch(base + url, { method, headers: { "Content-Type": "application/json", Authorization: token || "" }, body: body ? JSON.stringify(body) : undefined });
  return { status: res.status, json: await res.json() };
};

test.before(async () => {
  await db.migrate.latest();
  srv = server.listen(0);
  base = "http://127.0.0.1:" + srv.address().port;
  await api("POST", "/api/auth/register", { username: "owner", password: "pw" });
  const login = await api("POST", "/api/auth/login", { username: "owner", password: "pw" });
  token = login.json.token;
  assert.ok(token);
});

test.after(async () => {
  srv.close();
  await db.destroy();
  fs.rmSync(tmpDb, { force: true });
});

test("finance routes require a token", async () => {
  const saved = token;
  token = "";
  const r = await api("GET", "/api/finance/persona");
  assert.equal(r.status, 401);
  token = saved;
});

test("persona reports bot name and connection state", async () => {
  const r = await api("GET", "/api/finance/persona");
  assert.equal(r.status, 200);
  assert.equal(r.json.name, "Cato Ledger");
  assert.equal(r.json.grokConnected, false);
});

test("calendar seed + list + complete", async () => {
  const seed = await api("POST", "/api/finance/calendar/seed/2026");
  assert.ok(seed.json.added > 80);
  const again = await api("POST", "/api/finance/calendar/seed/2026");
  assert.equal(again.json.added, 0, "re-seeding is idempotent");
  const list = await api("GET", "/api/finance/calendar?from=2026-04-01&to=2026-04-30&category=tax");
  assert.ok(list.json.some((e) => /1040/.test(e.form)));
  const done = await api("PATCH", "/api/finance/calendar/" + list.json[0].id, { status: "done" });
  assert.equal(done.json.status, "done");
});

test("accounts + transactions feed reports and HELOC sizing", async () => {
  await api("POST", "/api/finance/accounts", { name: "Biz checking", type: "checking", balance: 42000, is_business: true });
  await api("POST", "/api/finance/accounts", { name: "Mortgage", type: "mortgage", balance: -260000, rate: 0.0625, payment: 1900 });
  await api("POST", "/api/finance/accounts", { name: "Visa", type: "credit", balance: -12000, rate: 0.249, payment: 400 });
  await api("POST", "/api/finance/transactions", [
    { date: "2026-08-03", amount: 18000, category: "sales", description: "Shopify payout", is_business: true },
    { date: "2026-08-10", amount: -6000, category: "inventory", description: "Blanks + print run", is_business: true },
    { date: "2026-08-15", amount: -2500, category: "rent", description: "Studio", is_business: true },
    { date: "2026-09-03", amount: 21000, category: "sales", description: "Shopify payout", is_business: true },
    { date: "2026-09-10", amount: -7000, category: "inventory", description: "Blanks", is_business: true },
    { date: "2026-09-20", amount: -1200, category: "loan", description: "Term loan", is_business: true },
  ]);
  const rep = await api("GET", "/api/finance/reports/summary");
  assert.equal(rep.status, 200);
  assert.ok(rep.json.spendingPie.labels.includes("inventory"));
  assert.equal(rep.json.cashFlowBar.labels.length, 2);
  assert.ok(rep.json.cashLine.data.length === 2);
  assert.ok(rep.json.netWorth.totalLiabilities > 0);
  assert.ok(rep.json.business.grossMargin > 0);

  const heloc = await api("POST", "/api/finance/heloc", { homeValue: 450000, renovationBudget: 50000 });
  assert.equal(heloc.json.firstMortgageBalance, 260000);
  assert.equal(heloc.json.debtTotal, 12000);
  assert.ok(heloc.json.lenders.length > 0);
});

test("loan comparison, tax, insurance, readiness, pricing endpoints", async () => {
  const loans = await api("POST", "/api/finance/loans/compare", { amount: 250000, termMonths: 120 });
  assert.ok(loans.json.best);
  assert.ok(loans.json.best.firstYearMonthly < loans.json.best.afterIntroPayment || loans.json.best.structure === "standard");
  const tax = await api("POST", "/api/finance/tax/estimate", { filingStatus: "mfj", businessNetProfit: 90000, dependentsUnder17: 1 });
  assert.ok(tax.json.totalTax > 0);
  const ins = await api("POST", "/api/finance/insurance/needs", { annualIncome: 90000, mortgageBalance: 260000 });
  assert.ok(ins.json.recommendedFaceAmount > 0);
  const ready = await api("POST", "/api/finance/move-readiness", { moveCost: 15000, expectedMonthlyLiftRevenue: 6000 });
  assert.ok(["GO", "NOT YET", "NO"].includes(ready.json.verdict));
  const price = await api("POST", "/api/finance/pricing", { unitCost: 20, marketHigh: 55, marketLow: 32, units: 50 });
  assert.equal(price.json.listPrice, 55);
});

test("documents prepare to signature", async () => {
  const d = await api("POST", "/api/finance/documents/prepare", { kind: "sba_1919", data: { businessName: "STOiiiC FiT", loanAmount: 250000 } });
  assert.equal(d.status, 201);
  assert.equal(d.json.status, "draft");
  assert.ok(d.json.missing.includes("ein"));
  const list = await api("GET", "/api/finance/documents");
  assert.equal(list.json.length, 1);
});

test("credit pull without provider says what to connect; upload works", async () => {
  const pull = await api("POST", "/api/finance/credit/pull", { consent: true });
  assert.equal(pull.json.status, "not_connected");
  const up = await api("POST", "/api/finance/credit/upload", { bureau: "Experian", score: 742, report: { utilization: 0.42 } });
  assert.equal(up.status, 201);
  assert.equal(up.json.analysis.tier, "very good");
  assert.ok(up.json.analysis.tips[0].includes("30%"));
});

test("chat answers offline with the bot name and stores history", async () => {
  const r = await api("POST", "/api/finance/chat", { message: "What is due this month?" });
  assert.equal(r.status, 200);
  assert.equal(r.json.offline, true);
  assert.match(r.json.reply, /Cato Ledger/);
  const msgs = await api("GET", "/api/finance/messages");
  assert.equal(msgs.json.length, 2);
});

test("direct tool call runs the readiness tool", async () => {
  const r = await api("POST", "/api/finance/tools/get_upcoming_events", { days: 400 });
  assert.ok(Array.isArray(r.json) && r.json.length > 0);
});
