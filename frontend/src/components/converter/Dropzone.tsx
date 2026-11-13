'use client';

import React, { useCallback, useState } from 'react';
import { UploadCloud, FileText, AlertCircle } from 'lucide-react';
import { useConverterStore } from '@/store/useConverterStore';

export const Dropzone: React.FC = () => {
  const { file, setFile, status } = useConverterStore();
  const [isDragOver, setIsDragOver] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleValidateAndSelect = (selectedFile: File) => {
    if (selectedFile.type !== 'application/pdf' && !selectedFile.name.toLowerCase().endsWith('.pdf')) {
      setValidationError('Пожалуйста, выберите файл в формате PDF');
      return;
    }
    if (selectedFile.size > 100 * 1024 * 1024) {
      setValidationError('Размер файла превышает лимит (100 МБ)');
      return;
    }
    setValidationError(null);
    setFile(selectedFile);
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleValidateAndSelect(e.dataTransfer.files[0]);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="w-full">
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={onDrop}
        className={`relative border-2 border-dashed rounded-stock p-8 sm:p-12 text-center transition-colors transition-transform cursor-pointer stock ${
          isDragOver ? 'border-accent bg-paper-2' : 'border-rule-2 hover:border-muted bg-cotton'
        } ${status === 'processing' ? 'pointer-events-none opacity-60' : ''}`}
      >
        <input
          type="file"
          accept=".pdf,application/pdf"
          onChange={(e) => e.target.files?.[0] && handleValidateAndSelect(e.target.files[0])}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer focus-visible:outline-2 focus-visible:outline-focus"
          aria-label="Выбрать PDF файл"
        />
        <div className="flex flex-col items-center justify-center space-y-4">
          <div className="w-14 h-14 rounded-stock bg-paper border border-rule-2 text-ink flex items-center justify-center shadow-card">
            {file ? <FileText className="w-7 h-7 text-ink" /> : <UploadCloud className="w-7 h-7 text-muted" />}
          </div>
          <div>
            <p className="text-base sm:text-lg font-medium text-ink">
              {file ? file.name : 'Перетащите PDF файл сюда или нажмите для выбора'}
            </p>
            <p className="text-xs sm:text-sm text-muted mt-1">
              {file ? (
                <span className="font-mono tabular-nums">{(file.size / (1024 * 1024)).toFixed(2)} МБ</span>
              ) : (
                'Поддерживаются документы до 100 МБ в PRO и до 10 МБ в базовом'
              )}
            </p>
          </div>
        </div>
      </div>
      {validationError && (
        <div className="mt-3 flex items-center gap-2 text-xs sm:text-sm text-error bg-error/10 p-3 rounded-stock border border-error/30">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{validationError}</span>
        </div>
      )}
    </div>
  );
};
