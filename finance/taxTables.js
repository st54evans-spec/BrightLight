// Federal and New Jersey tax tables.
// VERIFY EVERY JANUARY. Federal figures follow IRS Rev. Proc. 2025-32 (tax year 2026).
// NJ Gross Income Tax rates have been unchanged for years; confirm against NJ-1040 instructions.

const FEDERAL = {
  2026: {
    standardDeduction: { single: 16100, mfj: 32200, hoh: 24150, mfs: 16100 },
    brackets: {
      single: [
        [12400, 0.1],
        [50400, 0.12],
        [105700, 0.22],
        [201775, 0.24],
        [256225, 0.32],
        [640600, 0.35],
        [Infinity, 0.37],
      ],
      mfj: [
        [24800, 0.1],
        [100800, 0.12],
        [211400, 0.22],
        [403550, 0.24],
        [512450, 0.32],
        [768700, 0.35],
        [Infinity, 0.37],
      ],
      hoh: [
        [17700, 0.1],
        [67450, 0.12],
        [105700, 0.22],
        [201775, 0.24],
        [256225, 0.32],
        [640600, 0.35],
        [Infinity, 0.37],
      ],
    },
    childTaxCredit: 2200,
    seTaxRate: 0.153,
    ssWageBase: 184500,
    medicareRate: 0.029,
    qbiDeductionRate: 0.2,
  },
};
FEDERAL[2026].brackets.mfs = FEDERAL[2026].brackets.single;

const NJ = {
  // NJ has no standard deduction; personal exemptions instead.
  exemptions: { personal: 1000, dependent: 1500 },
  brackets: {
    single: [
      [20000, 0.014],
      [35000, 0.0175],
      [40000, 0.035],
      [75000, 0.05525],
      [500000, 0.0637],
      [1000000, 0.0897],
      [Infinity, 0.1075],
    ],
    mfj: [
      [20000, 0.014],
      [50000, 0.0175],
      [70000, 0.0245],
      [80000, 0.035],
      [150000, 0.05525],
      [500000, 0.0637],
      [1000000, 0.0897],
      [Infinity, 0.1075],
    ],
  },
  salesTaxRate: 0.06625,
};
NJ.brackets.hoh = NJ.brackets.mfj;
NJ.brackets.mfs = NJ.brackets.single;

function taxFromBrackets(taxable, brackets) {
  let tax = 0;
  let lower = 0;
  for (const [upper, rate] of brackets) {
    if (taxable <= lower) break;
    const slice = Math.min(taxable, upper) - lower;
    tax += slice * rate;
    lower = upper;
  }
  return tax;
}

module.exports = { FEDERAL, NJ, taxFromBrackets };
