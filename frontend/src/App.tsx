import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider, CssBaseline } from '@mui/material';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import theme from './theme';
import Layout from './components/layout/Layout';
import Dashboard from './pages/Dashboard';
import Jobs from './pages/Jobs';
import Contacts from './pages/Contacts';
import Outreach from './pages/Outreach';
import Stats from './pages/Stats';
import StartupDiscovery from './pages/StartupDiscovery';
import Settings from './pages/Settings';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30 * 1000, // 30 seconds
    },
  },
});

const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<Dashboard />} />
              <Route path="jobs" element={<Jobs />} />
              <Route path="contacts" element={<Contacts />} />
              <Route path="outreach" element={<Outreach />} />
              <Route path="stats" element={<Stats />} />
              <Route path="discovery" element={<StartupDiscovery />} />
              <Route path="settings" element={<Settings />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );
};

export default App;

