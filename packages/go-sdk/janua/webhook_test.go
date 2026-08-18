package janua

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"testing"
)

// sign reproduces the server's signing exactly (webhook_dispatcher
// ._calculate_signature / webhooks._generate_signature):
// hmac.new(secret, payload, sha256).hexdigest().
func sign(secret string, payload []byte) string {
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write(payload)
	return hex.EncodeToString(mac.Sum(nil))
}

func TestVerifyWebhookSignature_Valid(t *testing.T) {
	secret := "whsec_test_secret"
	payload := []byte(`{"event":"user.created","data":{"id":"abc"}}`)
	if !VerifyWebhookSignature(payload, sign(secret, payload), secret) {
		t.Fatal("valid signature was rejected")
	}
}

// KnownAnswer pins the exact wire format so Go and the Python server can never
// silently diverge. `want` is HMAC-SHA256("test-secret", "hello") as produced by
// Python's hmac.new(b"test-secret", b"hello", sha256).hexdigest() — computed
// independently, not by this package's own sign() helper.
func TestVerifyWebhookSignature_KnownAnswer(t *testing.T) {
	secret := "test-secret"
	payload := []byte("hello")
	const want = "bcc889a40667cab715e1dc22ad280692cf4bf1c3a280eeeca60d8dbcd8e4b993"

	if got := sign(secret, payload); got != want {
		t.Fatalf("Go HMAC disagrees with the Python server format:\n got  %s\n want %s", got, want)
	}
	// And the verifier accepts that exact server-produced signature.
	if !VerifyWebhookSignature(payload, want, secret) {
		t.Fatal("verify rejected the known-good server signature")
	}
}

func TestVerifyWebhookSignature_WrongSecret(t *testing.T) {
	payload := []byte(`{"event":"user.created"}`)
	sig := sign("correct-secret", payload)
	if VerifyWebhookSignature(payload, sig, "attacker-secret") {
		t.Fatal("signature verified under the wrong secret")
	}
}

func TestVerifyWebhookSignature_TamperedPayload(t *testing.T) {
	secret := "whsec_test_secret"
	sig := sign(secret, []byte(`{"amount":100}`))
	// Attacker keeps the signature but changes the body.
	if VerifyWebhookSignature([]byte(`{"amount":1000000}`), sig, secret) {
		t.Fatal("tampered payload passed verification")
	}
}

func TestVerifyWebhookSignature_EmptySignatureRejected(t *testing.T) {
	// The whole point of the fix: an unsigned delivery must NOT verify.
	if VerifyWebhookSignature([]byte(`{}`), "", "secret") {
		t.Fatal("empty signature was accepted — the placeholder bug is back")
	}
}

func TestVerifyWebhookSignature_EmptySecretRejected(t *testing.T) {
	payload := []byte(`{}`)
	if VerifyWebhookSignature(payload, sign("", payload), "") {
		t.Fatal("empty secret was accepted — an unconfigured consumer must fail closed")
	}
}

func TestVerifyWebhookSignature_Sha256PrefixTolerated(t *testing.T) {
	secret := "whsec_test_secret"
	payload := []byte(`{"event":"ping"}`)
	if !VerifyWebhookSignature(payload, "sha256="+sign(secret, payload), secret) {
		t.Fatal("a sha256= prefixed signature (proxy-forwarded) was rejected")
	}
}

func TestVerifyWebhookSignature_GarbageSignature(t *testing.T) {
	if VerifyWebhookSignature([]byte(`{}`), "not-hex-!!!", "secret") {
		t.Fatal("non-hex garbage verified")
	}
}
