
import React from 'react';

interface IconProps {
  name: string;
  className?: string;
}

// Icons are mostly from or inspired by Heroicons v1 (https://v1.heroicons.com/)
// FIX: Use React.ReactElement instead of JSX.Element to avoid "Cannot find namespace 'JSX'" error.
// FIX: The generic `React.ReactElement` type caused props type information to be lost.
// By specifying `React.SVGProps<SVGSVGElement>`, we allow TypeScript to validate the `className` prop for `React.cloneElement`.
const ICONS: Record<string, React.ReactElement<React.SVGProps<SVGSVGElement>>> = {
  upload: (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4-4m0 0l-4 4m4-4v12" />
    </svg>
  ),
  sparkles: (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
       <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M19 17v4m-2-2h4m-12-4a4 4 0 110-8 4 4 0 010 8z" />
    </svg>
  ),
  cut: (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.74 9l.36-1.08a1 1 0 00-.28-1.12l-1.74-1.74a1 1 0 00-1.12-.28L10 5.26 6.26 1.51a1 1 0 00-1.42 0L3.42 2.93a1 1 0 000 1.42L7.17 8H4a1 1 0 00-1 1v2a1 1 0 001 1h3.17l-4.75 4.75a1 1 0 000 1.42l1.42 1.42a1 1 0 001.42 0L14 12.41V15a1 1 0 001 1h2a1 1 0 001-1v-3.17l4.75-4.75a1 1 0 000-1.42l-1.42-1.42a1 1 0 00-1.42 0L15 7.59V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2.59z" />
    </svg>
  ),
  download: (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
    </svg>
  ),
  reset: (
     <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.5 12c0-4.142 3.358-7.5 7.5-7.5s7.5 3.358 7.5 7.5c0 4.142-3.358 7.5-7.5 7.5-1.83 0-3.543-.654-4.897-1.748L8.5 15.5m-.5-5.5v6h6" />
    </svg>
  ),
  crop: (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 21v-4a2 2 0 012-2h4" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 15v4a2 2 0 01-2 2h-4 M3 9V5a2 2 0 012-2h4" />
    </svg>
  )
};

export const Icon: React.FC<IconProps> = ({ name, className }) => {
  const IconSvg = ICONS[name];
  if (!IconSvg) {
    console.warn(`Icon "${name}" not found.`);
    // Return a placeholder to avoid breaking layout
    return <div className={`w-5 h-5 bg-slate-700 rounded-sm ${className}`} />;
  }

  // Clone the SVG element and apply the className prop
  return React.cloneElement(IconSvg, { className });
};
