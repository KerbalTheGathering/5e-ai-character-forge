import type { ReactNode } from "react";

export default function GlassCard({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={`card rounded-2xl p-5 backdrop-blur-md bg-white/5 border border-white/10 shadow-lg ${className ?? ""}`}>
      {children}
    </div>
  );
}
