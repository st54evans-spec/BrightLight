const router = require("express").Router();
const authenticate = require("../auth/authenticate-middleware");
const models = require("./models");
const reports = require("./reports");
const calc = require("./calculators");
const calendar = require("./calendar");
const grok = require("./grok");
const tools = require("./tools");
const forms = require("./integrations/forms");
const credit = require("./integrations/credit");
const plaid = require("./integrations/plaid");
const { businessLenders, helocLenders, PRIME } = require("./lenders");
const { BOT_NAME, BOT_TITLE, profile } = require("./persona");

router.use(authenticate);

const wrap = (fn) => (req, res) =>
  Promise.resolve(fn(req, res)).catch((err) => res.status(err.status || 500).json({ message: err.message }));
const uid = (req) => req.user.id;

// ---- persona / status ----
router.get("/persona", (req, res) =>
  res.json({ name: BOT_NAME, title: BOT_TITLE, profile, grokConnected: grok.configured(), model: grok.MODEL, plaidConnected: plaid.configured(), creditConnected: credit.configured() })
);

// ---- chat ----
router.get("/messages", wrap(async (req, res) => res.json(await models.listMessages(uid(req), Number(req.query.limit) || 40))));
router.delete("/messages", wrap(async (req, res) => res.json({ deleted: await models.clearMessages(uid(req)) })));
router.post(
  "/chat",
  wrap(async (req, res) => {
    const { message } = req.body || {};
    if (!message || !message.trim()) return res.status(400).json({ message: "message is required" });
    const userId = uid(req);
    const history = (await models.listMessages(userId, 30)).filter((m) => m.role !== "tool").map((m) => ({ role: m.role, content: m.content }));
    const prof = await models.getProfile(userId);
    await models.addMessage(userId, "user", message);
    const out = await grok.chat({ history, message, ctx: { userId }, notes: Object.keys(prof).length ? "Owner profile facts: " + JSON.stringify(prof) : "" });
    const saved = await models.addMessage(userId, "assistant", out.reply, { toolCalls: out.toolCalls.map((t) => ({ name: t.name, args: t.args })), citations: out.citations, offline: !!out.offline });
    res.json({ ...out, id: saved.id, bot: BOT_NAME });
  })
);
// Direct tool call (no LLM) for the dashboard.
router.post("/tools/:name", wrap(async (req, res) => res.json(await tools.run(req.params.name, req.body || {}, { userId: uid(req) }))));
router.get("/tools", (req, res) => res.json(tools.openAiToolDefs().map((t) => ({ name: t.function.name, description: t.function.description }))));

// ---- profile ----
router.get("/profile", wrap(async (req, res) => res.json(await models.getProfile(uid(req)))));
router.put("/profile", wrap(async (req, res) => res.json(await models.saveProfile(uid(req), req.body || {}))));

// ---- calendar ----
router.get("/calendar", wrap(async (req, res) => res.json(await models.listEvents(uid(req), req.query))));
router.post("/calendar", wrap(async (req, res) => res.status(201).json(await models.addEvent(uid(req), req.body))));
router.patch("/calendar/:id", wrap(async (req, res) => res.json(await models.updateEvent(uid(req), req.params.id, req.body))));
router.delete("/calendar/:id", wrap(async (req, res) => res.json({ deleted: await models.deleteEvent(uid(req), req.params.id) })));
router.post(
  "/calendar/seed/:year",
  wrap(async (req, res) => {
    const year = Number(req.params.year);
    const prof = await models.getProfile(uid(req));
    const events = calendar.buildYear(year, { entity: prof.entity, rules: req.body && req.body.rules }).map((e) => ({ ...e, source: "seed" }));
    res.json({ year, added: await models.addEvents(uid(req), events) });
  })
);
router.get("/calendar/preview/:year", (req, res) => res.json(calendar.buildYear(Number(req.params.year), { entity: req.query.entity })));

// ---- accounts / transactions ----
router.get("/accounts", wrap(async (req, res) => res.json(await models.listAccounts(uid(req)))));
router.post("/accounts", wrap(async (req, res) => res.status(201).json(await models.addAccount(uid(req), req.body))));
router.patch("/accounts/:id", wrap(async (req, res) => res.json(await models.updateAccount(uid(req), req.params.id, req.body))));
router.delete("/accounts/:id", wrap(async (req, res) => res.json({ deleted: await models.deleteAccount(uid(req), req.params.id) })));
router.get("/transactions", wrap(async (req, res) => res.json(await models.listTransactions(uid(req), req.query))));
router.post(
  "/transactions",
  wrap(async (req, res) => {
    if (Array.isArray(req.body)) return res.status(201).json({ added: await models.addTransactions(uid(req), req.body) });
    res.status(201).json(await models.addTransaction(uid(req), req.body));
  })
);

// ---- goals ----
router.get("/goals", wrap(async (req, res) => res.json(await models.listGoals(uid(req)))));
router.post("/goals", wrap(async (req, res) => res.status(201).json(await models.addGoal(uid(req), req.body))));
router.patch("/goals/:id", wrap(async (req, res) => res.json(await models.updateGoal(uid(req), req.params.id, req.body))));

// ---- reports (pie / line / bar) ----
router.get(
  "/reports/summary",
  wrap(async (req, res) => {
    const accounts = await models.listAccounts(uid(req));
    const transactions = await models.listTransactions(uid(req), req.query);
    res.json(reports.summary({ accounts, transactions }));
  })
);

// ---- lending ----
router.get("/lenders", (req, res) => res.json({ prime: PRIME, business: businessLenders, heloc: helocLenders }));
router.post("/loans/compare", (req, res) => {
  const { amount, termMonths = 120, customLenders = [] } = req.body || {};
  if (!amount) return res.status(400).json({ message: "amount is required" });
  res.json(calc.compareLoans({ amount: Number(amount), termMonths: Number(termMonths), lenders: [...businessLenders, ...customLenders] }));
});
router.post("/loans/amortize", (req, res) => res.json(calc.amortize(req.body)));
router.post("/heloc", wrap(async (req, res) => res.json(await tools.run("heloc_refinance", req.body, { userId: uid(req) }))));

// ---- planning calculators ----
router.post("/tax/estimate", (req, res) => res.json(calc.taxEstimate(req.body || {})));
router.post("/insurance/needs", (req, res) => res.json(calc.lifeInsuranceNeeds(req.body || {})));
router.post("/retirement", (req, res) => {
  if (req.body == null || req.body.currentAge == null) return res.status(400).json({ message: "currentAge is required" });
  res.json(calc.retirementProjection(req.body));
});
router.post("/education", (req, res) => res.json(calc.educationProjection(req.body || {})));
router.post("/move-readiness", wrap(async (req, res) => res.json(await tools.run("move_readiness", req.body, { userId: uid(req) }))));
router.post("/pricing", (req, res) => res.json(calc.pricingPlan(req.body || {})));

// ---- documents (to the signature line) ----
router.get("/documents/templates", (req, res) => res.json(Object.entries(forms.TEMPLATES).map(([kind, t]) => ({ kind, title: t.title, fields: t.fields, signatures: t.signatures }))));
router.get("/documents", wrap(async (req, res) => res.json(await models.listDocuments(uid(req)))));
router.get("/documents/:id", wrap(async (req, res) => res.json((await models.getDocument(uid(req), req.params.id)) || { message: "not found" })));
router.post(
  "/documents/prepare",
  wrap(async (req, res) => {
    const { kind, data } = req.body || {};
    const prepared = forms.prepare(kind, data || {});
    const doc = await models.addDocument(uid(req), prepared);
    res.status(201).json({ ...prepared, id: doc.id });
  })
);
router.patch(
  "/documents/:id",
  wrap(async (req, res) => {
    const doc = await models.getDocument(uid(req), req.params.id);
    if (!doc) return res.status(404).json({ message: "not found" });
    const merged = forms.prepare(doc.kind, { ...doc.fields, ...(req.body.fields || {}) });
    const status = req.body.status || merged.status;
    res.json(await models.updateDocument(uid(req), doc.id, { fields: merged.fields, missing: merged.missing, status }));
  })
);
// Fill an AcroForm PDF: body { pdfBase64, fieldMap } -> { pdfBase64, filled, notFound, availableFields }
router.post(
  "/documents/:id/fill-pdf",
  wrap(async (req, res) => {
    const doc = await models.getDocument(uid(req), req.params.id);
    if (!doc) return res.status(404).json({ message: "not found" });
    const { pdfBase64, fieldMap } = req.body || {};
    if (!pdfBase64) return res.status(400).json({ message: "pdfBase64 is required" });
    const out = await forms.fillPdf(Buffer.from(pdfBase64, "base64"), fieldMap || doc.fields);
    res.json({ pdfBase64: Buffer.from(out.bytes).toString("base64"), filled: out.filled, notFound: out.notFound, availableFields: out.availableFields, signaturesLeft: doc.signatures });
  })
);

// ---- credit ----
router.get("/credit", wrap(async (req, res) => res.json(await models.listCreditReports(uid(req)))));
router.post("/credit/pull", wrap(async (req, res) => res.json(await tools.run("pull_credit_report", req.body, { userId: uid(req) }))));
router.post(
  "/credit/upload",
  wrap(async (req, res) => {
    const { bureau, score, report } = req.body || {};
    const row = await models.addCreditReport(uid(req), { bureau, score, consent: true, data: report || {} });
    res.status(201).json({ ...row, analysis: credit.analyze({ score, ...(report || {}) }) });
  })
);

// ---- Plaid (bank / card / investment data) ----
router.post("/plaid/link-token", wrap(async (req, res) => res.json(await plaid.createLinkToken(uid(req)))));
router.post(
  "/plaid/exchange",
  wrap(async (req, res) => {
    const { public_token } = req.body || {};
    const ex = await plaid.exchangePublicToken(public_token);
    await models.saveIntegration(uid(req), "plaid", ex.access_token, { item_id: ex.item_id });
    res.json({ ok: true });
  })
);
router.post(
  "/plaid/sync",
  wrap(async (req, res) => {
    const userId = uid(req);
    const integ = await models.getIntegration(userId, "plaid");
    if (!integ) return res.status(400).json({ message: "Plaid not linked" });
    const meta = integ.meta ? JSON.parse(integ.meta) : {};
    const acct = await plaid.getAccounts(integ.token);
    const existing = await models.listAccounts(userId);
    const idMap = {};
    for (const a of acct.accounts) {
      const row = plaid.mapAccount(a);
      const found = existing.find((e) => e.external_id === row.external_id);
      const saved = found ? await models.updateAccount(userId, found.id, { balance: row.balance }) : await models.addAccount(userId, row);
      idMap[a.account_id] = saved.id;
    }
    let cursor = meta.cursor;
    let added = 0;
    let more = true;
    while (more) {
      const page = await plaid.syncTransactions(integ.token, cursor);
      const rows = page.added.map((t) => plaid.mapTransaction(t, idMap));
      if (rows.length) added += await models.addTransactions(userId, rows);
      cursor = page.next_cursor;
      more = page.has_more;
    }
    await models.saveIntegration(userId, "plaid", integ.token, { ...meta, cursor });
    res.json({ accounts: acct.accounts.length, transactionsAdded: added });
  })
);

module.exports = router;
