import { z } from 'zod'

export const whatsappVerificationSchema = z.object({
  waba_id: z.string().min(10, "WhatsApp Business Account ID required"),
  phone_number_id: z.string().min(10, "Phone Number ID required"),
  app_id: z.string().min(10, "App ID required"),
  system_user_token: z.string().min(20, "System User Token required")
})