const db = require("../database/dbConfig");

const parse = (s, fallback) => {
  try {
    return s ? JSON.parse(s) : fallback;
  } catch (e) {
    return fallback;
  }
};

async function insertAndFetch(table, row) {
  const [id] = await db(table).insert(row);
  return db(table).where({ id }).first();
}

// ---- profile ----
async function getProfile(userId) {
  const row = await db("finance_profile").where({ user_id: userId }).first();
  return row ? parse(row.data, {}) : {};
}
async function saveProfile(userId, data) {
  const existing = await db("finance_profile").where({ user_id: userId }).first();
  const merged = { ...(existing ? parse(existing.data, {}) : {}), ...data };
  if (existing) {
    await db("finance_profile").where({ id: existing.id }).update({ data: JSON.stringify(merged), updated_at: db.fn.now() });
  } else {
    await db("finance_profile").insert({ user_id: userId, data: JSON.stringify(merged) });
  }
  return merged;
}

// ---- events ----
// taxYear / quarter / kind ride along on the in-memory schedule for the tool.
// Only real columns are written.
const EVENT_COLUMNS = ["date", "title", "category", "jurisdiction", "form", "amount", "status", "source", "notes"];
function eventRow(userId, e) {
  const row = { user_id: userId };
  for (const key of EVENT_COLUMNS) if (e[key] !== undefined) row[key] = e[key];
  return row;
}
function listEvents(userId, { from, to, category, status } = {}) {
  let q = db("finance_events").where({ user_id: userId }).orderBy("date");
  if (from) q = q.where("date", ">=", from);
  if (to) q = q.where("date", "<=", to);
  if (category) q = q.where({ category });
  if (status) q = q.where({ status });
  return q;
}
const addEvent = (userId, e) => insertAndFetch("finance_events", eventRow(userId, e));
async function addEvents(userId, events) {
  if (!events.length) return 0;
  // Skip duplicates (same date + title) so re-seeding is safe.
  const existing = await db("finance_events").where({ user_id: userId }).select("date", "title");
  const seen = new Set(existing.map((e) => e.date + "|" + e.title));
  const fresh = events.filter((e) => !seen.has(e.date + "|" + e.title)).map((e) => eventRow(userId, e));
  for (let i = 0; i < fresh.length; i += 100) await db("finance_events").insert(fresh.slice(i, i + 100));
  return fresh.length;
}
async function updateEvent(userId, id, patch) {
  await db("finance_events").where({ id, user_id: userId }).update(patch);
  return db("finance_events").where({ id }).first();
}
const deleteEvent = (userId, id) => db("finance_events").where({ id, user_id: userId }).del();

// ---- accounts / transactions ----
const listAccounts = (userId) => db("finance_accounts").where({ user_id: userId }).orderBy("is_business").orderBy("name");
const addAccount = (userId, a) => insertAndFetch("finance_accounts", { ...a, user_id: userId });
async function updateAccount(userId, id, patch) {
  await db("finance_accounts").where({ id, user_id: userId }).update({ ...patch, updated_at: db.fn.now() });
  return db("finance_accounts").where({ id }).first();
}
const deleteAccount = (userId, id) => db("finance_accounts").where({ id, user_id: userId }).del();

function listTransactions(userId, { from, to, account_id, is_business } = {}) {
  let q = db("finance_transactions").where({ user_id: userId }).orderBy("date", "desc");
  if (from) q = q.where("date", ">=", from);
  if (to) q = q.where("date", "<=", to);
  if (account_id) q = q.where({ account_id });
  if (is_business != null) q = q.where({ is_business: !!is_business });
  return q;
}
const addTransaction = (userId, t) => insertAndFetch("finance_transactions", { ...t, user_id: userId });
async function addTransactions(userId, rows) {
  const prepared = rows.map((r) => ({ ...r, user_id: userId }));
  for (let i = 0; i < prepared.length; i += 100) await db("finance_transactions").insert(prepared.slice(i, i + 100));
  return prepared.length;
}

// ---- goals ----
const listGoals = (userId) => db("finance_goals").where({ user_id: userId });
const addGoal = (userId, g) => insertAndFetch("finance_goals", { ...g, user_id: userId });
async function updateGoal(userId, id, patch) {
  await db("finance_goals").where({ id, user_id: userId }).update(patch);
  return db("finance_goals").where({ id }).first();
}

// ---- documents ----
async function listDocuments(userId) {
  const rows = await db("finance_documents").where({ user_id: userId }).orderBy("created_at", "desc");
  return rows.map(hydrateDoc);
}
async function getDocument(userId, id) {
  const row = await db("finance_documents").where({ id, user_id: userId }).first();
  return row ? hydrateDoc(row) : null;
}
function hydrateDoc(row) {
  return { ...row, fields: parse(row.fields, {}), missing: parse(row.missing, []), signatures: parse(row.signatures, []) };
}
async function addDocument(userId, d) {
  const row = await insertAndFetch("finance_documents", {
    user_id: userId,
    kind: d.kind,
    status: d.status || "draft",
    fields: JSON.stringify(d.fields || {}),
    missing: JSON.stringify(d.missing || []),
    signatures: JSON.stringify(d.signatures || []),
  });
  return hydrateDoc(row);
}
async function updateDocument(userId, id, patch) {
  const p = { ...patch };
  for (const k of ["fields", "missing", "signatures"]) if (p[k] !== undefined) p[k] = JSON.stringify(p[k]);
  await db("finance_documents").where({ id, user_id: userId }).update(p);
  return getDocument(userId, id);
}

// ---- messages ----
const listMessages = (userId, limit = 40) =>
  db("finance_messages").where({ user_id: userId }).orderBy("id", "desc").limit(limit).then((r) => r.reverse());
const addMessage = (userId, role, content, meta) =>
  insertAndFetch("finance_messages", { user_id: userId, role, content, meta: meta ? JSON.stringify(meta) : null });
const clearMessages = (userId) => db("finance_messages").where({ user_id: userId }).del();

// ---- integrations / credit ----
const getIntegration = (userId, provider) => db("finance_integrations").where({ user_id: userId, provider }).first();
async function saveIntegration(userId, provider, token, meta) {
  const existing = await getIntegration(userId, provider);
  const row = { token, meta: meta ? JSON.stringify(meta) : null };
  if (existing) {
    await db("finance_integrations").where({ id: existing.id }).update(row);
    return getIntegration(userId, provider);
  }
  return insertAndFetch("finance_integrations", { ...row, user_id: userId, provider });
}
const listCreditReports = (userId) => db("finance_credit_reports").where({ user_id: userId }).orderBy("pulled_at", "desc");
const addCreditReport = (userId, r) =>
  insertAndFetch("finance_credit_reports", { ...r, data: r.data ? JSON.stringify(r.data) : null, user_id: userId });

module.exports = {
  db,
  getProfile,
  saveProfile,
  listEvents,
  addEvent,
  addEvents,
  updateEvent,
  deleteEvent,
  listAccounts,
  addAccount,
  updateAccount,
  deleteAccount,
  listTransactions,
  addTransaction,
  addTransactions,
  listGoals,
  addGoal,
  updateGoal,
  listDocuments,
  getDocument,
  addDocument,
  updateDocument,
  listMessages,
  addMessage,
  clearMessages,
  getIntegration,
  saveIntegration,
  listCreditReports,
  addCreditReport,
};
