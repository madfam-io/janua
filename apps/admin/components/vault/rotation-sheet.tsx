'use client'

import * as React from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Key, RefreshCw, AlertTriangle, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Separator } from '@/components/ui/separator'
import { Label } from '@/components/ui/label'
import type { MaskedSecret } from './types'
import { rotationSchema, type RotationFormValues } from './rotation-schema'

interface RotationSheetProps {
  secret: MaskedSecret
  onRotate: (secretId: string, newValue: string, reason?: string) => Promise<void>
}

export function RotationSheet({ secret, onRotate }: RotationSheetProps) {
  const [open, setOpen] = React.useState(false)
  const [loading, setLoading] = React.useState(false)
  const [confirmDialog, setConfirmDialog] = React.useState(false)

  const form = useForm<RotationFormValues>({
    resolver: zodResolver(rotationSchema),
    defaultValues: {
      newValue: '',
      confirmValue: '',
      reason: '',
    },
  })

  const onSubmit = async (_data: RotationFormValues) => {
    setConfirmDialog(true)
  }

  const executeRotation = async () => {
    const values = form.getValues()
    setLoading(true)
    try {
      await onRotate(secret.id, values.newValue, values.reason)
      form.reset()
      setConfirmDialog(false)
      setOpen(false)
    } catch (error) {
      console.error('Rotation failed:', error)
    } finally {
      setLoading(false)
    }
  }

  const isOverdue = new Date(secret.nextRotation) < new Date()

  return (
    <>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetTrigger asChild>
          <Button variant="ghost" size="sm" className="h-8">
            <RefreshCw className="h-4 w-4 mr-2" />
            Rotate
          </Button>
        </SheetTrigger>
        <SheetContent className="w-[500px] sm:max-w-[500px]">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              <Key className="h-5 w-5 text-primary" />
              Rotate Secret: {secret.name}
            </SheetTitle>
            <SheetDescription>
              Rotate this secret to a new value. This will update all dependent services.
            </SheetDescription>
          </SheetHeader>

          <div className="py-6 space-y-6">
            {/* Secret info */}
            <div className="space-y-2">
              <Label className="text-muted-foreground">Current Secret</Label>
              <div className="p-3 bg-muted rounded-lg font-mono text-sm">{secret.maskedValue}</div>
            </div>

            {/* Overdue warning */}
            {isOverdue && (
              <div className="p-3 bg-destructive/10 border border-destructive/30 rounded-lg flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-destructive">Rotation Overdue</p>
                  <p className="text-sm text-muted-foreground">
                    This secret was due for rotation on {new Date(secret.nextRotation).toLocaleDateString()}
                  </p>
                </div>
              </div>
            )}

            {/* Dependent services */}
            <div className="space-y-2">
              <Label className="text-muted-foreground">Dependent Services</Label>
              <div className="flex flex-wrap gap-2">
                {secret.dependentServices.map((service) => (
                  <Badge key={service} variant="secondary" className="font-mono">
                    {service}
                  </Badge>
                ))}
              </div>
            </div>

            <Separator />

            {/* Rotation form */}
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                <FormField
                  control={form.control}
                  name="newValue"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>New Secret Value</FormLabel>
                      <FormControl>
                        <Input
                          type="password"
                          placeholder="Enter new secret value"
                          className="font-mono"
                          {...field}
                        />
                      </FormControl>
                      <FormDescription>Paste or enter the new secret value</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="confirmValue"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Confirm Secret Value</FormLabel>
                      <FormControl>
                        <Input
                          type="password"
                          placeholder="Confirm new secret value"
                          className="font-mono"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="reason"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Rotation Reason (Optional)</FormLabel>
                      <FormControl>
                        <Input placeholder="e.g., Scheduled rotation, Security incident" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Danger zone */}
                <div className="danger-zone mt-6">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle className="h-4 w-4 text-destructive" />
                    <span className="font-semibold text-destructive">Danger Zone</span>
                  </div>
                  <p className="text-sm text-muted-foreground mb-4">
                    Rotating this secret will immediately invalidate the old value. Ensure all dependent services
                    can handle the change.
                  </p>
                  <Button type="submit" variant="destructive" className="w-full">
                    <RefreshCw className="mr-2 h-4 w-4" />
                    Initiate Rotation
                  </Button>
                </div>
              </form>
            </Form>
          </div>
        </SheetContent>
      </Sheet>

      {/* Confirmation dialog */}
      <AlertDialog open={confirmDialog} onOpenChange={setConfirmDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirm Secret Rotation</AlertDialogTitle>
            <AlertDialogDescription>
              You are about to rotate the secret <strong>{secret.name}</strong>. This will:
              <ul className="list-disc list-inside mt-2 space-y-1">
                <li>Invalidate the current secret immediately</li>
                <li>Update {secret.dependentServices.length} dependent service(s)</li>
                <li>Trigger webhook notifications</li>
              </ul>
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={loading}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={executeRotation}
              disabled={loading}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Rotating...
                </>
              ) : (
                'Confirm Rotation'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
