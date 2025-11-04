import { ReactNode } from 'react';

type GlassCardProps = {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  glow?: boolean;
};

export const GlassCard = ({ children, className = '', hover = false, glow = false }: GlassCardProps) => {
  return (
    <div
      className={`
        glass-card
        ${hover ? 'glass-hover' : ''}
        ${glow ? 'glass-glow' : ''}
        ${className}
      `}
    >
      {children}
    </div>
  );
};
