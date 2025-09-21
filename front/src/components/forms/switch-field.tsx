//import * as React from "react"
import { useController, UseControllerProps, FieldValues, FieldPath } from "react-hook-form"
import { cn } from "@/lib/utils"
import { FormItem, FormLabel, FormControl, FormDescription, FormMessage } from "@/components/ui/form"
import { Switch } from "@/components/ui/switch"

interface SwitchFieldProps<
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>
> extends UseControllerProps<TFieldValues, TName> {
  label?: string
  description?: string
  className?: string
  disabled?: boolean
}

/**
 * SwitchField component - controlled switch wrapper for react-hook-form
 * Provides consistent form field styling and validation integration
 */
export function SwitchField<
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>
>({
  name,
  control,
  defaultValue,
  rules,
  shouldUnregister,
  label,
  description,
  className,
  disabled,
}: SwitchFieldProps<TFieldValues, TName>) {
  const {
    field: { value, onChange, ...field },
    fieldState: { error },
  } = useController({
    name,
    control,
    defaultValue,
    rules,
    shouldUnregister,
  })

  return (
    <FormItem className={cn("flex flex-row items-center justify-between rounded-lg border p-4", className)}>
      <div className="space-y-0.5">
        {label && <FormLabel className="text-base">{label}</FormLabel>}
        {description && <FormDescription>{description}</FormDescription>}
      </div>
      <FormControl>
        <Switch
          {...field}
          checked={value}
          onCheckedChange={onChange}
          disabled={disabled}
        />
      </FormControl>
      <FormMessage>{error?.message}</FormMessage>
    </FormItem>
  )
}