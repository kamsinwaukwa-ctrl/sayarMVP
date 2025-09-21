//import * as React from "react"
import { useController, UseControllerProps, FieldValues, FieldPath } from "react-hook-form"
import { cn } from "../../lib/utils"
import { FormItem, FormLabel, FormControl, FormDescription, FormMessage } from "../ui/form"
import { Input } from "../ui/Input"

interface TextFieldProps<
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>
> extends UseControllerProps<TFieldValues, TName> {
  label?: string
  description?: string
  placeholder?: string
  type?: string
  className?: string
  required?: boolean
  disabled?: boolean
}

/**
 * TextField component - controlled input wrapper for react-hook-form
 * Provides consistent form field styling and validation integration
 */
export function TextField<
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
  placeholder,
  type = "text",
  className,
  required,
  disabled,
}: TextFieldProps<TFieldValues, TName>) {
  const {
    field,
    fieldState: { invalid, error },
  } = useController({
    name,
    control,
    defaultValue,
    rules: {
      ...rules,
      required: required ? `${label || name} is required` : rules?.required,
    },
    shouldUnregister,
  })

  return (
    <FormItem className={className}>
      {label && (
        <FormLabel className={cn(required && "after:content-['*'] after:text-destructive after:ml-0.5")}>
          {label}
        </FormLabel>
      )}
      <FormControl>
        <Input
          {...field}
          type={type}
          placeholder={placeholder}
          disabled={disabled}
          className={cn(invalid && "border-destructive focus-visible:ring-destructive")}
        />
      </FormControl>
      {description && <FormDescription>{description}</FormDescription>}
      <FormMessage>{error?.message}</FormMessage>
    </FormItem>
  )
}