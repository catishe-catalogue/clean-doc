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
    <div className="inline-flex p-1.5 rounded-stock bg-paper-2 border border-rule-2 gap-2 shadow-inner">
      {formats.map(({ value, label, icon }) => {
        const isSelected = targetFormat === value;
        return (
          <button
            key={value}
            type="button"
            onClick={() => setTargetFormat(value)}
            className={`flex items-center gap-2 px-4 py-2 rounded-stock text-sm font-medium transition-colors transition-transform focus-visible:outline-2 focus-visible:outline-focus ${
              isSelected
                ? 'bg-cotton text-ink border border-rule-2 shadow-card'
                : 'text-muted hover:text-ink'
            }`}
          >
            {icon}
            <span>{label}</span>
          </button>
        );
      })}
    </div>
  );
};
