import React from 'react';
import { translateText } from '@/utils/translations';

/** Renders a string with **bold** markdown as <strong> elements and translates country names */
export default function RichText({ text }: { text: string }) {
  if (!text) return null;
  const translatedText = translateText(text);
  const parts = translatedText.split(/\*\*(.+?)\*\*/g);
  return (
    <>
      {parts.map((part, i) =>
        i % 2 === 1 ? (
          <strong key={i} className="font-bold text-[#1A1C1E]">
            {part}
          </strong>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  );
}
