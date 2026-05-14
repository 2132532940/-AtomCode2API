const fs = require("fs");
const path = require("path");
const os = require("os");
const toml = require("toml");

const ATOMCODE_CONFIG_DIR = path.join(os.homedir(), ".atomcode");
const ATOMCODE_CONFIG_PATH = path.join(ATOMCODE_CONFIG_DIR, "config.toml");
const ATOMCODE_AUTH_PATH = path.join(ATOMCODE_CONFIG_DIR, "auth.toml");

const API_BASE_URL = "https://api-ai.gitcode.com/v1";
const GITCODE_API_BASE = "https://api.gitcode.com/api/v5";
const ATOMCODE_USER_AGENT = "atomcode/4.22.0";

let cachedToken = null;
let tokenExpiresAt = 0;
let cachedModels = null;
let modelsCachedAt = 0;
const MODELS_CACHE_TTL = 300000;

function loadToml(filePath) {
  try {
    if (fs.existsSync(filePath)) return toml.parse(fs.readFileSync(filePath, "utf-8"));
  } catch {}
  return {};
}

function getAccessToken() {
  if (process.env.ATOMCODE_API_KEY) return process.env.ATOMCODE_API_KEY;
  if (cachedToken && Date.now() < tokenExpiresAt) return cachedToken;

  const auth = loadToml(ATOMCODE_AUTH_PATH);
  const refreshToken = auth.refresh_token;

  if (refreshToken) {
    try {
      const resp = require("child_process").execSync(
        `curl -s --max-time 10 -X POST "https://acs.atomgit.com/oauth/refresh" -H "Content-Type: application/json" -d '{"refresh_token":"${refreshToken"}'`,
        { encoding: "utf-8" }
      );
      const data = JSON.parse(resp);
      if (data.access_token) {
        cachedToken = data.access_token;
        tokenExpiresAt = Date.now() + 86400000 * 6;
        return data.access_token;
      }
    } catch {}
  }

  return auth.access_token || null;
}

async function fetchCodingplanModels() {
  if (cachedModels && Date.now() - modelsCachedAt < MODELS_CACHE_TTL) return cachedModels;
  const token = getAccessToken();
  if (!token) return [];
  try {
    const resp = await fetch(`${GITCODE_API_BASE}/coding-plan/models`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (resp.ok) {
      const data = await resp.json();
      if (Array.isArray(data)) {
        cachedModels = data;
        modelsCachedAt = Date.now();
        return data;
      }
    }
  } catch {}
  return cachedModels || [];
}

module.exports = {
  ATOMCODE_CONFIG_DIR,
  API_BASE_URL,
  GITCODE_API_BASE,
  ATOMCODE_USER_AGENT,
  loadToml,
  getAccessToken,
  fetchCodingplanModels,
  SERVER_HOST: process.env.PROXY_HOST || "0.0.0.0",
  SERVER_PORT: parseInt(process.env.PROXY_PORT || "8001"),
  DEFAULT_MODEL: process.env.DEFAULT_MODEL || "deepseek-v4-flash",
};
