import React, { useState } from "react";
import { Line } from "react-chartjs-2";
import { financeApi, money, pct } from "../../utils/api";

const F = ({ l, k, f, set, step = "1" }) => (
  <label>
    {l}
    <input type="number" step={step} value={f[k]} onChange={(e) => set({ ...f, [k]: e.target.value })} />
  </label>
);
const clean = (o) => Object.fromEntries(Object.entries(o).filter(([, v]) => v !== "").map(([k, v]) => [k, Number(v)]));

export default function MovePanel() {
  const [m, setM] = useState({ moveCost: 20000, expectedMonthlyLiftRevenue: 8000, liftMarginPct: "", rampMonths: 3, cash: "", monthlyRevenue: "", monthlyCOGS: "", monthlyOpex: "", monthlyDebtService: "", minRunwayMonths: 6 });
  const [out, setOut] = useState(null);
  const [p, setP] = useState({ unitCost: 18, targetMarginPct: 55, marketLow: 30, marketHigh: 48, units: 40, mustSellByDays: 30, fees: 3 });
  const [price, setPrice] = useState(null);

  const ready = (e) => {
    e.preventDefault();
    const body = clean(m);
    if (body.liftMarginPct != null) body.liftMarginPct = body.liftMarginPct / 100;
    financeApi()
      .post("/move-readiness", body)
      .then((r) => setOut(r.data));
  };
  const runPrice = (e) => {
    e.preventDefault();
    const b = clean(p);
    b.targetMarginPct /= 100;
    b.fees /= 100;
    financeApi()
      .post("/pricing", b)
      .then((r) => setPrice(r.data));
  };

  return (
    <div className="fin-grid">
      <div className="fin-card">
        <h3>Is the STOiiiC FiT move backed by the numbers?</h3>
        <p className="fin-note">Blank business fields pull the last 3 months from your transactions. The move: a new line, a store, a big inventory buy, an ad push.</p>
        <form onSubmit={ready} className="fin-form">
          <F l="Move cost" k="moveCost" f={m} set={setM} />
          <F l="Expected revenue lift / mo" k="expectedMonthlyLiftRevenue" f={m} set={setM} />
          <F l="Lift margin % (blank = current)" k="liftMarginPct" f={m} set={setM} />
          <F l="Ramp months" k="rampMonths" f={m} set={setM} />
          <F l="Min runway months" k="minRunwayMonths" f={m} set={setM} />
          <F l="Cash (override)" k="cash" f={m} set={setM} />
          <F l="Revenue / mo (override)" k="monthlyRevenue" f={m} set={setM} />
          <F l="COGS / mo (override)" k="monthlyCOGS" f={m} set={setM} />
          <F l="Opex / mo (override)" k="monthlyOpex" f={m} set={setM} />
          <F l="Debt service / mo (override)" k="monthlyDebtService" f={m} set={setM} />
          <label>
            &nbsp;
            <button className="fin-btn">Decide</button>
          </label>
        </form>
        {out && (
          <div>
            <div className={"fin-verdict " + out.verdict.split(" ")[0]}>{out.verdict}</div>
            <ul style={{ paddingLeft: 18 }}>
              {out.checks.map((c) => (
                <li key={c.name} className={"fin-check " + (c.pass ? "pass" : "fail")}>
                  {c.pass ? "PASS" : "FAIL"} · {c.name} · {c.value}
                </li>
              ))}
            </ul>
            <div className="fin-kpis">
              <K l="Gross margin" v={pct(out.grossMargin)} />
              <K l="Free cash / mo" v={money(out.freeCash)} />
              <K l="Cash after move" v={money(out.cashAfterMove)} />
              <K l="Payback (months)" v={out.paybackMonths == null ? "never" : out.paybackMonths} />
              <K l="Lift profit / mo" v={money(out.monthlyLiftProfit)} />
              <K l="DSCR" v={out.dscr == null ? "no debt" : out.dscr} />
            </div>
            {out.whatWouldMakeItGo.length > 0 && <p className="fin-note">To make it GO: {out.whatWouldMakeItGo.join("; ")}.</p>}
          </div>
        )}
      </div>
      <div className="fin-card">
        <h3>Top dollar, on time</h3>
        <form onSubmit={runPrice} className="fin-form">
          <F l="Unit cost" k="unitCost" f={p} set={setP} step="0.01" />
          <F l="Target margin %" k="targetMarginPct" f={p} set={setP} />
          <F l="Market low" k="marketLow" f={p} set={setP} step="0.01" />
          <F l="Market high" k="marketHigh" f={p} set={setP} step="0.01" />
          <F l="Units" k="units" f={p} set={setP} />
          <F l="Must sell by (days)" k="mustSellByDays" f={p} set={setP} />
          <F l="Fees %" k="fees" f={p} set={setP} step="0.1" />
          <label>
            &nbsp;
            <button className="fin-btn">Price it</button>
          </label>
        </form>
        {price && (
          <div>
            <div className="fin-kpis">
              <K l="List" v={money(price.listPrice)} />
              <K l="Floor" v={money(price.floorPrice)} />
              <K l="Break-even" v={money(price.breakEven)} />
              <K l="Revenue at list" v={money(price.revenueAtList)} />
              <K l="Revenue at floor" v={money(price.revenueAtFloor)} />
            </div>
            <Line
              data={{ labels: price.dropSchedule.map((s) => "Day " + s.day), datasets: [{ label: "Price", data: price.dropSchedule.map((s) => s.price), borderColor: "#d4af37", fill: false }] }}
              options={{ legend: { labels: { fontColor: "#e8e6df" } }, scales: { yAxes: [{ ticks: { fontColor: "#9a978f" } }], xAxes: [{ ticks: { fontColor: "#9a978f" } }] } }}
            />
            <ul className="fin-note" style={{ paddingLeft: 18 }}>
              {price.plays.map((x) => (
                <li key={x}>{x}</li>
              ))}
            </ul>
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
