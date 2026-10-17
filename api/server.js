const express = require("express");
const cors = require("cors");
const helmet = require("helmet");

require("dotenv").config();
const authRouter = require("../auth/authRouter.js");
const financeRouter = require("../finance/financeRouter.js");

const server = express();

server.use(logger);
server.use(helmet());
server.use(cors());
server.use(express.json({ limit: "15mb" })); // PDFs for form filling come in as base64

server.use("/api/auth", authRouter); // <<<< can add middlware
server.use("/api/finance", financeRouter); // JWT-protected: the accountant bot, calendar, calculators

server.get("/", (req, res) => {
  res.json({ message: "This one's for IAN" });
});

function logger(req, res, next) {
  console.log(
    `[${new Date().toISOString()}] ${req.method} to ${req.url} from ${req.get(
      "host"
    )}`
  );
  next();
}

module.exports = server;
