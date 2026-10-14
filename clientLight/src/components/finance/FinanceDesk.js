import React, { useEffect, useState } from "react";
import Navbar from "../navbar/navbar";
import ChatPanel from "./ChatPanel";
import CalendarPanel from "./CalendarPanel";
import ChartsPanel from "./ChartsPanel";
import LendingPanel from "./LendingPanel";
import PlanPanel from "./PlanPanel";
import MovePanel from "./MovePanel";
import PaperworkPanel from "./PaperworkPanel";
import { financeApi } from "../../utils/api";
import "./finance.css";

const TABS = ["Desk", "Charts", "Lending", "Taxes & Plan", "The Move", "Paperwork"];

export default function FinanceDesk(props) {
  const [persona, setPersona] = useState(null);
  const [tab, setTab] = useState("Desk");
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!localStorage.getItem("token")) {
      props.history.push("/login");
      return;
    }
    financeApi()
      .get("/persona")
      .then((r) => setPersona(r.data))
      .catch((e) => setErr((e.response && e.response.data && e.response.data.message) || e.message));
  }, [props.history]);

  return (
    <div className="fin-page">
      <Navbar {...props} />
      <div className="fin-head">
        <h1>{persona ? persona.name : "Finance Desk"}</h1>
        <span className="sub">{persona ? persona.title + " · " + persona.profile.business.name : ""}</span>
        <div className="fin-status">
          {persona && (
            <React.Fragment>
              <span className={"fin-pill " + (persona.grokConnected ? "on" : "off")}>Grok {persona.grokConnected ? "on" : "off"}</span>
              <span className={"fin-pill " + (persona.plaidConnected ? "on" : "off")}>Bank data {persona.plaidConnected ? "on" : "off"}</span>
              <span className={"fin-pill " + (persona.creditConnected ? "on" : "off")}>Credit {persona.creditConnected ? "on" : "off"}</span>
            </React.Fragment>
          )}
        </div>
      </div>
      <div className="fin-body">
        {err && <div className="fin-card" style={{ color: "#d9534f" }}>{err}</div>}
        <div className="fin-tabs">
          {TABS.map((t) => (
            <button key={t} className={tab === t ? "on" : ""} onClick={() => setTab(t)}>
              {t}
            </button>
          ))}
        </div>
        {tab === "Desk" && (
          <div className="fin-grid">
            <ChatPanel persona={persona} />
            <CalendarPanel />
          </div>
        )}
        {tab === "Charts" && <ChartsPanel />}
        {tab === "Lending" && <LendingPanel />}
        {tab === "Taxes & Plan" && <PlanPanel />}
        {tab === "The Move" && <MovePanel />}
        {tab === "Paperwork" && <PaperworkPanel persona={persona} />}
      </div>
    </div>
  );
}
