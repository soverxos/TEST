import { ReactNode } from 'react';

type GlassCardProps = {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  glow?: boolean;
  gradient?: 'primary' | 'accent' | 'success' | 'danger' | 'none';
};

export const GlassCard = ({ 
  children, 
  className = '', 
  hover = false, 
  glow = false,
  gradient = 'none'
}: GlassCardProps) => {
  const gradientClasses = {
    primary: 'before:bg-gradient-to-br before:from-cyan-500/10 before:to-blue-500/10',
    accent: 'before:bg-gradient-to-br before:from-purple-500/10 before:to-pink-500/10',
    success: 'before:bg-gradient-to-br before:from-green-500/10 before:to-emerald-500/10',
    danger: 'before:bg-gradient-to-br before:from-red-500/10 before:to-orange-500/10',
    none: '',
  };

  return (
    <div
      className={`
        glass-card
        ${hover ? 'glass-hover' : ''}
        ${glow ? 'glass-glow' : ''}
        ${gradientClasses[gradient]}
        ${className}
      `}
    >
      {children}
    </div>
  );
};
