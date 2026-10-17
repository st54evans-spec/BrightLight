const jwt = require("jsonwebtoken");
const secret = require("../config/secret.js");

// Accepts "Authorization: <token>" (what axiosWithAuth sends) or "Bearer <token>".
module.exports = (req, res, next) => {
  const header = req.headers.authorization || "";
  const token = header.startsWith("Bearer ") ? header.slice(7) : header;
  if (!token) return res.status(401).json({ message: "Missing token" });
  jwt.verify(token, secret.jwtSecret, (err, decoded) => {
    if (err) return res.status(401).json({ message: "Invalid token" });
    req.user = { id: decoded.id, username: decoded.usersname || decoded.username };
    next();
  });
};
