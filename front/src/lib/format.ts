/**
 * Formatting utilities for currency, dates, and other display values
 */

/**
 * Converts Naira input (string or number) to kobo (integer)
 * Uses precision-first approach to avoid floating-point errors
 * @param input - Naira amount as string or number (e.g., "90", "90.50", 90)
 * @returns Integer kobo value (e.g., 9000, 9050)
 * @throws Error if input is invalid or too large
 */
export const nairaToKobo = (input: string | number): number => {
  const s = String(input).replace(/,/g, "").trim();
  if (!/^\d+(\.\d{1,2})?$/.test(s)) {
    throw new Error("Enter a valid amount (max 2 decimals)");
  }
  const [intPart, decPart = ""] = s.split(".");
  const cents = (decPart + "00").slice(0, 2);
  const kobo = Number(intPart) * 100 + Number(cents);
  if (!Number.isSafeInteger(kobo)) throw new Error("Amount too large");
  return kobo;
};

/**
 * Converts kobo (integer) to formatted Naira display string
 * @param kobo - Kobo amount as integer (e.g., 9000, 9050)
 * @returns Formatted currency string (e.g., "₦90.00", "₦90.50")
 */
export const koboToNairaDisplay = (kobo?: number | null): string => {
  if (kobo === null || kobo === undefined) return "";
  return (Number(kobo) / 100).toLocaleString("en-NG", {
    style: "currency",
    currency: "NGN",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
};

/**
 * Converts kobo (integer) to plain Naira number for form inputs
 * @param kobo - Kobo amount as integer (e.g., 9000, 9050)
 * @returns Plain number in Naira (e.g., 90, 90.5)
 */
export const koboToNairaNumber = (kobo?: number | null): number => {
  if (kobo === null || kobo === undefined) return 0;
  return Number(kobo) / 100;
};

// Legacy functions - kept for backward compatibility
export const formatNaira = (kobo: number): string => {
  return koboToNairaDisplay(kobo);
}

export const formatDate = (isoString: string): string => {
  return new Intl.DateTimeFormat('en-NG', {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(new Date(isoString))
}

export const formatCurrency = (amount: number, currency: string = 'NGN'): string => {
  return new Intl.NumberFormat('en-NG', {
    style: 'currency',
    currency: currency
  }).format(amount)
}

export const formatNumber = (number: number): string => {
  return new Intl.NumberFormat('en-NG').format(number)
}