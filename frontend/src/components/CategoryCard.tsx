'use client';

import Image from 'next/image';

interface CategoryCardProps {
  title: string;
  subtitle: string;
  image?: string;
  active?: boolean;
}

export default function CategoryCard({ title, subtitle, image, active }: CategoryCardProps) {
  return (
    <div className={`category-transition flex flex-col gap-4 cursor-pointer group ${!active ? 'opacity-70 grayscale' : ''}`}>
      <div className={`relative aspect-square rounded-[2rem] overflow-hidden border-2 transition-all ${active ? 'border-[#064E3B]' : 'border-transparent group-hover:border-[#E5E7EB]'}`}>
        <Image 
          src={image || 'https://images.unsplash.com/photo-1508098682722-e99c43a406b2?q=80&w=400&h=400&auto=format&fit=crop'} 
          alt={title}
          fill
          className="object-cover grayscale-[0.2] transition-all duration-500 group-hover:scale-110 group-hover:grayscale-0"
        />
        {active ? (
          <div className="absolute inset-0 bg-[#064E3B]/10 flex items-center justify-center">
            <div className="bg-white p-2 rounded-full shadow-lg">
              <svg className="w-4 h-4 text-[#064E3B]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
              </svg>
            </div>
          </div>
        ) : (
          <div className="absolute inset-0 bg-white/40 backdrop-blur-[2px] opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center p-6 text-center">
            <span className="text-[10px] font-bold text-[#1A1C1E] uppercase tracking-widest leading-tight">
              Disponible en siguientes actualizaciones
            </span>
          </div>
        )}
      </div>
      <div>
        <h3 className="font-editorial text-xl font-bold text-[#1A1C1E] group-hover:text-[#064E3B] transition-colors">{title}</h3>
        <p className="text-xs font-bold text-[#64748B] uppercase tracking-widest">{subtitle}</p>
      </div>
    </div>
  );
}
