import { forwardRef } from "react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface FormFieldProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: React.ReactNode;
  icon?: LucideIcon;
  error?: string;
  hint?: string;
  trailing?: React.ReactNode;
}

const FormField = forwardRef<HTMLInputElement, FormFieldProps>(function FormField(
  { label, icon: Icon, error, hint, trailing, id, name, className, ...props },
  ref
) {
  const inputId = id ?? name;
  return (
    <div className={className}>
      <label htmlFor={inputId} className="block text-xs font-bold text-dark uppercase tracking-wide mb-2">
        {label}
      </label>
      <div className="relative">
        {Icon && <Icon size={15} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />}
        <input
          ref={ref}
          id={inputId}
          name={name}
          aria-invalid={!!error}
          aria-describedby={error ? `${inputId}-error` : undefined}
          className={cn(
            "w-full py-3 bg-surface border rounded-xl text-base sm:text-sm text-dark placeholder:text-gray-400 focus:outline-hidden focus:ring-2 transition-all disabled:bg-gray-50 disabled:text-gray-500",
            Icon ? "pl-11" : "pl-4",
            trailing ? "pr-12" : "pr-4",
            error
              ? "border-red-300 focus:ring-red-100 focus:border-red-400"
              : "border-gray-200 focus:ring-primary/20 focus:border-primary"
          )}
          {...props}
        />
        {trailing && <div className="absolute right-3 top-1/2 -translate-y-1/2">{trailing}</div>}
      </div>
      {error ? (
        <p id={`${inputId}-error`} className="text-xs text-red-600 mt-1.5 ml-1">{error}</p>
      ) : hint ? (
        <p className="text-xs text-gray-400 mt-1.5 ml-1">{hint}</p>
      ) : null}
    </div>
  );
});

export default FormField;
