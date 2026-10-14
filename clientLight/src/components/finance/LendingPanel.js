import React, { useState } from "react";
import { Line } from "react-chartjs-2";
import { financeApi, money, pct } from "../../utils/api";

const Field = ({ l, k, f, set, step = "1" }) => (
  <label>
    {l}
    <input type="number" step={step} value={f[k]} onChange={(e) => set({ ...f, [k]: e.target.value })} />
  </label>
);
const n = (v, d) => (v === "" || v == null ? d : Number(v));

export default function LendingPanel() {
  const [loan, setLoan] = useState({ amount: 250000, termMonths: 120 });
  const [loans, setLoans] = useState(null);
  const [h, setH] = useState({ homeValue: 450000, firstMortgageBalance: "", renovationBudget: 60000, helocRate: 6.75, maxCLTV: 85, closingCosts: 1500 });
  const [heloc, setHeloc] = useState(null);
  const [err, setErr] = useState("");

  const compare = (e) => {
    e.preventDefault();
    financeApi()
      .post("/loans/compare", { amount: n(loan.amount, 0), termMonths: n(loan.termMonths, 120) })
      .then((r) => setLoans(r.data))
      .catch((x) => setErr(x.message));
  };
  const runHeloc = (e) => {
    e.preventDefault();
    financeApi()
      .post("/heloc", {
        homeValue: n(h.homeValue, 0),
        firstMortgageBalance: h.firstMortgageBalance === "" ? undefined : Number(h.firstMortgageBalance),
        renovationBudget: n(h.renovationBudget, 0),
        helocRate: n(h.helocRate, 6.75) / 100,
        maxCLTV: n(h.maxCLTV, 85) / 100,
        closingCosts: n(h.closingCosts, 0),
      })
      .then((r) => setHeloc(r.data))
      .catch((x) => setErr(x.message));
  };

  return (
    <div className="fin-grid">
      <div className="fin-card">
        <h3>Business loan: high value, low year-one payments, best interest</h3>
        <form onSubmit={compare} className="fin-form">
          <Field l="Amount" k="amount" f={loan} set={setLoan} />
          <Field l="Term (months)" k="termMonths" f={loan} set={setLoan} />
          <label>
            &nbsp;
            <button className="fin-btn">Compare lenders</button>
          </label>
        </form>
        {err && <div style={{ color: "#d9534f" }}>{err}</div>}
        {loans && loans.ranked.length === 0 && <div className="fin-note">{loans.note}</div>}
        {loans && loans.ranked.length > 0 && (
          <div style={{ overflowX: "auto" }}>
            <table className="fin-table">
              <thead>
                <tr>
                  <th>Lender</th>
                  <th>Rate</th>
                  <th>Yr-1 / mo</th>
                  <th>After</th>
                  <th>Total interest</th>
                  <th>Max</th>
                  <th>Score</th>
                </tr>
              </thead>
              <tbody>
                {loans.ranked.map((l, i) => (
                  <tr key={l.lender} className={i === 0 ? "best" : ""}>
                    <td>
                      {l.lender}
                      <div className="fin-note">
                        {l.product} · {l.structure.replace("_", " ")} · {l.requirements}
                      </div>
                    </td>
                    <td>{pct(l.rate)}</td>
                    <td>{money(l.firstYearMonthly)}</td>
                    <td>{money(l.afterIntroPayment)}</td>
                    <td>{money(l.totalInterest)}</td>
                    <td>{money(l.maxAmount)}</td>
                    <td>{l.score}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="fin-note">Indicative rates (prime 6.75%). Ask the accountant to refresh quotes with live search, then paste real offers.</p>
          </div>
        )}
      </div>
      <div className="fin-card">
        <h3>HELOC on 2034 Lambert Ave: clear all debt + renovation</h3>
        <form onSubmit={runHeloc} className="fin-form">
          <Field l="Home value" k="homeValue" f={h} set={setH} />
          <Field l="1st mortgage (blank = from accounts)" k="firstMortgageBalance" f={h} set={setH} />
          <Field l="Renovation budget" k="renovationBudget" f={h} set={setH} />
          <Field l="HELOC rate %" k="helocRate" f={h} set={setH} step="0.01" />
          <Field l="Max CLTV %" k="maxCLTV" f={h} set={setH} />
          <Field l="Closing costs" k="closingCosts" f={h} set={setH} />
          <label>
            &nbsp;
            <button className="fin-btn">Size the line</button>
          </label>
        </form>
        <p className="fin-note">Debts come from your liability accounts (credit, loan, heloc). Add them under Charts.</p>
        {heloc && (
          <div>
            <div className="fin-kpis">
              <K l="Need (debt + reno + costs)" v={money(heloc.needed)} />
              <K l="Max line at CLTV" v={money(heloc.maxLine)} />
              <K l="Line size" v={money(heloc.lineSize)} />
              <K l="Shortfall" v={money(heloc.shortfall)} />
              <K l="Interest-only / mo" v={money(heloc.interestOnlyPayment)} />
              <K l="Current debt pmts / mo" v={money(heloc.currentDebtPayments)} />
              <K l="Monthly cash freed" v={money(heloc.monthlyCashFlowChange)} />
              <K l="Debt blended rate" v={pct(heloc.weightedDebtRate)} />
              <K l="CLTV after" v={pct(heloc.cltv)} />
              <K l="Repay pmt (yr 11+)" v={money(heloc.repayPayment)} />
            </div>
            <strong>{heloc.verdict}</strong>
            <Line
              data={{
                labels: ["Now", "Draw period", "Repay period"],
                datasets: [{ label: "Monthly payment", data: [heloc.currentDebtPayments, heloc.interestOnlyPayment, heloc.repayPayment], borderColor: "#d4af37", fill: false }],
              }}
              options={{ legend: { labels: { fontColor: "#e8e6df" } }, scales: { yAxes: [{ ticks: { fontColor: "#9a978f" } }], xAxes: [{ ticks: { fontColor: "#9a978f" } }] } }}
            />
            <h4>Where to apply</h4>
            <table className="fin-table">
              <thead>
                <tr>
                  <th>Lender</th>
                  <th>Rate</th>
                  <th>Max CLTV</th>
                  <th>Note</th>
                </tr>
              </thead>
              <tbody>
                {heloc.lenders.map((l) => (
                  <tr key={l.name}>
                    <td>{l.name}</td>
                    <td>{pct(l.rate)}</td>
                    <td>{pct(l.maxCLTV)}</td>
                    <td className="fin-note">
                      {l.intro}. {l.note}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

const K = ({ l, v }) => (
  <div className="fin-kpi">
    <div className="v">{v}</div>
    <div className="l">{l}</div>
  </div>
);
