import * as z from 'zod'

export const rotationSchema = z
  .object({
    newValue: z.string().min(1, 'New secret value is required'),
    confirmValue: z.string().min(1, 'Please confirm the secret value'),
    reason: z.string().optional(),
  })
  .refine((data) => data.newValue === data.confirmValue, {
    message: "Values don't match",
    path: ['confirmValue'],
  })

export type RotationFormValues = z.infer<typeof rotationSchema>
