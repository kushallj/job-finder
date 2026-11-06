// Jobify inbox: Cloudflare Email Worker (free with Email Routing).
//
// Route: Email Routing -> Catch-all address on INBOX_DOMAIN -> "Send to a Worker" -> this worker.
// Every message to <anything>@INBOX_DOMAIN is POSTed raw to the Jobify API, signed with
// HMAC-SHA256(INBOUND_WEBHOOK_SECRET, "<unix seconds>.<raw bytes>") so the API can reject
// forged or replayed deliveries. Setup steps: CLAUDE.md -> "Jobify inbox".

const DEFAULT_MAX_BYTES = 10 * 1024 * 1024;

export default {
  async email(message, env) {
    const maxBytes = Number(env.MAX_BYTES || DEFAULT_MAX_BYTES);
    if (message.rawSize > maxBytes) {
      message.setReject("Message too large");
      return;
    }
    const raw = new Uint8Array(await new Response(message.raw).arrayBuffer());
    const timestamp = Math.floor(Date.now() / 1000).toString();
    const signature = await hmacHex(env.INBOUND_WEBHOOK_SECRET, timestamp, raw);

    const res = await fetch(env.INBOUND_URL, {
      method: "POST",
      headers: {
        "Content-Type": "message/rfc822",
        "X-Jobify-Timestamp": timestamp,
        "X-Jobify-Signature": signature,
        "X-Jobify-Envelope-To": message.to,
      },
      body: raw,
    });
    if (res.status === 413) {
      message.setReject("Message too large");
    } else if (!res.ok) {
      // Fail the delivery so it shows up in Email Routing activity instead of vanishing.
      throw new Error(`Jobify API responded ${res.status}`);
    }
  },
};

export async function hmacHex(secret, timestamp, body) {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const prefix = enc.encode(`${timestamp}.`);
  const data = new Uint8Array(prefix.length + body.length);
  data.set(prefix);
  data.set(body, prefix.length);
  const mac = new Uint8Array(await crypto.subtle.sign("HMAC", key, data));
  return Array.from(mac, (b) => b.toString(16).padStart(2, "0")).join("");
}
