'use client';

interface BentoCardProps {
  children: React.ReactNode;
  className?: string;
  padding?: boolean;
}

export default function BentoCard({ children, className = '', padding = true }: BentoCardProps) {
  return (
    <div className={`bento-card ${padding ? 'p-8' : ''} ${className}`}>
      {children}
    </div>
  );
}
