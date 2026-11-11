'use client';
import React from 'react';
import { FileText, Table } from 'lucide-react';
import { useConverterStore } from '@/store/useConverterStore';
import { TargetFormat } from '@/lib/types';

export const FormatSelector: React.FC = () => {
  const { targetFormat, setTargetFormat } = useConverterStore();

  const formats: { value: TargetFormat; label: string; icon: React.ReactNode }[] = [
    { value: 'docx', label: 'Word (.docx)', icon: <FileText className="w-4 h-4" /> },
    { value: 'xlsx', label: 'Excel (.xlsx)', icon: <Table className="w-4 h-4" /> },
  ];

  return (
    <div className="flex gap-3">
      {formats.map(({ value, label, icon }) => (
        <button
          key={value}
          onClick={() => setTargetFormat(value)}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl border text-sm font-medium transition-all ${
            targetFormat === value
              ? 'border-blue-500 bg-blue-50 text-blue-700'
              : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'
          }`}
        >
          {icon}
          {label}
        </button>
      ))}
    </div>
  );
};
