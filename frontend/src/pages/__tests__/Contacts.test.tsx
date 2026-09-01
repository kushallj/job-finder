import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import React from 'react';
import { renderWithProviders } from '../../test/test-utils';
import { Contacts } from '../Contacts';
import { contactsApi } from '../../api';

describe('Contacts Page Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders contacts table and searches contacts', async () => {
    const mockContacts = {
      contacts: [
        {
          id: 1,
          name: 'Sarah Jenkins',
          company: 'Stripe',
          title: 'Director of Infrastructure',
          email: 'sjenkins@stripe.com',
          confidence_score: 95,
        },
      ],
      pagination: { total: 1, pages: 1, page: 1, limit: 100 },
    };

    vi.spyOn(contactsApi, 'getAll').mockResolvedValue(mockContacts);

    renderWithProviders(<Contacts />);

    await waitFor(() => {
      expect(screen.getByText(/Sarah Jenkins/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Director of Infrastructure/i)).toBeInTheDocument();
    expect(screen.getByText('sjenkins@stripe.com')).toBeInTheDocument();

    const searchInput = screen.getByPlaceholderText(/Search by name, title, company, or email\.\.\./i);
    fireEvent.change(searchInput, { target: { value: 'Sarah' } });


    expect(screen.getByText(/Sarah Jenkins/i)).toBeInTheDocument();
  });
});
