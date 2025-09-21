//import * as React from "react"
import { useController, UseControllerProps, FieldValues, FieldPath } from "react-hook-form"
import { cn } from "../../lib/utils"
import { FormItem, FormLabel, FormControl, FormDescription, FormMessage } from "../ui/form"
import { Checkbox } from "../ui/checkbox"

interface CheckboxFieldProps<
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>
> extends UseControllerProps<TFieldValues, TName> {
  label?: string
  description?: string
  className?: string
  disabled?: boolean
}

/**
 * CheckboxField component - controlled checkbox wrapper for react-hook-form
 * Provides consistent form field styling and validation integration
 */
export function CheckboxField<
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
}: CheckboxFieldProps<TFieldValues, TName>) {
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
    <FormItem className={cn("flex flex-row items-start space-x-3 space-y-0", className)}>
      <FormControl>
        <Checkbox
          {...field}
          checked={value}
          onCheckedChange={onChange}
          disabled={disabled}
        />
      </FormControl>
      <div className="space-y-1 leading-none">
        {label && <FormLabel>{label}</FormLabel>}
        {description && <FormDescription>{description}</FormDescription>}
        <FormMessage>{error?.message}</FormMessage>
      </div>
    </FormItem>
  )
}