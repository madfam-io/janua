import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { SignJWT, exportJWK, generateKeyPair } from 'jose';
import type { JWK, KeyLike } from 'jose';
import { verify } from './index';

const ISSUER = 'https://auth.example.test';
const AUDIENCE = 'test-audience';
const KID = 'test-key-1';

// Placeholder only — a real x5c entry is a base64 DER certificate. The verifier
// must ignore it and build the key from the JWK's n/e members instead.
const PLACEHOLDER_X5C = Buffer.from('placeholder-der-certificate-bytes').toString('base64');

let urlCounter = 0;
// The module-level JWKS cache is keyed by URL, so each test uses its own URL
// to stay isolated from previous fetches.
function uniqueJwksUrl(): string {
  urlCounter += 1;
  return `${ISSUER}/.well-known/jwks-${urlCounter}.json`;
}

function stubJWKSFetch(keys: JWK[]) {
  const fetchMock = vi.fn(
    async () =>
      new Response(JSON.stringify({ keys }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
  );
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

describe('verify with JWKS', () => {
  let privateKey: KeyLike;
  let publicJwk: JWK;

  beforeEach(async () => {
    const pair = await generateKeyPair('RS256', { extractable: true });
    privateKey = pair.privateKey;
    publicJwk = await exportJWK(pair.publicKey);
    publicJwk.kid = KID;
    publicJwk.use = 'sig';
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  async function signToken(options: { kid?: string; expired?: boolean; key?: KeyLike } = {}) {
    const nowSeconds = Math.floor(Date.now() / 1000);
    return new SignJWT({ userId: 'user-123', email: 'user@example.test' })
      .setProtectedHeader({
        alg: 'RS256',
        ...(options.kid !== undefined && { kid: options.kid }),
      })
      .setIssuedAt(options.expired ? nowSeconds - 600 : nowSeconds)
      .setIssuer(ISSUER)
      .setAudience(AUDIENCE)
      .setExpirationTime(options.expired ? nowSeconds - 300 : nowSeconds + 300)
      .sign(options.key ?? privateKey);
  }

  it('verifies a token against a JWKS key that includes x5c', async () => {
    publicJwk.alg = 'RS256';
    publicJwk.x5c = [PLACEHOLDER_X5C];
    stubJWKSFetch([publicJwk]);

    const token = await signToken({ kid: KID });
    const result = await verify(token, {
      jwksUrl: uniqueJwksUrl(),
      issuer: ISSUER,
      audience: AUDIENCE,
    });

    expect(result.error).toBeUndefined();
    expect(result.valid).toBe(true);
    expect(result.payload?.userId).toBe('user-123');
    expect(result.payload?.iss).toBe(ISSUER);
  });

  it('verifies when the JWKS key has no alg member', async () => {
    delete publicJwk.alg;
    publicJwk.x5c = [PLACEHOLDER_X5C];
    stubJWKSFetch([publicJwk]);

    const token = await signToken({ kid: KID });
    const result = await verify(token, {
      jwksUrl: uniqueJwksUrl(),
      issuer: ISSUER,
      audience: AUDIENCE,
    });

    expect(result.error).toBeUndefined();
    expect(result.valid).toBe(true);
  });

  it('rejects a token whose kid has no match in the JWKS', async () => {
    publicJwk.alg = 'RS256';
    stubJWKSFetch([publicJwk]);

    const token = await signToken({ kid: 'unknown-key' });
    const result = await verify(token, { jwksUrl: uniqueJwksUrl() });

    expect(result.valid).toBe(false);
    expect(result.error).toBe('No matching key found in JWKS');
  });

  it('rejects a token without a kid header', async () => {
    publicJwk.alg = 'RS256';
    stubJWKSFetch([publicJwk]);

    const token = await signToken();
    const result = await verify(token, { jwksUrl: uniqueJwksUrl() });

    expect(result.valid).toBe(false);
    expect(result.error).toBe('No kid in token header');
  });

  it('rejects a token signed by a different key with the same kid', async () => {
    publicJwk.alg = 'RS256';
    stubJWKSFetch([publicJwk]);

    const impostor = await generateKeyPair('RS256', { extractable: true });
    const token = await signToken({ kid: KID, key: impostor.privateKey });
    const result = await verify(token, { jwksUrl: uniqueJwksUrl() });

    expect(result.valid).toBe(false);
  });

  it('flags expired tokens', async () => {
    publicJwk.alg = 'RS256';
    stubJWKSFetch([publicJwk]);

    const token = await signToken({ kid: KID, expired: true });
    const result = await verify(token, { jwksUrl: uniqueJwksUrl() });

    expect(result.valid).toBe(false);
    expect(result.expired).toBe(true);
  });

  it('caches the JWKS per URL', async () => {
    publicJwk.alg = 'RS256';
    const fetchMock = stubJWKSFetch([publicJwk]);
    const token = await signToken({ kid: KID });

    const firstUrl = uniqueJwksUrl();
    await verify(token, { jwksUrl: firstUrl });
    await verify(token, { jwksUrl: firstUrl });
    expect(fetchMock).toHaveBeenCalledTimes(1);

    await verify(token, { jwksUrl: uniqueJwksUrl() });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
