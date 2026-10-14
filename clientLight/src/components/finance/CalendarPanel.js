import React, { useEffect, useState } from "react";
import { financeApi, money } from "../../utils/api";

const today = () => new Date().toISOString().slice(0, 10);
const plusDays = (n) => new Date(Date.now() + n * 864e5).toISOString().slice(0, 10);

export default function CalendarPanel() {
  const [events, setEvents] = useState([]);
  const [days, setDays] = useState(45);
  const [category, setCategory] = useState("");
  const [form, setForm] = useState({ date: today(), title: "", category: "bill", amount: "" });
  const [msg, setMsg] = useState("");

  const load = () =>
    financeApi()
      .get("/calendar", { params: { from: today(), to: plusDays(days), status: "pending", category: category || undefined } })
      .then((r) => setEvents(r.data))
      .catch((e) => setMsg(e.message));

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [days, category]);

  const seed = () => {
    const y = new Date().getFullYear();
    Promise.all([financeApi().post("/calendar/seed/" + y), financeApi().post("/calendar/seed/" + (y + 1))])
      .then((rs) => {
        setMsg(`Loaded ${rs[0].data.added + rs[1].data.added} federal, NJ, bill and invoice dates for ${y}-${y + 1}.`);
        load();
      })
      .catch((e) => setMsg(e.message));
  };

  const done = (id) =>
    financeApi()
      .patch("/calendar/" + id, { status: "done" })
      .then(load);

  const add = (e) => {
    e.preventDefault();
    if (!form.title) return;
    financeApi()
      .post("/calendar", { ...form, amount: form.amount ? Number(form.amount) : null })
      .then(() => {
        setForm({ ...form, title: "", amount: "" });
        load();
      });
  };

  return (
    <div className="fin-card">
      <h3>Financial calendar</h3>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginBottom: 8 }}>
        <select value={days} onChange={(e) => setDays(Number(e.target.value))} style={selStyle}>
          <option value={14}>Next 2 weeks</option>
          <option value={45}>Next 45 days</option>
          <option value={120}>Next 4 months</option>
          <option value={400}>Next year</option>
        </select>
        <select value={category} onChange={(e) => setCategory(e.target.value)} style={selStyle}>
          <option value="">All</option>
          {["tax", "bill", "invoice", "bookkeeping", "planning", "compliance", "loan", "insurance"].map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <button className="fin-btn ghost" onClick={seed}>
          Load tax + bill dates
        </button>
      </div>
      {msg && <div className="fin-note">{msg}</div>}
      <ul className="fin-events" style={{ maxHeight: 330, overflowY: "auto", padding: 0 }}>
        {events.length === 0 && <li className="fin-note">Nothing pending in this window.</li>}
        {events.map((e) => (
          <li key={e.id}>
            <span className="d">{e.date}</span>
            <span>
              {e.title}
              {e.form ? <span className="fin-note"> ({e.form})</span> : null}
              {e.amount ? <span className="fin-note"> {money(e.amount)}</span> : null}
              <span className={"cat " + e.category}>{e.category}</span>
            </span>
            <button onClick={() => done(e.id)} title="Mark done">
              done
            </button>
          </li>
        ))}
      </ul>
      <form onSubmit={add} className="fin-form" style={{ marginTop: 10 }}>
        <label>
          Date
          <input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
        </label>
        <label>
          What
          <input value={form.title} placeholder="Pay printer invoice" onChange={(e) => setForm({ ...form, title: e.target.value })} />
        </label>
        <label>
          Type
          <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
            {["bill", "invoice", "tax", "bookkeeping", "planning", "compliance", "loan", "insurance"].map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </label>
        <label>
          Amount
          <input type="number" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} />
        </label>
        <label>
          &nbsp;
          <button className="fin-btn" type="submit">
            Add
          </button>
        </label>
      </form>
    </div>
  );
}

const selStyle = { background: "#0f1115", color: "#e8e6df", border: "1px solid #333", borderRadius: 6, padding: 6 };
