// Passkey Registration using WebAuthn API

document.addEventListener('DOMContentLoaded', () => {
  const registerButton = document.getElementById('registerPasskeyButton');
  const _statusDiv = document.getElementById('passkeyStatus');

  if (registerButton) {
    registerButton.addEventListener('click', registerPasskey);
  }
});

async function registerPasskey() {
  const statusDiv = document.getElementById('passkeyStatus');

  try {
    statusDiv.textContent = 'Requesting passkey registration options...';
    statusDiv.className = 'passkey-status alert alert-info';

    // Step 1: Get registration options from server
    const optionsResponse = await fetch('/passkey/register/options', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    });

    if (!optionsResponse.ok) {
      throw new Error('Failed to get registration options');
    }

    const options = await optionsResponse.json();

    // Step 2: Convert challenge from base64url to ArrayBuffer
    const publicKeyOptions = {
      ...options,
      challenge: base64urlToBuffer(options.challenge),
      user: {
        ...options.user,
        id: base64urlToBuffer(options.user.id)
      },
      excludeCredentials: options.excludeCredentials?.map(cred => ({
        ...cred,
        id: base64urlToBuffer(cred.id)
      }))
    };

    statusDiv.textContent = 'Please follow your device prompts to create passkey...';

    // Step 3: Create credential using WebAuthn
    const credential = await navigator.credentials.create({
      publicKey: publicKeyOptions
    });

    if (!credential) {
      throw new Error('Credential creation failed');
    }

    statusDiv.textContent = 'Verifying passkey...';

    // Step 4: Send credential to server for verification
    const verifyResponse = await fetch('/passkey/register/verify', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        credential: {
          id: credential.id,
          rawId: bufferToBase64url(credential.rawId),
          response: {
            attestationObject: bufferToBase64url(credential.response.attestationObject),
            clientDataJSON: bufferToBase64url(credential.response.clientDataJSON)
          },
          type: credential.type
        }
      })
    });

    if (!verifyResponse.ok) {
      throw new Error('Passkey verification failed');
    }

    statusDiv.textContent = '✓ Passkey registered successfully!';
    statusDiv.className = 'passkey-status alert alert-success';

    // Redirect to security page after 2 seconds
    setTimeout(() => {
      window.location.href = '/security';
    }, 2000);

  } catch (error) {
    console.error('Passkey registration error:', error);
    statusDiv.textContent = `Error: ${error.message}`;
    statusDiv.className = 'passkey-status alert alert-error';
  }
}

// Helper functions for base64url encoding/decoding
function base64urlToBuffer(base64url) {
  const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/');
  const padLen = (4 - (base64.length % 4)) % 4;
  const padded = base64 + '='.repeat(padLen);
  const binary = atob(padded);
  const buffer = new ArrayBuffer(binary.length);
  const bytes = new Uint8Array(buffer);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return buffer;
}

function bufferToBase64url(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  const base64 = btoa(binary);
  return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}
