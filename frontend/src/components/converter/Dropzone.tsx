'use client';

import React, { useCallback, useRef, useState } from 'react';
import { UploadCloud, FileText, AlertCircle, CheckCircle2 } from 'lucide-react';
import { useConverterStore } from '@/store/useConverterStore';

export const Dropzone: React.FC = () => {
  const { file, setFile, status } = useConverterStore();
  const [isDragOver, setIsDragOver] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

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
    if (e.dataTransfer.files?.[0]) handleValidateAndSelect(e.dataTransfer.files[0]);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const isSuccess = status === 'completed';
  const isUploading = status === 'processing' || status === 'queued';
  const isError = status === 'failed';
  const isDisabled = isUploading;

  // Цвет рамки по состоянию — через inline style для точного token-маппинга
  const borderStyle: React.CSSProperties = {
    borderColor: isSuccess
      ? 'var(--color-paid)'
      : isError || validationError
        ? 'var(--color-danger)'
        : isDragOver
          ? 'var(--color-accent)'
          : undefined,
    borderStyle: isDragOver ? 'solid' : undefined,
    background: isDragOver
      ? 'color-mix(in oklch, var(--color-accent) 7%, var(--color-cotton))'
      : undefined,
  };

  const icon = isSuccess
    ? <CheckCircle2 className="w-7 h-7" style={{ color: 'var(--color-paid)' }} />
    : file
      ? <FileText className="w-7 h-7 text-ink" />
      : <UploadCloud className="w-7 h-7 text-muted" />;

  return (
    <div className="w-full">
      {/* Прогресс-полоска 2px сверху при загрузке */}
      {isUploading && (
        <div className="relative h-0.5 w-full mb-0 overflow-hidden rounded-t-stock">
          <div
            className="absolute inset-y-0 left-0 bg-paid"
            style={{ width: '100%', animation: 'progress-indeterminate 1.4s ease-in-out infinite' }}
          />
        </div>
      )}

      <div
        role="button"
        tabIndex={isDisabled ? -1 : 0}
        aria-label="Загрузить PDF файл"
        onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={onDrop}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); inputRef.current?.click(); } }}
        onClick={() => !isDisabled && inputRef.current?.click()}
        className={`relative border-2 border-dashed border-rule-2 rounded-stock p-8 sm:p-12 text-center cursor-pointer stock ${
          isDisabled ? 'pointer-events-none opacity-60' : ''
        }`}
        style={{
          ...borderStyle,
          transition: 'border-color 150ms ease-out, background-color 150ms ease-out',
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,application/pdf"
          onChange={(e) => e.target.files?.[0] && handleValidateAndSelect(e.target.files[0])}
          className="sr-only"
          tabIndex={-1}
        />
        <div className="flex flex-col items-center justify-center space-y-4">
          <div className="w-14 h-14 rounded-stock bg-paper border border-rule-2 text-ink flex items-center justify-center shadow-card">
            {icon}
          </div>
          <div>
            <p className="text-base sm:text-lg font-medium text-ink">
              {isSuccess
                ? 'Конвертация завершена'
                : file
                  ? file.name
                  : 'Перетащите PDF файл сюда или нажмите для выбора'}
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
        <div
          className="mt-3 flex items-center gap-2 text-xs sm:text-sm p-3 rounded-stock border"
          style={{
            color: 'var(--color-danger)',
            background: 'color-mix(in oklch, var(--color-danger) 8%, white)',
            borderColor: 'color-mix(in oklch, var(--color-danger) 30%, transparent)',
          }}
          role="alert"
          aria-live="polite"
        >
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{validationError}</span>
        </div>
      )}
    </div>
  );
};
