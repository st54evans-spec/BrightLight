import axios from "axios";

// Point the client at the API. Local dev: REACT_APP_API_URL=http://localhost:3111
export const API_URL = process.env.REACT_APP_API_URL || "https://quietlight-db.herokuapp.com";

export const financeApi = () =>
  axios.create({
    baseURL: API_URL + "/api/finance",
    headers: { Authorization: localStorage.getItem("token") || "" },
  });

export const money = (n) =>
  n == null || isNaN(n) ? "-" : Number(n).toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export const pct = (n) => (n == null ? "-" : (Number(n) * 100).toFixed(2) + "%");
