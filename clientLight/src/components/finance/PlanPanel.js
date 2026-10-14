import React, { useState } from "react";
import { Line, Bar } from "react-chartjs-2";
import { financeApi, money, pct } from "../../utils/api";

const F = ({ l, k, f, set, type = "number" }) => (
  <label>
    {l}
    <input type={type} value={f[k]} onChange={(e) => set({ ...f, [k]: e.target.value })} />
  </label>
);
const nums = (o) => Object.fromEntries(Object.entries(o).map(([k, v]) => [k, v === "" || isNaN(v) ? v : Number(v)]));
const K = ({ l, v }) => (
  <div className="fin-kpi">
    <div className="v">{v}</div>
    <div className="l">{l}</div>
  </div>
);
const axes = { legend: { labels: { fontColor: "#e8e6df" } }, scales: { yAxes: [{ ticks: { fontColor: "#9a978f" } }], xAxes: [{ ticks: { fontColor: "#9a978f" } }] } };

export default function PlanPanel() {
  const [tax, setTax] = useState({ year: 2026, filingStatus: "mfj", w2Wages: 0, businessNetProfit: 90000, otherIncome: 0, dependentsUnder17: 1, otherDependents: 0, itemizedDeductions: 0, federalWithheld: 0, njWithheld: 0, estimatesPaid: 0 });
  const [taxOut, setTaxOut] = useState(null);
  const [ins, setIns] = useState({ debts: 20000, annualIncome: 90000, yearsToReplace: 15, mortgageBalance: 260000, educationPerChild: 120000, children: 1, finalExpenses: 15000, existingCoverage: 0, liquidAssets: 10000 });
  const [insOut, setInsOut] = useState(null);
  const [ret, setRet] = useState({ currentAge: 35, retireAge: 65, currentSavings: 20000, monthlyContribution: 500, annualReturn: 7, inflation: 3, desiredAnnualIncome: 80000 });
  const [retOut, setRetOut] = useState(null);
  const [edu, setEdu] = useState({ childAge: 3, startAge: 18, currentSavings: 0, monthlyContribution: 200, annualReturn: 6, targetToday: 120000 });
  const [eduOut, setEduOut] = useState(null);

  const run = (path, body, set) => (e) => {
    e.preventDefault();
    financeApi()
      .post(path, body)
      .then((r) => set(r.data))
      .catch((x) => set({ error: (x.response && x.response.data && x.response.data.message) || x.message }));
  };

  return (
    <div className="fin-grid">
      <div className="fin-card">
        <h3>Federal + NJ tax estimate (family + STOiiiC FiT)</h3>
        <form onSubmit={run("/tax/estimate", nums(tax), setTaxOut)} className="fin-form">
          <label>
            Filing status
            <select value={tax.filingStatus} onChange={(e) => setTax({ ...tax, filingStatus: e.target.value })}>
              <option value="mfj">Married joint</option>
              <option value="single">Single</option>
              <option value="hoh">Head of household</option>
              <option value="mfs">Married separate</option>
            </select>
          </label>
          <F l="W-2 wages" k="w2Wages" f={tax} set={setTax} />
          <F l="Business net profit" k="businessNetProfit" f={tax} set={setTax} />
          <F l="Other income" k="otherIncome" f={tax} set={setTax} />
          <F l="Kids under 17" k="dependentsUnder17" f={tax} set={setTax} />
          <F l="Itemized deductions" k="itemizedDeductions" f={tax} set={setTax} />
          <F l="Federal withheld" k="federalWithheld" f={tax} set={setTax} />
          <F l="NJ withheld" k="njWithheld" f={tax} set={setTax} />
          <F l="Estimates paid" k="estimatesPaid" f={tax} set={setTax} />
          <label>
            &nbsp;
            <button className="fin-btn">Run numbers</button>
          </label>
        </form>
        {taxOut && !taxOut.error && (
          <div>
            <div className="fin-kpis">
              <K l="Federal total" v={money(taxOut.federal.totalTax)} />
              <K l="of which SE tax" v={money(taxOut.federal.selfEmploymentTax)} />
              <K l="NJ tax" v={money(taxOut.nj.tax)} />
              <K l="Federal balance due" v={money(taxOut.federal.balanceDue)} />
              <K l="NJ balance due" v={money(taxOut.nj.balanceDue)} />
              <K l="Fed quarterly est." v={money(taxOut.quarterlyEstimate)} />
              <K l="NJ quarterly est." v={money(taxOut.njQuarterlyEstimate)} />
              <K l="Effective fed rate" v={pct(taxOut.federal.effectiveRate)} />
            </div>
            <Bar
              data={{
                labels: ["Fed income tax", "SE tax", "Credits", "NJ tax"],
                datasets: [{ label: "USD", data: [taxOut.federal.incomeTax, taxOut.federal.selfEmploymentTax, -taxOut.federal.credits, taxOut.nj.tax], backgroundColor: ["#d4af37", "#e59866", "#8fb98f", "#7fb3d5"] }],
              }}
              options={axes}
            />
            <p className="fin-note">{taxOut.note}</p>
          </div>
        )}
        {taxOut && taxOut.error && <div style={{ color: "#d9534f" }}>{taxOut.error}</div>}
      </div>

      <div className="fin-card">
        <h3>Life insurance need (DIME)</h3>
        <form onSubmit={run("/insurance/needs", nums(ins), setInsOut)} className="fin-form">
          <F l="Debts (non-mortgage)" k="debts" f={ins} set={setIns} />
          <F l="Annual income" k="annualIncome" f={ins} set={setIns} />
          <F l="Years to replace" k="yearsToReplace" f={ins} set={setIns} />
          <F l="Mortgage balance" k="mortgageBalance" f={ins} set={setIns} />
          <F l="Education per child" k="educationPerChild" f={ins} set={setIns} />
          <F l="Children" k="children" f={ins} set={setIns} />
          <F l="Existing coverage" k="existingCoverage" f={ins} set={setIns} />
          <F l="Liquid assets" k="liquidAssets" f={ins} set={setIns} />
          <label>
            &nbsp;
            <button className="fin-btn">Size policy</button>
          </label>
        </form>
        {insOut && !insOut.error && (
          <div>
            <div className="fin-kpis">
              <K l="Total need" v={money(insOut.totalNeed)} />
              <K l="Gap" v={money(insOut.gap)} />
              <K l="Buy (face amount)" v={money(insOut.recommendedFaceAmount)} />
              <K l="Term" v={insOut.suggestedTerm + " yrs"} />
            </div>
            <ul className="fin-note" style={{ paddingLeft: 18 }}>
              {insOut.guidance.map((g) => (
                <li key={g}>{g}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="fin-card">
        <h3>Retirement</h3>
        <form onSubmit={run("/retirement", { ...nums(ret), annualReturn: Number(ret.annualReturn) / 100, inflation: Number(ret.inflation) / 100 }, setRetOut)} className="fin-form">
          <F l="Current age" k="currentAge" f={ret} set={setRet} />
          <F l="Retire at" k="retireAge" f={ret} set={setRet} />
          <F l="Saved now" k="currentSavings" f={ret} set={setRet} />
          <F l="Monthly contribution" k="monthlyContribution" f={ret} set={setRet} />
          <F l="Return %" k="annualReturn" f={ret} set={setRet} />
          <F l="Inflation %" k="inflation" f={ret} set={setRet} />
          <F l="Income wanted (today $)" k="desiredAnnualIncome" f={ret} set={setRet} />
          <label>
            &nbsp;
            <button className="fin-btn">Project</button>
          </label>
        </form>
        {retOut && !retOut.error && (
          <div>
            <div className="fin-kpis">
              <K l="Projected at retirement" v={money(retOut.projectedNominal)} />
              <K l="In today's dollars" v={money(retOut.projectedInTodaysDollars)} />
              <K l="Target" v={money(retOut.targetNominal)} />
              <K l="Extra / mo to close gap" v={money(retOut.extraMonthlyNeeded)} />
            </div>
            <Line data={{ labels: retOut.path.map((p) => p.age), datasets: [{ label: "Balance", data: retOut.path.map((p) => p.balance), borderColor: "#d4af37", fill: false }] }} options={axes} />
            <p className="fin-note">{retOut.allocationIdea}</p>
          </div>
        )}
      </div>

      <div className="fin-card">
        <h3>Brynlee's future (529)</h3>
        <form onSubmit={run("/education", { ...nums(edu), annualReturn: Number(edu.annualReturn) / 100 }, setEduOut)} className="fin-form">
          <F l="Child age" k="childAge" f={edu} set={setEdu} />
          <F l="College at" k="startAge" f={edu} set={setEdu} />
          <F l="Saved now" k="currentSavings" f={edu} set={setEdu} />
          <F l="Monthly contribution" k="monthlyContribution" f={edu} set={setEdu} />
          <F l="Return %" k="annualReturn" f={edu} set={setEdu} />
          <F l="Cost today (4 yrs)" k="targetToday" f={edu} set={setEdu} />
          <label>
            &nbsp;
            <button className="fin-btn">Project</button>
          </label>
        </form>
        {eduOut && !eduOut.error && (
          <div>
            <div className="fin-kpis">
              <K l="Projected" v={money(eduOut.projected)} />
              <K l="Cost at start" v={money(eduOut.targetAtStart)} />
              <K l="Gap" v={money(eduOut.gap)} />
              <K l="Extra / mo" v={money(eduOut.extraMonthlyNeeded)} />
            </div>
            <p className="fin-note">{eduOut.vehicle}</p>
          </div>
        )}
      </div>
    </div>
  );
}
