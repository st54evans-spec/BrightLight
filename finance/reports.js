// Turns accounts + transactions into chart-ready data: pie, line, bar.
const round = (n) => Math.round(n * 100) / 100;

function monthKey(date) {
  return date.slice(0, 7);
}

function spendingPie(transactions) {
  const byCat = {};
  for (const t of transactions) {
    if (t.amount >= 0) continue;
    byCat[t.category] = (byCat[t.category] || 0) + Math.abs(Number(t.amount));
  }
  const labels = Object.keys(byCat).sort((a, b) => byCat[b] - byCat[a]);
  return { labels, data: labels.map((l) => round(byCat[l])) };
}

function netWorthPie(accounts) {
  const assets = {};
  const liabilities = {};
  for (const a of accounts) {
    const bal = Number(a.balance);
    const bucket = ["credit", "loan", "mortgage", "heloc"].includes(a.type) ? liabilities : assets;
    bucket[a.type] = (bucket[a.type] || 0) + Math.abs(bal);
  }
  const sum = (o) => Object.values(o).reduce((s, v) => s + v, 0);
  return {
    assets: { labels: Object.keys(assets), data: Object.values(assets).map(round) },
    liabilities: { labels: Object.keys(liabilities), data: Object.values(liabilities).map(round) },
    netWorth: round(sum(assets) - sum(liabilities)),
    totalAssets: round(sum(assets)),
    totalLiabilities: round(sum(liabilities)),
  };
}

function cashFlowBar(transactions) {
  const months = {};
  for (const t of transactions) {
    const k = monthKey(t.date);
    months[k] = months[k] || { income: 0, expenses: 0 };
    if (t.amount >= 0) months[k].income += Number(t.amount);
    else months[k].expenses += Math.abs(Number(t.amount));
  }
  const labels = Object.keys(months).sort();
  return {
    labels,
    income: labels.map((k) => round(months[k].income)),
    expenses: labels.map((k) => round(months[k].expenses)),
    net: labels.map((k) => round(months[k].income - months[k].expenses)),
  };
}

function cashLine(transactions, startingCash = 0) {
  const sorted = [...transactions].sort((a, b) => a.date.localeCompare(b.date));
  const byMonth = {};
  let running = startingCash;
  for (const t of sorted) {
    running += Number(t.amount);
    byMonth[monthKey(t.date)] = running;
  }
  const labels = Object.keys(byMonth).sort();
  return { labels, data: labels.map((k) => round(byMonth[k])) };
}

function businessSnapshot(transactions) {
  const biz = transactions.filter((t) => t.is_business);
  const last3 = biz.filter((t) => t.date >= shiftMonths(-3));
  const revenue = last3.filter((t) => t.amount > 0).reduce((s, t) => s + Number(t.amount), 0) / 3;
  const cogs = last3.filter((t) => t.amount < 0 && /cogs|inventory|product|materials/i.test(t.category)).reduce((s, t) => s + Math.abs(Number(t.amount)), 0) / 3;
  const opex = last3.filter((t) => t.amount < 0 && !/cogs|inventory|product|materials|debt|loan/i.test(t.category)).reduce((s, t) => s + Math.abs(Number(t.amount)), 0) / 3;
  const debt = last3.filter((t) => t.amount < 0 && /debt|loan/i.test(t.category)).reduce((s, t) => s + Math.abs(Number(t.amount)), 0) / 3;
  return { monthlyRevenue: round(revenue), monthlyCOGS: round(cogs), monthlyOpex: round(opex), monthlyDebtService: round(debt), grossMargin: revenue ? round((revenue - cogs) / revenue) : 0 };
}

function shiftMonths(n) {
  const d = new Date();
  d.setMonth(d.getMonth() + n);
  return d.toISOString().slice(0, 10);
}

function summary({ accounts, transactions }) {
  const cashAccounts = accounts.filter((a) => ["checking", "savings"].includes(a.type));
  const cash = cashAccounts.reduce((s, a) => s + Number(a.balance), 0);
  return {
    cash: round(cash),
    netWorth: netWorthPie(accounts),
    spendingPie: spendingPie(transactions),
    cashFlowBar: cashFlowBar(transactions),
    cashLine: cashLine(transactions, cash - transactions.reduce((s, t) => s + Number(t.amount), 0)),
    business: businessSnapshot(transactions),
  };
}

module.exports = { spendingPie, netWorthPie, cashFlowBar, cashLine, businessSnapshot, summary };
