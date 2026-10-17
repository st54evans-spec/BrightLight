import React, { useEffect, useRef, useState } from "react";
import { financeApi } from "../../utils/api";

const QUICK = [
  "What is due in the next 30 days?",
  "Estimate our 2026 federal and NJ taxes.",
  "Compare lenders for a $250,000 loan, low payments year one.",
  "Size a HELOC on 2034 Lambert Ave to clear all debt plus $60k renovation.",
  "Can the numbers back a STOiiiC FiT move costing $20k?",
  "How much life insurance do we need?",
  "Build a retirement and Brynlee 529 plan.",
  "Price 40 hoodies at $18 cost to sell in 30 days for top dollar.",
];

export default function ChatPanel({ persona }) {
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const logRef = useRef(null);

  const load = () =>
    financeApi()
      .get("/messages")
      .then((r) => setMessages(r.data))
      .catch((e) => setError(e.message));

  useEffect(() => {
    load();
  }, []);
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [messages, busy]);

  const send = (msg) => {
    const m = (msg || text).trim();
    if (!m || busy) return;
    setBusy(true);
    setError("");
    setText("");
    setMessages((prev) => [...prev, { id: "tmp", role: "user", content: m }]);
    financeApi()
      .post("/chat", { message: m })
      .then((r) => {
        setMessages((prev) => [
          ...prev.filter((x) => x.id !== "tmp"),
          { id: "u" + Date.now(), role: "user", content: m },
          { id: r.data.id, role: "assistant", content: r.data.reply, meta: JSON.stringify({ toolCalls: r.data.toolCalls }) },
        ]);
      })
      .catch((e) => setError((e.response && e.response.data && e.response.data.message) || e.message))
      .finally(() => setBusy(false));
  };

  const clear = () =>
    financeApi()
      .delete("/messages")
      .then(() => setMessages([]));

  const name = (persona && persona.name) || "Accountant";

  return (
    <div className="fin-card fin-chat">
      <h3>
        Talk to {name}{" "}
        <span className={"fin-pill " + (persona && persona.grokConnected ? "on" : "off")}>{persona && persona.grokConnected ? "Grok " + persona.model : "Grok offline"}</span>
      </h3>
      <div className="fin-quick">
        {QUICK.map((q) => (
          <button key={q} onClick={() => send(q)}>
            {q}
          </button>
        ))}
      </div>
      <div className="fin-chat-log" ref={logRef}>
        {messages.length === 0 && <div className="fin-note">No messages yet. Ask {name} what is due, or pick a prompt above.</div>}
        {messages.map((m) => {
          let tools = [];
          try {
            tools = (m.meta && JSON.parse(m.meta).toolCalls) || [];
          } catch (e) {
            tools = [];
          }
          return (
            <div key={m.id} className={"fin-msg " + m.role}>
              <div className="who">{m.role === "user" ? "You" : name}</div>
              {m.content}
              {tools.length > 0 && <div className="tools">ran: {tools.map((t) => t.name).join(", ")}</div>}
            </div>
          );
        })}
        {busy && <div className="fin-msg assistant">{name} is running the numbers...</div>}
      </div>
      {error && <div style={{ color: "#d9534f", marginTop: 6 }}>{error}</div>}
      <div className="fin-chat-input">
        <textarea
          value={text}
          placeholder={"Ask " + name + " anything about the money."}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
        />
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <button className="fin-btn" onClick={() => send()} disabled={busy}>
            Send
          </button>
          <button className="fin-btn ghost" onClick={clear}>
            Clear
          </button>
        </div>
      </div>
    </div>
  );
}
