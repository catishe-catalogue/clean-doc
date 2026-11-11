'use client';
import { useEffect, useRef } from 'react';
import { SSEProgressPayload } from '@/lib/types';

export function useSSEStream(
  streamUrl: string | null,
  onMessage: (payload: SSEProgressPayload) => void,
  onError?: () => void,
) {
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!streamUrl) return;

    const es = new EventSource(streamUrl);
    esRef.current = es;

    es.onmessage = (e) => {
      try {
        const payload = JSON.parse(e.data as string) as SSEProgressPayload;
        onMessage(payload);
        if (payload.status === 'completed' || payload.status === 'failed') {
          es.close();
        }
      } catch {
        // ignore malformed event
      }
    };

    es.onerror = () => {
      es.close();
      onError?.();
    };

    return () => {
      es.close();
    };
  }, [streamUrl]); // eslint-disable-line react-hooks/exhaustive-deps
}
