import axios from "axios";

const API = axios.create({
  baseURL: "http://127.0.0.1:8000/api/",
});

API.interceptors.request.use((req) => {
  const token = localStorage.getItem("token");
  const isPublic = req.url.includes("login") || req.url.includes("register");
  if (token && !isPublic) {
    req.headers.Authorization = `Bearer ${token}`;
  }
  return req;
});

export default API;