import { create } from 'zustand';

export type NotifyType = 'success' | 'error' | 'info';

interface Notification {
  id: number;
  type: NotifyType;
  message: string;
}

interface NotifyStore {
  notification: Notification | null;
  notify: (type: NotifyType, message: string) => void;
  dismiss: () => void;
}

let _id = 0;

export const useNotifyStore = create<NotifyStore>((set, get) => ({
  notification: null,
  notify(type, message) {
    const id = ++_id;
    set({ notification: { id, type, message } });
    // Автосброс через 4 секунды
    setTimeout(() => {
      if (get().notification?.id === id) set({ notification: null });
    }, 4000);
  },
  dismiss() {
    set({ notification: null });
  },
}));
