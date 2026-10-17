// Paperwork to the signature line.
// prepare(kind, data) builds a field map for a known form, lists what is still blank,
// and lists the signature lines left for the owner. fillPdf() writes those fields into
// an AcroForm PDF (the official IRS / SBA / lender PDF) using pdf-lib.

const TEMPLATES = {
  federal_1040: {
    title: "Form 1040 (federal individual return)",
    fields: ["firstName", "lastName", "ssn", "spouseFirstName", "spouseLastName", "spouseSsn", "address", "city", "state", "zip", "filingStatus", "dependents", "w2Wages", "businessNetProfit", "otherIncome", "agi", "deduction", "qbiDeduction", "taxableIncome", "incomeTax", "credits", "selfEmploymentTax", "totalTax", "federalWithheld", "estimatesPaid", "balanceDue", "bankRouting", "bankAccount"],
    signatures: ["Taxpayer signature + date", "Spouse signature + date (if MFJ)"],
    reviewNote: "Have a CPA/EA review Schedule C, SE, and QBI before e-filing.",
  },
  schedule_c: {
    title: "Schedule C (Profit or Loss from Business) - STOiiiC FiT",
    fields: ["businessName", "ein", "businessAddress", "accountingMethod", "grossReceipts", "returnsAllowances", "cogs", "advertising", "carTruck", "contractLabor", "depreciation", "insurance", "interest", "legalProfessional", "officeExpense", "rent", "repairs", "supplies", "taxesLicenses", "travel", "meals", "utilities", "wages", "otherExpenses", "netProfit", "inventoryBegin", "inventoryPurchases", "inventoryEnd"],
    signatures: [],
    reviewNote: "Inventory method must match last year; retail uses cost method by default.",
  },
  nj_1040: {
    title: "NJ-1040 (New Jersey resident return)",
    fields: ["firstName", "lastName", "ssn", "spouseFirstName", "spouseSsn", "address", "city", "state", "zip", "county", "filingStatus", "exemptions", "wages", "businessIncome", "otherIncome", "grossIncome", "exemptionAmount", "taxableIncome", "njTax", "njWithheld", "propertyTaxPaid", "propertyTaxDeductionOrCredit", "balanceDue"],
    signatures: ["Taxpayer signature + date", "Spouse signature + date (if joint)"],
    reviewNote: "Claim the NJ property tax deduction/credit for 2034 Lambert Ave; check the 529 (NJBEST) deduction.",
  },
  sba_1919: {
    title: "SBA Form 1919 (Borrower Information Form) + lender application",
    fields: ["businessName", "ein", "businessAddress", "entityType", "dateEstablished", "naics", "ownerName", "ownerSsn", "ownerPct", "ownerAddress", "citizenship", "loanAmount", "useOfProceeds", "annualRevenue", "netProfit", "existingDebt", "employees", "collateral", "priorGovernmentDebt", "criminalHistory"],
    signatures: ["Applicant/owner signature + date", "Each 20%+ owner signature"],
    reviewNote: "Lender will also want 3 yrs business + personal returns, YTD P&L, balance sheet, debt schedule, and a 12-month projection.",
  },
  heloc_application: {
    title: "HELOC application (Uniform Residential Loan Application 1003 style)",
    fields: ["borrowerName", "borrowerSsn", "coBorrowerName", "coBorrowerSsn", "propertyAddress", "propertyValue", "firstMortgageLender", "firstMortgageBalance", "firstMortgagePayment", "requestedLine", "purpose", "employer", "employmentYears", "monthlyIncome", "businessIncome", "assets", "liabilities", "monthlyDebtPayments", "insuranceCarrier", "propertyTaxAnnual"],
    signatures: ["Borrower signature + date", "Co-borrower signature + date", "Consent to pull credit"],
    reviewNote: "Property: 2034 Lambert Ave. Bring 2 yrs returns, 2 months statements, homeowners insurance declaration, mortgage statement.",
  },
  life_insurance_application: {
    title: "Term life insurance application",
    fields: ["insuredName", "dob", "ssn", "address", "height", "weight", "tobacco", "occupation", "annualIncome", "faceAmount", "termYears", "primaryBeneficiary", "contingentBeneficiary", "existingCoverage", "physicianName", "medications", "riders"],
    signatures: ["Insured signature + date", "Owner signature (if different)", "HIPAA authorization"],
    reviewNote: "Medical exam or e-health records consent usually required above $500k.",
  },
};

function prepare(kind, data = {}) {
  const t = TEMPLATES[kind];
  if (!t) throw new Error("Unknown form kind: " + kind + ". Known: " + Object.keys(TEMPLATES).join(", "));
  const fields = {};
  const missing = [];
  for (const f of t.fields) {
    if (data[f] !== undefined && data[f] !== null && data[f] !== "") fields[f] = data[f];
    else missing.push(f);
  }
  const status = missing.length ? "draft" : "ready_for_signature";
  return { kind, title: t.title, status, fields, missing, signatures: t.signatures, reviewNote: t.reviewNote, completion: Math.round(((t.fields.length - missing.length) / t.fields.length) * 100) };
}

/** Fill an AcroForm PDF. fieldMap: { pdfFieldName: value }. Returns bytes. Signature fields are never touched. */
async function fillPdf(pdfBytes, fieldMap) {
  const { PDFDocument } = require("pdf-lib");
  const doc = await PDFDocument.load(pdfBytes);
  const form = doc.getForm();
  const filled = [];
  const notFound = [];
  for (const [name, value] of Object.entries(fieldMap)) {
    if (/sign/i.test(name)) continue;
    try {
      const field = form.getField(name);
      const type = field.constructor.name;
      if (type === "PDFCheckBox") value ? field.check() : field.uncheck();
      else if (type === "PDFTextField") field.setText(String(value));
      else if (type === "PDFDropdown" || type === "PDFRadioGroup") field.select(String(value));
      filled.push(name);
    } catch (e) {
      notFound.push(name);
    }
  }
  const bytes = await doc.save();
  return { bytes, filled, notFound, availableFields: form.getFields().map((f) => f.getName()) };
}

module.exports = { TEMPLATES, prepare, fillPdf };
