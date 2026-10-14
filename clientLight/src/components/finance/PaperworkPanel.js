import React, { useEffect, useState } from "react";
import { financeApi } from "../../utils/api";

export default function PaperworkPanel({ persona }) {
  const [templates, setTemplates] = useState([]);
  const [docs, setDocs] = useState([]);
  const [kind, setKind] = useState("heloc_application");
  const [fields, setFields] = useState({});
  const [credit, setCredit] = useState([]);
  const [msg, setMsg] = useState("");

  const load = () =>
    Promise.all([financeApi().get("/documents/templates"), financeApi().get("/documents"), financeApi().get("/credit")]).then(([t, d, c]) => {
      setTemplates(t.data);
      setDocs(d.data);
      setCredit(c.data);
    });
  useEffect(() => {
    load();
  }, []);

  const tpl = templates.find((t) => t.kind === kind);
  const prepare = (e) => {
    e.preventDefault();
    financeApi()
      .post("/documents/prepare", { kind, data: fields })
      .then((r) => {
        setMsg(`${r.data.title}: ${r.data.completion}% filled. Blank: ${r.data.missing.length}. Signatures left for you: ${r.data.signatures.join("; ")}`);
        load();
      });
  };
  const pull = () => {
    if (!window.confirm("Authorize " + ((persona && persona.name) || "the accountant") + " to pull your credit report through the connected provider?")) return;
    financeApi()
      .post("/credit/pull", { consent: true })
      .then((r) => {
        setMsg(r.data.message || `Pulled ${r.data.bureau} score ${r.data.score}.`);
        load();
      });
  };

  return (
    <div className="fin-grid">
      <div className="fin-card">
        <h3>Paperwork, filled to the signature line</h3>
        <form onSubmit={prepare}>
          <div className="fin-form">
            <label>
              Form
              <select
                value={kind}
                onChange={(e) => {
                  setKind(e.target.value);
                  setFields({});
                }}
              >
                {templates.map((t) => (
                  <option key={t.kind} value={t.kind}>
                    {t.title}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {tpl && (
            <div className="fin-form">
              {tpl.fields.map((f) => (
                <label key={f}>
                  {f}
                  <input value={fields[f] || ""} onChange={(e) => setFields({ ...fields, [f]: e.target.value })} />
                </label>
              ))}
            </div>
          )}
          <button className="fin-btn">Prepare</button>
          {tpl && <p className="fin-note">You sign: {tpl.signatures.join("; ") || "no signature on this schedule"}.</p>}
        </form>
        {msg && <p>{msg}</p>}
        <h4>Prepared documents</h4>
        <table className="fin-table">
          <thead>
            <tr>
              <th>Form</th>
              <th>Status</th>
              <th>Blank fields</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {docs.map((d) => (
              <tr key={d.id}>
                <td>{d.kind}</td>
                <td>{d.status.replace(/_/g, " ")}</td>
                <td className="fin-note">{d.missing.join(", ") || "none"}</td>
                <td className="fin-note">{String(d.created_at).slice(0, 10)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="fin-note">To fill the official PDF: POST the AcroForm PDF (base64) to /api/finance/documents/:id/fill-pdf. Signature fields are never written.</p>
      </div>
      <div className="fin-card">
        <h3>Credit</h3>
        <span className={"fin-pill " + (persona && persona.creditConnected ? "on" : "off")}>{persona && persona.creditConnected ? "provider connected" : "no provider connected"}</span>{" "}
        <span className={"fin-pill " + (persona && persona.plaidConnected ? "on" : "off")}>{persona && persona.plaidConnected ? "Plaid connected" : "Plaid not connected"}</span>
        <p className="fin-note" style={{ marginTop: 8 }}>
          Pulling a report needs your consent every time. Without a provider, pull your free weekly reports at annualcreditreport.com and upload the score and utilization via POST /api/finance/credit/upload.
        </p>
        <button className="fin-btn" onClick={pull}>
          Pull my credit report
        </button>
        <table className="fin-table" style={{ marginTop: 10 }}>
          <thead>
            <tr>
              <th>Bureau</th>
              <th>Score</th>
              <th>Pulled</th>
            </tr>
          </thead>
          <tbody>
            {credit.map((c) => (
              <tr key={c.id}>
                <td>{c.bureau}</td>
                <td>{c.score}</td>
                <td className="fin-note">{String(c.pulled_at).slice(0, 10)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
