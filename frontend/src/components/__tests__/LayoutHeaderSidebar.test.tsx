import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { Route, Routes } from 'react-router-dom';
import { renderWithProviders } from '../../test/test-utils';
import { Sidebar } from '../layout/Sidebar';
import { Header } from '../layout/Header';
import { Layout } from '../layout/Layout';
import { useUIStore } from '../../stores/useUIStore';

describe('Layout, Header, and Sidebar Navigation', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    useUIStore.setState({ sidebarOpen: true });
  });

  it('renders Sidebar navigation items with active links', () => {
    renderWithProviders(<Sidebar mobileOpen={false} onMobileClose={vi.fn()} />, {
      initialEntries: ['/jobs'],
    });

    const items = screen.getAllByText(/Command Center/i);
    expect(items.length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Opportunities & Jobs/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/AI Agents/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Global Remote Radar/i).length).toBeGreaterThan(0);
  });

  it('renders Header with title and triggers menu click', () => {
    const onMenuClick = vi.fn();
    renderWithProviders(<Header onMenuClick={onMenuClick} title="Opportunities & Jobs" />);

    expect(screen.getByText(/Opportunities & Jobs/i)).toBeInTheDocument();

    const menuButton = screen.getByLabelText(/open drawer/i);
    fireEvent.click(menuButton);
    expect(onMenuClick).toHaveBeenCalled();
  });

  it('renders full Layout with routed child content', () => {
    renderWithProviders(
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<div data-testid="child-content">Main Page Content</div>} />
        </Route>
      </Routes>,
      { initialEntries: ['/'] }
    );

    expect(screen.getByTestId('child-content')).toBeInTheDocument();
  });
});
