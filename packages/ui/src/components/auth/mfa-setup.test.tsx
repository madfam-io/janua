import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, act } from '@/test/test-utils'
import userEvent from '@testing-library/user-event'
import { MFASetup } from './mfa-setup'

describe('MFASetup', () => {
  const mockMFAData = {
    secret: 'JBSWY3DPEHPK3PXP',
    qrCode: 'data:image/png;base64,iVBORw0KGgo...',
    backupCodes: ['CODE1234', 'CODE5678', 'CODE9012'],
  }

  const mockOnFetchSetupData = vi.fn()
  const mockOnComplete = vi.fn()
  const mockOnError = vi.fn()
  const mockOnCancel = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    global.alert = vi.fn()

    // Mock window.location
    Object.defineProperty(window, 'location', {
      value: { href: '' },
      writable: true,
      configurable: true,
    })

    // Mock URL.createObjectURL
    global.URL.createObjectURL = vi.fn(() => 'blob:mock-url')
    global.URL.revokeObjectURL = vi.fn()

    // Mock clipboard API
    Object.defineProperty(navigator, 'clipboard', {
      value: {
        writeText: vi.fn(() => Promise.resolve()),
        readText: vi.fn(() => Promise.resolve('')),
      },
      configurable: true,
      writable: true,
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  describe('Rendering', () => {
    it('should render setup wizard with provided MFA data', () => {
      render(<MFASetup mfaData={mockMFAData} />)

      expect(screen.getByText(/set up two-factor authentication/i)).toBeInTheDocument()
      expect(screen.getByText(/step 1 of 3/i)).toBeInTheDocument()
    })

    it('should show loading state when fetching MFA data', async () => {
      mockOnFetchSetupData.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve(mockMFAData), 100))
      )

      render(<MFASetup onFetchSetupData={mockOnFetchSetupData} />)

      // Loading state shows a spinner with animate-spin class
      const spinner = document.querySelector('.animate-spin')
      expect(spinner).toBeInTheDocument()
    })

    it('should fetch MFA data on mount when not provided', async () => {
      mockOnFetchSetupData.mockResolvedValue(mockMFAData)

      render(<MFASetup onFetchSetupData={mockOnFetchSetupData} />)

      await waitFor(() => {
        expect(mockOnFetchSetupData).toHaveBeenCalled()
      })
    })

    it('should show error when fetch fails', async () => {
      mockOnFetchSetupData.mockRejectedValue(new Error('Failed to fetch'))

      render(<MFASetup onFetchSetupData={mockOnFetchSetupData} onError={mockOnError} />)

      await waitFor(() => {
        expect(screen.getByText(/failed to load mfa setup data/i)).toBeInTheDocument()
        expect(mockOnError).toHaveBeenCalled()
      })
    })
  })

  describe('Step 1: Scan QR Code', () => {
    it('should display QR code', () => {
      render(<MFASetup mfaData={mockMFAData} />)

      const qrImage = screen.getByAltText(/qr code/i)
      expect(qrImage).toBeInTheDocument()
      expect(qrImage).toHaveAttribute('src', mockMFAData.qrCode)
    })

    it('should display manual entry secret', () => {
      render(<MFASetup mfaData={mockMFAData} />)

      expect(screen.getByText(mockMFAData.secret)).toBeInTheDocument()
      expect(screen.getByText(/or enter this code manually/i)).toBeInTheDocument()
    })

    it('should copy secret to clipboard', async () => {
      const user = userEvent.setup()
      render(<MFASetup mfaData={mockMFAData} />)

      const copyButton = screen.getByRole('button', { name: /copy/i })
      expect(copyButton).toBeInTheDocument()

      await user.click(copyButton)

      expect(await screen.findByText(/copied/i)).toBeInTheDocument()
    })

    it('should show copied state temporarily', async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true })
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })

      render(<MFASetup mfaData={mockMFAData} />)

      const copyButton = screen.getByRole('button', { name: /copy/i })
      await user.click(copyButton)

      expect(screen.getByText(/copied/i)).toBeInTheDocument()

      await act(async () => {
        vi.advanceTimersByTime(2500)
      })

      await waitFor(() => {
        expect(screen.queryByText(/copied/i)).not.toBeInTheDocument()
      })
    })

    it('should navigate to verify step', async () => {
      const user = userEvent.setup()
      render(<MFASetup mfaData={mockMFAData} />)

      const continueButton = screen.getByRole('button', { name: /continue/i })
      await user.click(continueButton)

      await waitFor(() => {
        expect(screen.getByText(/step 2 of 3/i)).toBeInTheDocument()
        expect(screen.getByText(/verify your code/i)).toBeInTheDocument()
      })
    })

    it('should call onCancel when cancel button is clicked', async () => {
      const user = userEvent.setup()
      render(<MFASetup mfaData={mockMFAData} onCancel={mockOnCancel} />)

      const cancelButton = screen.getByRole('button', { name: /cancel/i })
      await user.click(cancelButton)

      expect(mockOnCancel).toHaveBeenCalled()
    })

    it('should not show cancel button when callback not provided', () => {
      render(<MFASetup mfaData={mockMFAData} />)

      expect(screen.queryByRole('button', { name: /cancel/i })).not.toBeInTheDocument()
    })
  })

  describe('Step 2: Verify Code', () => {
    const navigateToVerifyStep = async (user: ReturnType<typeof userEvent.setup>) => {
      const continueButton = screen.getByRole('button', { name: /continue/i })
      await user.click(continueButton)
      await waitFor(() => {
        expect(screen.getByText(/step 2 of 3/i)).toBeInTheDocument()
      })
    }

    it('should display verification code input', async () => {
      const user = userEvent.setup()
      render(<MFASetup mfaData={mockMFAData} />)

      await navigateToVerifyStep(user)

      expect(screen.getByLabelText(/verification code/i)).toBeInTheDocument()
    })

    it('should only accept numeric input', async () => {
      const user = userEvent.setup()
      render(<MFASetup mfaData={mockMFAData} />)

      await navigateToVerifyStep(user)

      const codeInput = screen.getByLabelText(/verification code/i)
      await user.type(codeInput, 'abc123def')

      expect(codeInput).toHaveValue('123')
    })

    it('should limit input to 6 digits', async () => {
      const user = userEvent.setup()
      render(<MFASetup mfaData={mockMFAData} />)

      await navigateToVerifyStep(user)

      const codeInput = screen.getByLabelText(/verification code/i)
      await user.type(codeInput, '1234567890')

      expect(codeInput).toHaveValue('123456')
    })

    it('should verify code and proceed to backup codes', async () => {
      const user = userEvent.setup()
      mockOnComplete.mockResolvedValue(undefined)

      render(<MFASetup mfaData={mockMFAData} onComplete={mockOnComplete} showBackupCodes={true} />)

      await navigateToVerifyStep(user)

      const codeInput = screen.getByLabelText(/verification code/i)
      await user.type(codeInput, '123456')

      const verifyButton = screen.getByRole('button', { name: /verify/i })
      await user.click(verifyButton)

      await waitFor(() => {
        expect(mockOnComplete).toHaveBeenCalledWith('123456')
        expect(screen.getByText(/step 3 of 3/i)).toBeInTheDocument()
      })
    })

    it('should skip backup codes step when disabled', async () => {
      const user = userEvent.setup()
      mockOnComplete.mockResolvedValue(undefined)

      render(<MFASetup mfaData={mockMFAData} onComplete={mockOnComplete} showBackupCodes={false} />)

      await navigateToVerifyStep(user)

      const codeInput = screen.getByLabelText(/verification code/i)
      await user.type(codeInput, '123456')

      const verifyButton = screen.getByRole('button', { name: /verify/i })
      await user.click(verifyButton)

      await waitFor(() => {
        expect(mockOnComplete).toHaveBeenCalledWith('123456')
      })

      // Should not show step 3 when backup codes disabled
      expect(screen.queryByText(/step 3 of 3/i)).not.toBeInTheDocument()
    })

    it('should show error on invalid verification code', async () => {
      const user = userEvent.setup()
      mockOnComplete.mockRejectedValue(new Error('Invalid code'))

      render(<MFASetup mfaData={mockMFAData} onComplete={mockOnComplete} onError={mockOnError} />)

      await navigateToVerifyStep(user)

      const codeInput = screen.getByLabelText(/verification code/i)
      await user.type(codeInput, '000000')

      const verifyButton = screen.getByRole('button', { name: /verify/i })
      await user.click(verifyButton)

      await waitFor(() => {
        expect(mockOnError).toHaveBeenCalled()
      })
    })

    it('should disable verify button when code is incomplete', async () => {
      const user = userEvent.setup()
      render(<MFASetup mfaData={mockMFAData} />)

      await navigateToVerifyStep(user)

      const verifyButton = screen.getByRole('button', { name: /verify/i })
      expect(verifyButton).toBeDisabled()

      const codeInput = screen.getByLabelText(/verification code/i)
      await user.type(codeInput, '12345')
      expect(verifyButton).toBeDisabled()

      await user.type(codeInput, '6')
      expect(verifyButton).not.toBeDisabled()
    })

    it('should show loading state during verification', async () => {
      const user = userEvent.setup()
      let resolveVerification: () => void
      mockOnComplete.mockImplementation(
        () => new Promise<void>((resolve) => { resolveVerification = resolve })
      )

      render(<MFASetup mfaData={mockMFAData} onComplete={mockOnComplete} />)

      await navigateToVerifyStep(user)

      const codeInput = screen.getByLabelText(/verification code/i)
      await user.type(codeInput, '123456')

      const verifyButton = screen.getByRole('button', { name: /verify/i })
      await user.click(verifyButton)

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /verifying/i })).toBeDisabled()
      })

      // Cleanup - resolve the promise
      await act(async () => {
        resolveVerification!()
      })
    })

    it('should allow going back to scan step', async () => {
      const user = userEvent.setup()
      render(<MFASetup mfaData={mockMFAData} />)

      await navigateToVerifyStep(user)

      const backButton = screen.getByRole('button', { name: /back/i })
      await user.click(backButton)

      await waitFor(() => {
        expect(screen.getByText(/step 1 of 3/i)).toBeInTheDocument()
        expect(screen.getByText(/scan this qr code/i)).toBeInTheDocument()
      })
    })
  })

  describe('Step 3: Backup Codes', () => {
    const navigateToBackupCodesStep = async (user: ReturnType<typeof userEvent.setup>) => {
      mockOnComplete.mockResolvedValue(undefined)

      // Step 1 -> Step 2
      const continueButton = screen.getByRole('button', { name: /continue/i })
      await user.click(continueButton)

      await waitFor(() => {
        expect(screen.getByText(/step 2 of 3/i)).toBeInTheDocument()
      })

      // Step 2 -> Step 3
      const codeInput = screen.getByLabelText(/verification code/i)
      await user.type(codeInput, '123456')

      const verifyButton = screen.getByRole('button', { name: /verify/i })
      await user.click(verifyButton)

      await waitFor(() => {
        expect(screen.getByText(/step 3 of 3/i)).toBeInTheDocument()
      })
    }

    it('should display backup codes', async () => {
      const user = userEvent.setup()
      render(<MFASetup mfaData={mockMFAData} onComplete={mockOnComplete} showBackupCodes={true} />)

      await navigateToBackupCodesStep(user)

      mockMFAData.backupCodes.forEach((code) => {
        expect(screen.getByText(code)).toBeInTheDocument()
      })
    })

    it('should download backup codes', async () => {
      const user = userEvent.setup()
      render(<MFASetup mfaData={mockMFAData} onComplete={mockOnComplete} showBackupCodes={true} />)

      await navigateToBackupCodesStep(user)

      // Mock document methods
      const mockClick = vi.fn()
      const mockAppendChild = vi.spyOn(document.body, 'appendChild').mockImplementation(() => null as unknown as HTMLAnchorElement)
      const mockRemoveChild = vi.spyOn(document.body, 'removeChild').mockImplementation(() => null as unknown as HTMLAnchorElement)
      const mockCreateElement = vi.spyOn(document, 'createElement').mockReturnValue({
        click: mockClick,
        href: '',
        download: '',
      } as unknown as HTMLAnchorElement)

      const downloadButton = screen.getByRole('button', { name: /download codes/i })
      await user.click(downloadButton)

      expect(mockCreateElement).toHaveBeenCalledWith('a')
      expect(mockClick).toHaveBeenCalled()

      mockCreateElement.mockRestore()
      mockAppendChild.mockRestore()
      mockRemoveChild.mockRestore()
    })

    it('should show warning about backup codes', async () => {
      const user = userEvent.setup()
      render(<MFASetup mfaData={mockMFAData} onComplete={mockOnComplete} showBackupCodes={true} />)

      await navigateToBackupCodesStep(user)

      expect(screen.getByText(/important/i)).toBeInTheDocument()
      expect(screen.getByText(/each backup code can only be used once/i)).toBeInTheDocument()
    })

    it('should require download before completing', async () => {
      const user = userEvent.setup()
      render(<MFASetup mfaData={mockMFAData} onComplete={mockOnComplete} showBackupCodes={true} />)

      await navigateToBackupCodesStep(user)

      const completeButton = screen.getByRole('button', { name: /complete setup/i })
      await user.click(completeButton)

      expect(global.alert).toHaveBeenCalledWith(
        'Please download your backup codes before continuing'
      )
    })

    it('should complete setup after download', async () => {
      const user = userEvent.setup()
      render(<MFASetup mfaData={mockMFAData} onComplete={mockOnComplete} showBackupCodes={true} />)

      await navigateToBackupCodesStep(user)

      // Mock document methods for download
      const mockClick = vi.fn()
      const mockAppendChild = vi.spyOn(document.body, 'appendChild').mockImplementation(() => null as unknown as HTMLAnchorElement)
      const mockRemoveChild = vi.spyOn(document.body, 'removeChild').mockImplementation(() => null as unknown as HTMLAnchorElement)
      const mockCreateElement = vi.spyOn(document, 'createElement').mockReturnValue({
        click: mockClick,
        href: '',
        download: '',
      } as unknown as HTMLAnchorElement)

      const downloadButton = screen.getByRole('button', { name: /download codes/i })
      const completeButton = screen.getByRole('button', { name: /complete setup/i })

      await user.click(downloadButton)
      await user.click(completeButton)

      expect(window.location.href).toBe('/dashboard')

      mockCreateElement.mockRestore()
      mockAppendChild.mockRestore()
      mockRemoveChild.mockRestore()
    })
  })

  describe('Accessibility', () => {
    const navigateToVerifyStep = async (user: ReturnType<typeof userEvent.setup>) => {
      const continueButton = screen.getByRole('button', { name: /continue/i })
      await user.click(continueButton)
      await waitFor(() => {
        expect(screen.getByText(/step 2 of 3/i)).toBeInTheDocument()
      })
    }

    it('should have proper form labels', async () => {
      const user = userEvent.setup()
      render(<MFASetup mfaData={mockMFAData} />)

      await navigateToVerifyStep(user)

      expect(screen.getByLabelText(/verification code/i)).toBeInTheDocument()
    })

    it('should have autocomplete attribute for OTP', async () => {
      const user = userEvent.setup()
      render(<MFASetup mfaData={mockMFAData} />)

      await navigateToVerifyStep(user)

      const codeInput = screen.getByLabelText(/verification code/i)
      expect(codeInput).toHaveAttribute('autocomplete', 'one-time-code')
    })

    it('should have proper input mode for numeric entry', async () => {
      const user = userEvent.setup()
      render(<MFASetup mfaData={mockMFAData} />)

      await navigateToVerifyStep(user)

      const codeInput = screen.getByLabelText(/verification code/i)
      expect(codeInput).toHaveAttribute('inputmode', 'numeric')
    })

    it('should support keyboard navigation', async () => {
      const user = userEvent.setup()
      render(<MFASetup mfaData={mockMFAData} onCancel={mockOnCancel} />)

      await user.tab()
      expect(screen.getByRole('button', { name: /copy/i })).toHaveFocus()

      await user.tab()
      expect(screen.getByRole('button', { name: /cancel/i })).toHaveFocus()

      await user.tab()
      expect(screen.getByRole('button', { name: /continue/i })).toHaveFocus()
    })
  })

  describe('Error Handling', () => {
    it('should handle clipboard write errors gracefully', async () => {
      const user = userEvent.setup()
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

      // Override clipboard to simulate error
      Object.defineProperty(navigator, 'clipboard', {
        value: {
          writeText: vi.fn(() => Promise.reject(new Error('Clipboard error'))),
        },
        configurable: true,
      })

      render(<MFASetup mfaData={mockMFAData} />)

      const copyButton = screen.getByRole('button', { name: /copy/i })
      await user.click(copyButton)

      await waitFor(() => {
        expect(consoleError).toHaveBeenCalled()
      })

      consoleError.mockRestore()
    })

    it('should display error from onError callback', async () => {
      const user = userEvent.setup()
      const error = new Error('Custom error')
      mockOnComplete.mockRejectedValue(error)

      render(<MFASetup mfaData={mockMFAData} onComplete={mockOnComplete} onError={mockOnError} />)

      const continueButton = screen.getByRole('button', { name: /continue/i })
      await user.click(continueButton)

      await waitFor(() => {
        expect(screen.getByText(/step 2 of 3/i)).toBeInTheDocument()
      })

      const codeInput = screen.getByLabelText(/verification code/i)
      await user.type(codeInput, '000000')

      const verifyButton = screen.getByRole('button', { name: /verify/i })
      await user.click(verifyButton)

      await waitFor(() => {
        expect(mockOnError).toHaveBeenCalled()
      })
    })
  })
})
