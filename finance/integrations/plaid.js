// Bank / card / investment data via Plaid. Needs PLAID_CLIENT_ID + PLAID_SECRET.
// Flow: createLinkToken -> (front end opens Plaid Link) -> exchangePublicToken -> sync.
const ENV = process.env.PLAID_ENV || "sandbox";
const BASE = `https://${ENV}.plaid.com`;

function configured() {
  return !!(process.env.PLAID_CLIENT_ID && process.env.PLAID_SECRET);
}

async function call(path, body) {
  if (!configured()) throw new Error("Plaid not configured. Set PLAID_CLIENT_ID and PLAID_SECRET.");
  const res = await fetch(BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ client_id: process.env.PLAID_CLIENT_ID, secret: process.env.PLAID_SECRET, ...body }),
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.error_message || "Plaid error " + res.status);
  return json;
}

const createLinkToken = (userId) =>
  call("/link/token/create", {
    user: { client_user_id: String(userId) },
    client_name: "BrightLight Finance",
    products: ["transactions"],
    country_codes: ["US"],
    language: "en",
  });

const exchangePublicToken = (publicToken) => call("/item/public_token/exchange", { public_token: publicToken });
const getAccounts = (accessToken) => call("/accounts/get", { access_token: accessToken });
const syncTransactions = (accessToken, cursor) => call("/transactions/sync", { access_token: accessToken, cursor: cursor || undefined });

/** Map Plaid account -> finance_accounts row. */
function mapAccount(a) {
  const typeMap = { depository: a.subtype === "savings" ? "savings" : "checking", credit: "credit", loan: a.subtype === "mortgage" ? "mortgage" : "loan", investment: "investment" };
  return {
    name: a.name,
    type: typeMap[a.type] || a.type,
    institution: a.official_name || "",
    balance: a.type === "credit" || a.type === "loan" ? -Math.abs(a.balances.current || 0) : a.balances.current || 0,
    external_id: a.account_id,
  };
}

/** Map Plaid transaction -> finance_transactions row. Plaid amounts are positive for outflows. */
function mapTransaction(t, accountIdMap) {
  return {
    account_id: accountIdMap[t.account_id] || null,
    date: t.date,
    amount: -Number(t.amount),
    category: (t.personal_finance_category && t.personal_finance_category.primary) || (t.category && t.category[0]) || "uncategorized",
    description: t.merchant_name || t.name,
    external_id: t.transaction_id,
  };
}

module.exports = { configured, createLinkToken, exchangePublicToken, getAccounts, syncTransactions, mapAccount, mapTransaction };
