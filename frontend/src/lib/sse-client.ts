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

    const handleEvent = (e: Event) => {
      const msg = e as MessageEvent;
      if (!msg.data) return;
      try {
        const payload = JSON.parse(msg.data as string) as SSEProgressPayload;
        onMessage(payload);
        if (payload.status === 'completed' || payload.status === 'failed') {
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
      if (es.readyState === EventSource.CLOSED) return;
      es.close();
      onError?.();
    };

    return () => {
      es.close();
    };
  }, [streamUrl]); // eslint-disable-line react-hooks/exhaustive-deps
}
