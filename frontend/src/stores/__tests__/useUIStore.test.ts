import { describe, it, expect, beforeEach } from 'vitest';
import { useUIStore } from '../useUIStore';

describe('useUIStore', () => {
  beforeEach(() => {
    useUIStore.setState({
      sidebarOpen: true,
      mode: 'light',
      globalLoading: false,
      notifications: [],
    });
    localStorage.clear();
  });

  it('toggles sidebar and sets sidebar state explicitly', () => {
    expect(useUIStore.getState().sidebarOpen).toBe(true);

    useUIStore.getState().toggleSidebar();
    expect(useUIStore.getState().sidebarOpen).toBe(false);

    useUIStore.getState().toggleSidebar();
    expect(useUIStore.getState().sidebarOpen).toBe(true);

    useUIStore.getState().setSidebarOpen(false);
    expect(useUIStore.getState().sidebarOpen).toBe(false);
  });

  it('toggles theme between light and dark', () => {
    expect(useUIStore.getState().mode).toBe('light');

    useUIStore.getState().toggleTheme();
    expect(useUIStore.getState().mode).toBe('dark');

    useUIStore.getState().toggleTheme();
    expect(useUIStore.getState().mode).toBe('light');
  });

  it('sets global loading state', () => {
    expect(useUIStore.getState().globalLoading).toBe(false);

    useUIStore.getState().setGlobalLoading(true);
    expect(useUIStore.getState().globalLoading).toBe(true);

    useUIStore.getState().setGlobalLoading(false);
    expect(useUIStore.getState().globalLoading).toBe(false);
  });

  it('adds, removes, and clears notifications with UUIDs', () => {
    const { addNotification, removeNotification, clearNotifications } = useUIStore.getState();

    addNotification({ type: 'success', message: 'Email sent successfully!' });
    addNotification({ type: 'error', message: 'Rate limit hit!' });

    let notifications = useUIStore.getState().notifications;
    expect(notifications.length).toBe(2);
    expect(notifications[0].message).toBe('Email sent successfully!');
    expect(notifications[0].type).toBe('success');
    expect(notifications[0].id).toBeDefined();

    const idToRemove = notifications[0].id;
    removeNotification(idToRemove);

    notifications = useUIStore.getState().notifications;
    expect(notifications.length).toBe(1);
    expect(notifications[0].message).toBe('Rate limit hit!');

    clearNotifications();
    expect(useUIStore.getState().notifications).toEqual([]);
  });
});
