import { Router, Request, Response } from 'express';
import crypto from 'crypto';

export const mfaRouter = Router();

/**
 * Generate a cryptographically secure random string
 * Uses crypto.randomBytes for security-critical random generation
 */
function generateSecureRandom(length: number): string {
  return crypto.randomBytes(length).toString('base64url').slice(0, length);
}

/**
 * Generate a cryptographically secure backup code
 */
function generateBackupCode(): string {
  const part1 = crypto.randomBytes(4).toString('hex').toUpperCase().slice(0, 4);
  const part2 = crypto.randomBytes(4).toString('hex').toUpperCase().slice(0, 4);
  return `BACKUP-${part1}-${part2}`;
}

// Get MFA status
mfaRouter.get('/status', (_req: Request, res: Response) => {
  res.json({
    enabled: false,
    methods: [],
    backupCodesRemaining: 0
  });
});

// Enable MFA
mfaRouter.post('/enable', (req: Request, res: Response) => {
  const { method } = req.body;

  if (!method || !['totp', 'sms'].includes(method)) {
    return res.status(400).json({ error: 'Invalid MFA method' });
  }

  // Generate cryptographically secure secret for TOTP
  const secret = generateSecureRandom(20);

  res.json({
    method,
    secret,
    qrCode: `otpauth://totp/Janua:user@example.com?secret=${secret}&issuer=Janua`,
    backupCodes: [
      generateBackupCode(),
      generateBackupCode(),
      generateBackupCode()
    ]
  });
});

// Verify MFA code
mfaRouter.post('/verify', (req: Request, res: Response) => {
  const { code } = req.body;

  if (!code) {
    return res.status(400).json({ error: 'Code is required' });
  }

  // Mock verification - accept any 6-digit code
  if (code.length === 6 && /^\d+$/.test(code)) {
    res.json({ valid: true });
  } else {
    res.status(400).json({ error: 'Invalid code' });
  }
});

// Disable MFA
mfaRouter.post('/disable', (_req: Request, res: Response) => {
  res.json({
    message: 'MFA disabled successfully'
  });
});

// Generate backup codes
mfaRouter.post('/backup-codes', (_req: Request, res: Response) => {
  const codes = Array.from({ length: 8 }, () => generateBackupCode());

  res.json({ codes });
});
