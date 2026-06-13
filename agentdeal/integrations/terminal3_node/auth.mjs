// Terminal 3 identity sidecar.
//
// The Terminal 3 ADK is a Node-only SDK (SIWE auth + encrypted TEE session +
// a WASM crypto component) - there is no REST API. The Python identity adapter
// shells out to this script to authenticate with the developer key and read the
// real tenant DID straight off the authenticated session (never derived/hardcoded).
//
// Usage:  T3N_API_KEY=0x... node auth.mjs
// Output (stdout, one line of JSON):
//   {"ok": true, "address": "0x..", "did": "did:t3n:..", "env": "testnet"}
//   {"ok": false, "error": "..."}

const KEY = process.env.T3N_API_KEY;
const ENV = process.env.T3N_ENV || "testnet";

function emit(obj) {
  process.stdout.write(JSON.stringify(obj) + "\n");
}

if (!KEY) {
  emit({ ok: false, error: "T3N_API_KEY not set" });
  process.exit(1);
}

try {
  const sdk = await import("@terminal3/t3n-sdk");
  const {
    T3nClient,
    setEnvironment,
    loadWasmComponent,
    eth_get_address,
    metamask_sign,
    createEthAuthInput,
  } = sdk;

  setEnvironment(ENV); // "testnet" | "production" - SDK resolves the node URL

  const wasmComponent = await loadWasmComponent(); // all crypto runs in the WASM component
  const address = eth_get_address(KEY);

  const t3n = new T3nClient({
    wasmComponent,
    // EthSign signs the login challenge with the developer key.
    handlers: { EthSign: metamask_sign(address, undefined, KEY) },
  });

  await t3n.handshake();
  const did = await t3n.authenticate(createEthAuthInput(address));

  // Golden rule: read the tenant DID back off the authenticated session.
  emit({ ok: true, address, did: did?.value ?? String(did), env: ENV });
  process.exit(0);
} catch (err) {
  emit({ ok: false, error: err?.message ? String(err.message) : String(err) });
  process.exit(1);
}
