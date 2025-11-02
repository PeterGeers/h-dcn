
import React from 'react';
import { Icon } from './Icon';

export const Header: React.FC = () => {
  return (
    <header className="bg-slate-900/50 backdrop-blur-sm border-b border-slate-700 sticky top-0 z-10">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-3">
            <Icon name="sparkles" className="h-8 w-8 text-indigo-400" />
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">
              AI Image Enhancer
            </h1>
          </div>
        </div>
      </div>
    </header>
  );
};
