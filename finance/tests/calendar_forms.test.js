const test = require("node:test");
const assert = require("node:assert/strict");
const calendar = require("../calendar");
const forms = require("../integrations/forms");

test("tax deadlines land on business days and include NJ sales tax", () => {
  const ev = calendar.taxDeadlines(2026);
  for (const e of ev) {
    const d = new Date(e.date + "T12:00:00Z").getUTCDay();
    assert.ok(d !== 0 && d !== 6, e.title + " on weekend");
  }
  assert.ok(ev.some((e) => e.form === "ST-50"));
  assert.ok(ev.some((e) => /1040-ES/.test(e.form)));
  // 2026-01-15 is a Thursday; 2026-04-15 is a Wednesday
  assert.ok(ev.some((e) => e.date === "2026-04-15" && /1040/.test(e.form)));
});

test("S-corp entity moves the business return to March 15", () => {
  const ev = calendar.taxDeadlines(2027, "S-Corp");
  assert.ok(ev.some((e) => e.date === "2027-03-15" && /1120-S/.test(e.form)));
});

test("recurring rules expand and buildYear sorts", () => {
  const y = calendar.buildYear(2026);
  assert.ok(y.length > 80);
  for (let i = 1; i < y.length; i++) assert.ok(y[i].date >= y[i - 1].date);
  assert.equal(y.filter((e) => e.category === "invoice").length, 24);
  assert.ok(y.filter((e) => e.category === "bookkeeping").length >= 52);
});

test("forms.prepare lists missing fields and signature lines", () => {
  const p = forms.prepare("heloc_application", { borrowerName: "Owner", propertyAddress: "2034 Lambert Ave", requestedLine: 95000 });
  assert.equal(p.status, "draft");
  assert.ok(p.missing.includes("borrowerSsn"));
  assert.ok(p.signatures.length >= 2);
  assert.ok(p.completion > 0 && p.completion < 100);
  assert.throws(() => forms.prepare("nope"), /Unknown form kind/);
});

test("forms.fillPdf writes text fields and skips signatures", async () => {
  const { PDFDocument } = require("pdf-lib");
  const doc = await PDFDocument.create();
  const page = doc.addPage([400, 400]);
  const form = doc.getForm();
  const name = form.createTextField("borrowerName");
  name.addToPage(page, { x: 20, y: 300, width: 200, height: 20 });
  const sig = form.createTextField("borrowerSignature");
  sig.addToPage(page, { x: 20, y: 200, width: 200, height: 20 });
  const bytes = await doc.save();
  const out = await forms.fillPdf(bytes, { borrowerName: "Owner", borrowerSignature: "X", missingField: "y" });
  assert.deepEqual(out.filled, ["borrowerName"]);
  assert.deepEqual(out.notFound, ["missingField"]);
  const reloaded = await PDFDocument.load(out.bytes);
  assert.equal(reloaded.getForm().getTextField("borrowerName").getText(), "Owner");
  assert.equal(reloaded.getForm().getTextField("borrowerSignature").getText(), undefined);
});
