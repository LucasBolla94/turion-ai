import express from "express";
import { WebSocketServer } from "ws";
import makeWASocket, {
  useMultiFileAuthState,
  fetchLatestBaileysVersion,
  makeInMemoryStore,
} from "@whiskeysockets/baileys";
import pino from "pino";

const PORT = process.env.PORT || 3001;
const API_KEY = process.env.API_KEY || "";

const app = express();
app.use(express.json());

function requireKey(req, res, next) {
  if (!API_KEY) return next();
  const key = req.headers["x-api-key"];
  if (key !== API_KEY) return res.status(401).json({ error: "unauthorized" });
  return next();
}

const server = app.listen(PORT, () => {
  console.log(`WhatsApp gateway listening on :${PORT}`);
});

const wss = new WebSocketServer({ server, path: "/events" });
const clients = new Set();

wss.on("connection", (ws) => {
  clients.add(ws);
  ws.on("close", () => clients.delete(ws));
});

function broadcast(event) {
  const payload = JSON.stringify(event);
  for (const client of clients) {
    try {
      client.send(payload);
    } catch (_) {
      // ignore broken clients
    }
  }
}

const logger = pino({ level: "info" });
const store = makeInMemoryStore({ logger });

let sock;
let currentQR = null;

async function startSocket() {
  const { state, saveCreds } = await useMultiFileAuthState("./data");
  const { version } = await fetchLatestBaileysVersion();

  sock = makeWASocket({
    version,
    auth: state,
    logger,
    printQRInTerminal: true,
  });

  store.bind(sock.ev);

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("connection.update", (update) => {
    if (update.qr) {
      currentQR = update.qr;
      broadcast({ type: "qr", data: update.qr });
    }

    if (update.connection === "open") {
      broadcast({ type: "status", data: "connected" });
    }

    if (update.connection === "close") {
      broadcast({ type: "status", data: "disconnected" });
      startSocket().catch(() => {});
    }
  });

  sock.ev.on("messages.upsert", async ({ messages }) => {
    for (const msg of messages) {
      if (!msg.message || msg.key.fromMe) continue;
      const from = msg.key.remoteJid || "";
      const text =
        msg.message.conversation ||
        msg.message.extendedTextMessage?.text ||
        "";
      if (!text) continue;
      broadcast({ type: "message", from, text });
    }
  });
}

app.get("/health", (_req, res) => res.json({ ok: true }));
app.get("/qr", requireKey, (_req, res) => res.json({ qr: currentQR }));

app.post("/send", requireKey, async (req, res) => {
  const { to, text } = req.body || {};
  if (!to || !text) return res.status(400).json({ error: "missing to/text" });
  try {
    await sock.sendMessage(to, { text });
    return res.json({ ok: true });
  } catch (err) {
    return res.status(500).json({ error: "send failed" });
  }
});

startSocket().catch((err) => {
  console.error("Failed to start Baileys", err);
  process.exit(1);
});
