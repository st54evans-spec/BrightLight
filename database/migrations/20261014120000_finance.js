exports.up = async function (knex) {
  await knex.schema.createTable("finance_profile", (t) => {
    t.increments();
    t.integer("user_id").unsigned().references("id").inTable("users").onDelete("CASCADE");
    t.text("data").notNullable().defaultTo("{}"); // JSON
    t.timestamp("updated_at").defaultTo(knex.fn.now());
  });

  await knex.schema.createTable("finance_events", (t) => {
    t.increments();
    t.integer("user_id").unsigned().references("id").inTable("users").onDelete("CASCADE");
    t.string("date", 10).notNullable().index();
    t.string("title", 255).notNullable();
    t.string("category", 50).notNullable().defaultTo("other"); // tax | bill | invoice | bookkeeping | planning | compliance | loan | insurance
    t.string("jurisdiction", 30).defaultTo("");
    t.string("form", 100).defaultTo("");
    t.decimal("amount", 14, 2);
    t.string("status", 20).notNullable().defaultTo("pending"); // pending | done | skipped
    t.string("source", 20).notNullable().defaultTo("manual"); // seed | manual | bot
    t.text("notes");
    t.timestamp("created_at").defaultTo(knex.fn.now());
  });

  await knex.schema.createTable("finance_accounts", (t) => {
    t.increments();
    t.integer("user_id").unsigned().references("id").inTable("users").onDelete("CASCADE");
    t.string("name", 120).notNullable();
    t.string("type", 30).notNullable(); // checking | savings | credit | loan | mortgage | heloc | investment | retirement | 529
    t.string("institution", 120);
    t.decimal("balance", 14, 2).notNullable().defaultTo(0);
    t.decimal("rate", 7, 5); // annual, e.g. 0.0675
    t.decimal("payment", 12, 2); // monthly minimum
    t.boolean("is_business").notNullable().defaultTo(false);
    t.string("external_id", 120);
    t.timestamp("updated_at").defaultTo(knex.fn.now());
  });

  await knex.schema.createTable("finance_transactions", (t) => {
    t.increments();
    t.integer("user_id").unsigned().references("id").inTable("users").onDelete("CASCADE");
    t.integer("account_id").unsigned().references("id").inTable("finance_accounts").onDelete("SET NULL");
    t.string("date", 10).notNullable().index();
    t.decimal("amount", 14, 2).notNullable(); // positive = inflow, negative = outflow
    t.string("category", 60).notNullable().defaultTo("uncategorized");
    t.string("description", 255);
    t.boolean("is_business").notNullable().defaultTo(false);
    t.string("external_id", 120);
  });

  await knex.schema.createTable("finance_goals", (t) => {
    t.increments();
    t.integer("user_id").unsigned().references("id").inTable("users").onDelete("CASCADE");
    t.string("name", 120).notNullable();
    t.string("type", 30).notNullable(); // retirement | education | loan | heloc | insurance | move | emergency
    t.decimal("target_amount", 14, 2);
    t.string("target_date", 10);
    t.decimal("current_amount", 14, 2).defaultTo(0);
    t.text("notes");
  });

  await knex.schema.createTable("finance_documents", (t) => {
    t.increments();
    t.integer("user_id").unsigned().references("id").inTable("users").onDelete("CASCADE");
    t.string("kind", 40).notNullable(); // federal_1040 | schedule_c | nj_1040 | sba_1919 | loan_application | heloc_application | life_insurance_application
    t.string("status", 30).notNullable().defaultTo("draft"); // draft | ready_for_signature | signed | filed
    t.text("fields").notNullable().defaultTo("{}"); // JSON of filled values
    t.text("missing").notNullable().defaultTo("[]"); // JSON list of fields still blank
    t.text("signatures").notNullable().defaultTo("[]"); // JSON list of signature lines left for the owner
    t.timestamp("created_at").defaultTo(knex.fn.now());
  });

  await knex.schema.createTable("finance_messages", (t) => {
    t.increments();
    t.integer("user_id").unsigned().references("id").inTable("users").onDelete("CASCADE");
    t.string("role", 20).notNullable(); // user | assistant | tool
    t.text("content").notNullable();
    t.text("meta"); // JSON: tool calls, citations
    t.timestamp("created_at").defaultTo(knex.fn.now());
  });

  await knex.schema.createTable("finance_integrations", (t) => {
    t.increments();
    t.integer("user_id").unsigned().references("id").inTable("users").onDelete("CASCADE");
    t.string("provider", 40).notNullable(); // plaid | credit | xai
    t.text("token"); // access token; encrypt at rest in production
    t.text("meta");
    t.timestamp("created_at").defaultTo(knex.fn.now());
  });

  await knex.schema.createTable("finance_credit_reports", (t) => {
    t.increments();
    t.integer("user_id").unsigned().references("id").inTable("users").onDelete("CASCADE");
    t.string("bureau", 30);
    t.integer("score");
    t.boolean("consent").notNullable().defaultTo(false);
    t.text("data"); // JSON
    t.timestamp("pulled_at").defaultTo(knex.fn.now());
  });
};

exports.down = async function (knex) {
  for (const t of [
    "finance_credit_reports",
    "finance_integrations",
    "finance_messages",
    "finance_documents",
    "finance_goals",
    "finance_transactions",
    "finance_accounts",
    "finance_events",
    "finance_profile",
  ]) {
    await knex.schema.dropTableIfExists(t);
  }
};
