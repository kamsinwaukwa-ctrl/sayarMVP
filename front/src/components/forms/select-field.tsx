import * as React from "react"
import { useController, UseControllerProps, FieldValues, FieldPath } from "react-hook-form"
import { cn } from "../../lib/utils"
import { FormItem, FormLabel, FormControl, FormDescription, FormMessage } from "../ui/form"
import { Select } from "../ui/Select"

interface SelectOption {
  value: string
  label: string
  disabled?: boolean
}

interface SelectFieldProps<
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>
> extends UseControllerProps<TFieldValues, TName> {
  label?: string
  description?: string
  placeholder?: string
  options: SelectOption[]
  className?: string
  required?: boolean
  disabled?: boolean
}

/**
 * SelectField component - controlled select wrapper for react-hook-form
 * Provides consistent form field styling and validation integration
 */
export function SelectField<
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
  options,
  className,
  required,
  disabled,
}: SelectFieldProps<TFieldValues, TName>) {
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
        <Select
          {...field}
          disabled={disabled}
          className={cn(invalid && "border-destructive focus-visible:ring-destructive")}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((option) => (
            <option
              key={option.value}
              value={option.value}
              disabled={option.disabled}
            >
              {option.label}
            </option>
          ))}
        </Select>
      </FormControl>
      {description && <FormDescription>{description}</FormDescription>}
      <FormMessage>{error?.message}</FormMessage>
    </FormItem>
  )
}