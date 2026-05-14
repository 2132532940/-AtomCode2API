const express = require("express");
const cors = require("cors");
const {
  API_BASE_URL,
  GITCODE_API_BASE,
  ATOMCODE_USER_AGENT,
  getAccessToken,
  fetchCodingplanModels,
  SERVER_HOST,
  SERVER_PORT,
} = require("./config");

const app = express();
app.use(cors());
app.use(express.json({ limit: "10mb" }));

app.get("/v1/models", async (req, res) => {
  const models = await fetchCodingplanModels();
  const now = Math.floor(Date.now() / 1000);
  const data = (models.length ? models : [{ display_model_name: "deepseek-v4-flash" }])
    .map((m) => ({
      id: m.display_model_name,
      object: "model",
      created: now,
      owned_by: "atomcode-codingplan",
    }));
  res.json({ object: "list", data });
});

app.get("/v1/models/:modelId", async (req, res) => {
  const models = await fetchCodingplanModels();
  const available = models.map((m) => m.display_model_name);
  if (available.includes(req.params.modelId) || req.params.modelId === "deepseek-v4-flash") {
    return res.json({
      id: req.params.modelId,
      object: "model",
      created: Math.floor(Date.now() / 1000),
      owned_by: "atomcode-codingplan",
    });
  }
  res.status(404).json({ error: { message: `Model ${req.params.modelId} not found` } });
});

async function handleChatCompletion(req, res) {
  const apiKey = getAccessToken();
  if (!apiKey) {
    return res.status(401).json({ error: { message: "未找到 Token，请先运行 atomcode login" } });
  }

  const body = req.body;
  const url = `${API_BASE_URL}/chat/completions`;
  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${apiKey}`,
    "User-Agent": ATOMCODE_USER_AGENT,
  };
  const payload = { ...body, stream: body.stream || false };

  try {
    if (payload.stream) {
      res.setHeader("Content-Type", "text/event-stream");
      res.setHeader("Cache-Control", "no-cache");
      res.setHeader("Connection", "keep-alive");
      res.flushHeaders();

      const response = await fetch(url, { method: "POST", headers, body: JSON.stringify(payload) });
      if (!response.ok) {
        res.write(`data: ${JSON.stringify({ error: { message: await response.text(), status: response.status } })}\n\n`);
        res.end();
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6);
            if (data.trim() === "[DONE]") {
              res.write("data: [DONE]\n\n");
            } else {
              res.write(`${line}\n\n`);
            }
          }
        }
      }
      res.end();
    } else {
      const response = await fetch(url, { method: "POST", headers, body: JSON.stringify(payload) });
      if (!response.ok) {
        return res.status(response.status).json({ error: { message: await response.text() } });
      }
      res.json(await response.json());
    }
  } catch (err) {
    if (!res.headersSent) res.status(500).json({ error: { message: `上游请求失败: ${err.message}` } });
  }
}

app.post("/v1/chat/completions", handleChatCompletion);
app.post("/chat/completions", handleChatCompletion);

app.get("/v1/codingplan/models", async (req, res) => {
  const token = getAccessToken();
  if (!token) return res.status(401).json({ error: { message: "未登录" } });
  try {
    const resp = await fetch(`${GITCODE_API_BASE}/coding-plan/models`, { headers: { Authorization: `Bearer ${token}` } });
    res.json(await resp.json());
  } catch (e) {
    res.status(500).json({ error: { message: e.message } });
  }
});

app.get("/v1/codingplan/status", async (req, res) => {
  const token = getAccessToken();
  if (!token) return res.status(401).json({ error: { message: "未登录" } });
  try {
    const resp = await fetch(`${GITCODE_API_BASE}/coding-plan/status`, { headers: { Authorization: `Bearer ${token}` } });
    res.json(await resp.json());
  } catch (e) {
    res.status(500).json({ error: { message: e.message } });
  }
});

app.get("/v1/health", (req, res) => {
  res.json({ status: "ok", token_configured: !!getAccessToken(), service: "AtomCode2API" });
});

app.get("/", (req, res) => {
  res.json({
    service: "AtomCode2API",
    version: "2.0.0",
    endpoints: {
      chat_completions: "/v1/chat/completions",
      models: "/v1/models",
      codingplan_models: "/v1/codingplan/models",
      codingplan_status: "/v1/codingplan/status",
      health: "/v1/health",
    },
  });
});

app.listen(SERVER_PORT, SERVER_HOST, () => {
  console.log(`AtomCode2API 服务已启动`);
  console.log(`  API: http://localhost:${SERVER_PORT}/v1/chat/completions`);
  console.log(`  模型: http://localhost:${SERVER_PORT}/v1/models`);
  console.log(`  Token: ${getAccessToken() ? "已配置" : "未配置"}`);
});
