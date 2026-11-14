'use client';
import { useEffect, useRef } from 'react';
import { SSEProgressPayload } from '@/lib/types';
import { apiClient } from '@/lib/api-client';

interface JobSnapshotDto {
  id: string;
  status: 'pending' | 'queued' | 'processing' | 'completed' | 'failed';
  progress_percent: number;
  current_step: string;
  page_count?: number | null;
  is_preview_only?: boolean;
  preview_urls?: string[];
  download_url?: string | null;
  error_message?: string | null;
}

export function useSSEStream(
  streamUrl: string | null,
  onMessage: (payload: SSEProgressPayload) => void,
  onError?: () => void,
  jobId?: string | null,
) {
  const esRef = useRef<EventSource | null>(null);
  const pollTimerRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const pollDelayRef = useRef<number>(2000);
  const reconnectAttemptsRef = useRef<number>(0);
  const isFinishedRef = useRef<boolean>(false);

  useEffect(() => {
    if (!streamUrl) {
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      return;
    }

    isFinishedRef.current = false;
    reconnectAttemptsRef.current = 0;
    pollDelayRef.current = 2000;

    const stopPolling = () => {
      if (pollTimerRef.current) {
        clearTimeout(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };

    const schedulePoll = (id: string) => {
      if (isFinishedRef.current) return;
      stopPolling();
      pollTimerRef.current = setTimeout(async () => {
        if (isFinishedRef.current) return;
        try {
          const snapshot = await apiClient<JobSnapshotDto>(`/api/v1/convert/jobs/${id}`);
          const payload: SSEProgressPayload = {
            job_id: String(snapshot.id),
            status: snapshot.status,
            progress_percent: snapshot.progress_percent,
            current_step: snapshot.current_step,
            page_total: snapshot.page_count ?? undefined,
            preview_urls: snapshot.preview_urls,
            download_url: snapshot.download_url,
            is_preview_only: snapshot.is_preview_only,
            error: snapshot.error_message,
          };
          onMessage(payload);

          if (payload.status === 'completed' || payload.status === 'failed') {
            isFinishedRef.current = true;
            stopPolling();
            if (esRef.current) esRef.current.close();
            return;
          }

          // Экспоненциальный backoff: 2 -> 4 -> 8 -> 16 -> 30s
          pollDelayRef.current = Math.min(pollDelayRef.current * 2, 30000);
          schedulePoll(id);
        } catch {
          pollDelayRef.current = Math.min(pollDelayRef.current * 2, 30000);
          schedulePoll(id);
        }
      }, pollDelayRef.current);
    };

    const connectSSE = () => {
      if (isFinishedRef.current) return;
      if (esRef.current) {
        esRef.current.close();
      }

      const es = new EventSource(streamUrl);
      esRef.current = es;

      const handleEvent = (e: Event) => {
        const msg = e as MessageEvent;
        if (!msg.data) return;
        try {
          const payload = JSON.parse(msg.data as string) as SSEProgressPayload;
          // При успешных сообщениях от SSE останавливаем фолбэк-поллинг
          stopPolling();
          reconnectAttemptsRef.current = 0;
          pollDelayRef.current = 2000;

          onMessage(payload);
          if (payload.status === 'completed' || payload.status === 'failed') {
            isFinishedRef.current = true;
            es.close();
          }
        } catch {
          // ignore malformed event
        }
      };

      es.addEventListener('message', handleEvent);
      es.addEventListener('progress', handleEvent);
      es.addEventListener('complete', handleEvent);
      es.addEventListener('error', handleEvent);

      es.onerror = () => {
        if (isFinishedRef.current) return;
        es.close();

        // 1. Активация поллинг-фолбэка только при падении SSE
        const targetJobId = jobId || streamUrl.split('/jobs/')[1]?.split('/')[0];
        if (targetJobId && !isFinishedRef.current) {
          schedulePoll(targetJobId);
        }

        // 2. До 3 попыток переподключения SSE
        if (reconnectAttemptsRef.current < 3) {
          reconnectAttemptsRef.current += 1;
          const reconnectDelay = reconnectAttemptsRef.current * 2000;
          reconnectTimerRef.current = setTimeout(() => {
            if (!isFinishedRef.current) {
              connectSSE();
            }
          }, reconnectDelay);
        } else {
          onError?.();
        }
      };
    };

    connectSSE();

    return () => {
      isFinishedRef.current = true;
      if (esRef.current) esRef.current.close();
      stopPolling();
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
    };
  }, [streamUrl, jobId]); // eslint-disable-line react-hooks/exhaustive-deps
}
