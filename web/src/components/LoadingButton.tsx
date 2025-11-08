import { useState } from "react";
import type { PropsWithChildren } from "react";

type LoadingButtonProps = PropsWithChildren<{
  onClick: () => void | Promise<void>;
  className?: string;
  title?: string;
  disabled?: boolean;
  loading?: boolean; // external loading control (optional)
}>;

export default function LoadingButton({ onClick, className, title, disabled, loading, children }: LoadingButtonProps) {
  const [internalLoading, setInternalLoading] = useState(false);
  const busy = Boolean(loading ?? internalLoading);

  async function handleClick() {
    if (busy || disabled) return;
    try {
      const res = onClick?.();
      if (res && typeof (res as any).then === 'function') {
        setInternalLoading(true);
        await (res as Promise<void>);
      }
    } finally {
      setInternalLoading(false);
    }
  }

  return (
    <button
      className={`btn ${busy ? 'btn-disabled' : ''} ${className || ''}`}
      onClick={handleClick}
      disabled={disabled || busy}
      aria-busy={busy ? true : undefined}
      title={title}
    >
      <span className="btn-content">
        {busy && <span className="spinner" aria-hidden="true" />}
        {children}
      </span>
    </button>
  );
}

