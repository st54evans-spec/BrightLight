import React, { useEffect, useState } from "react";
import { Pie, Line, Bar } from "react-chartjs-2";
import { financeApi, money, pct } from "../../utils/api";

const PALETTE = ["#d4af37", "#7fb3d5", "#8fb98f", "#c9a0dc", "#e59866", "#9a978f", "#d9534f", "#5dade2", "#f7dc6f", "#76d7c4"];
const opts = (title) => ({
  legend: { labels: { fontColor: "#e8e6df" } },
  title: { display: !!title, text: title, fontColor: "#d4af37" },
  scales: { yAxes: [{ ticks: { fontColor: "#9a978f" }, gridLines: { color: "#262a33" } }], xAxes: [{ ticks: { fontColor: "#9a978f" }, gridLines: { color: "#262a33" } }] },
});
const pieOpts = (title) => ({ legend: { labels: { fontColor: "#e8e6df" } }, title: { display: true, text: title, fontColor: "#d4af37" } });

export default function ChartsPanel() {
  const [s, setS] = useState(null);
  const [err, setErr] = useState("");
  const [acct, setAcct] = useState({ name: "", type: "checking", balance: "", rate: "", payment: "", is_business: false });
  const [tx, setTx] = useState({ date: new Date().toISOString().slice(0, 10), amount: "", category: "sales", description: "", is_business: true });

  const load = () =>
    financeApi()
      .get("/reports/summary")
      .then((r) => setS(r.data))
      .catch((e) => setErr(e.message));
  useEffect(() => {
    load();
  }, []);

  const addAccount = (e) => {
    e.preventDefault();
    financeApi()
      .post("/accounts", { ...acct, balance: Number(acct.balance), rate: acct.rate ? Number(acct.rate) / 100 : null, payment: acct.payment ? Number(acct.payment) : null })
      .then(() => {
        setAcct({ ...acct, name: "", balance: "", rate: "", payment: "" });
        load();
      });
  };
  const addTx = (e) => {
    e.preventDefault();
    financeApi()
      .post("/transactions", { ...tx, amount: Number(tx.amount) })
      .then(() => {
        setTx({ ...tx, amount: "", description: "" });
        load();
      });
  };

  if (err) return <div className="fin-card">{err}</div>;
  if (!s) return <div className="fin-card">Loading reports...</div>;

  const pie = (p, title) => ({
    labels: p.labels,
    datasets: [{ data: p.data, backgroundColor: PALETTE }],
  });

  return (
    <div>
      <div className="fin-kpis">
        <Kpi l="Cash on hand" v={money(s.cash)} />
        <Kpi l="Net worth" v={money(s.netWorth.netWorth)} />
        <Kpi l="Assets" v={money(s.netWorth.totalAssets)} />
        <Kpi l="Liabilities" v={money(s.netWorth.totalLiabilities)} />
        <Kpi l="Biz revenue / mo (3-mo avg)" v={money(s.business.monthlyRevenue)} />
        <Kpi l="Gross margin" v={pct(s.business.grossMargin)} />
        <Kpi l="Opex / mo" v={money(s.business.monthlyOpex)} />
        <Kpi l="Debt service / mo" v={money(s.business.monthlyDebtService)} />
      </div>
      <div className="fin-charts">
        <div className="fin-card">
          <Pie data={pie(s.spendingPie)} options={pieOpts("Spending by category")} />
        </div>
        <div className="fin-card">
          <Pie data={pie(s.netWorth.liabilities)} options={pieOpts("Debt by type (what the HELOC would clear)")} />
        </div>
        <div className="fin-card">
          <Line
            data={{ labels: s.cashLine.labels, datasets: [{ label: "Cash", data: s.cashLine.data, borderColor: "#d4af37", backgroundColor: "rgba(212,175,55,0.15)", fill: true }] }}
            options={opts("Cash over time")}
          />
        </div>
        <div className="fin-card">
          <Bar
            data={{
              labels: s.cashFlowBar.labels,
              datasets: [
                { label: "Income", data: s.cashFlowBar.income, backgroundColor: "#8fb98f" },
                { label: "Expenses", data: s.cashFlowBar.expenses, backgroundColor: "#d9534f" },
                { label: "Net", data: s.cashFlowBar.net, backgroundColor: "#d4af37" },
              ],
            }}
            options={opts("Income vs expenses by month")}
          />
        </div>
      </div>
      <div className="fin-grid" style={{ marginTop: 18 }}>
        <div className="fin-card">
          <h3>Add account</h3>
          <p className="fin-note">Liabilities as negative balances. Connect Plaid on the server to sync these automatically.</p>
          <form onSubmit={addAccount} className="fin-form">
            <label>
              Name
              <input value={acct.name} onChange={(e) => setAcct({ ...acct, name: e.target.value })} required />
            </label>
            <label>
              Type
              <select value={acct.type} onChange={(e) => setAcct({ ...acct, type: e.target.value })}>
                {["checking", "savings", "credit", "loan", "mortgage", "heloc", "investment", "retirement", "529"].map((t) => (
                  <option key={t}>{t}</option>
                ))}
              </select>
            </label>
            <label>
              Balance
              <input type="number" step="0.01" value={acct.balance} onChange={(e) => setAcct({ ...acct, balance: e.target.value })} required />
            </label>
            <label>
              Rate %
              <input type="number" step="0.01" value={acct.rate} onChange={(e) => setAcct({ ...acct, rate: e.target.value })} />
            </label>
            <label>
              Monthly payment
              <input type="number" value={acct.payment} onChange={(e) => setAcct({ ...acct, payment: e.target.value })} />
            </label>
            <label>
              Business?
              <select value={acct.is_business ? "yes" : "no"} onChange={(e) => setAcct({ ...acct, is_business: e.target.value === "yes" })}>
                <option value="no">personal</option>
                <option value="yes">business</option>
              </select>
            </label>
            <label>
              &nbsp;
              <button className="fin-btn">Save</button>
            </label>
          </form>
        </div>
        <div className="fin-card">
          <h3>Add transaction</h3>
          <p className="fin-note">Inflows positive, outflows negative. Use categories like sales, inventory, rent, ads, loan.</p>
          <form onSubmit={addTx} className="fin-form">
            <label>
              Date
              <input type="date" value={tx.date} onChange={(e) => setTx({ ...tx, date: e.target.value })} />
            </label>
            <label>
              Amount
              <input type="number" step="0.01" value={tx.amount} onChange={(e) => setTx({ ...tx, amount: e.target.value })} required />
            </label>
            <label>
              Category
              <input value={tx.category} onChange={(e) => setTx({ ...tx, category: e.target.value })} />
            </label>
            <label>
              Description
              <input value={tx.description} onChange={(e) => setTx({ ...tx, description: e.target.value })} />
            </label>
            <label>
              Business?
              <select value={tx.is_business ? "yes" : "no"} onChange={(e) => setTx({ ...tx, is_business: e.target.value === "yes" })}>
                <option value="yes">business</option>
                <option value="no">personal</option>
              </select>
            </label>
            <label>
              &nbsp;
              <button className="fin-btn">Save</button>
            </label>
          </form>
        </div>
      </div>
    </div>
  );
}

const Kpi = ({ l, v }) => (
  <div className="fin-kpi">
    <div className="v">{v}</div>
    <div className="l">{l}</div>
  </div>
);
