// Credit report pulls.
// Consumer credit APIs (Experian Connect, Array, CRS, Stitch Credit) all require a signed
// agreement and the consumer's written consent (FCRA permissible purpose). This module
// talks to any provider that exposes a simple JSON endpoint:
//   POST $CREDIT_API_URL  { consumer: {...}, consent: true }  ->  { bureau, score, report }
// Set CREDIT_API_URL and CREDIT_API_KEY. Without them the owner can paste a report
// pulled from annualcreditreport.com (free weekly) via POST /api/finance/credit/upload.

function configured() {
  return !!(process.env.CREDIT_API_URL && process.env.CREDIT_API_KEY);
}

async function pull({ consumer, consent }) {
  if (!consent) throw new Error("Written consent is required before pulling a credit report.");
  if (!configured()) {
    return {
      status: "not_connected",
      message:
        "No credit provider connected. Set CREDIT_API_URL and CREDIT_API_KEY, or upload a report from annualcreditreport.com (free weekly) at POST /api/finance/credit/upload.",
    };
  }
  const res = await fetch(process.env.CREDIT_API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: "Bearer " + process.env.CREDIT_API_KEY },
    body: JSON.stringify({ consumer, consent: true, purpose: "consumer_initiated" }),
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.message || "Credit provider error " + res.status);
  return { status: "ok", bureau: json.bureau, score: json.score, report: json.report || json };
}

/** What lenders look at, from a parsed report. */
function analyze(report) {
  const score = report.score || null;
  const tier = score == null ? "unknown" : score >= 760 ? "excellent" : score >= 720 ? "very good" : score >= 680 ? "good" : score >= 640 ? "fair" : "poor";
  const util = report.utilization != null ? report.utilization : null;
  const tips = [];
  if (util != null && util > 0.3) tips.push("Pay revolving balances under 30% utilization before applying; under 10% for the best HELOC tier.");
  if (report.latePayments) tips.push("Late payments on file: ask for goodwill removal letters; avoid any new lates for 12 months.");
  if (report.inquiries > 3) tips.push("Hard inquiries are high; cluster loan shopping inside a 14 day window.");
  if (!tips.length) tips.push("Profile is clean. Shop lenders within 14 days so inquiries count once.");
  return { score, tier, utilization: util, tips };
}

module.exports = { configured, pull, analyze };
