import api from '../axios';
import type {
  ContactSearchRequest,
  ContactSearchResponse,
  Contact,
} from '../types';

export const contactsApi = {
  /**
   * Search for contacts at a specific company
   */
  search: async (data: ContactSearchRequest): Promise<ContactSearchResponse> => {
    const response = await api.post<ContactSearchResponse>('/api/contacts/search', data);
    return response.data;
  },

  /**
   * Get all contacts (with optional company filter)
   */
  getAll: async (company?: string, page: number = 1, limit: number = 50): Promise<{
    contacts: Contact[];
    pagination: {
      page: number;
      limit: number;
      total: number;
      pages: number;
    };
  }> => {
    const response = await api.get('/api/contacts', {
      params: { company, page, limit },
    });
    return response.data;
  },

  /**
   * Get a specific contact by ID
   */
  getById: async (contactId: number): Promise<Contact> => {
    const response = await api.get<Contact>(`/api/contacts/${contactId}`);
    return response.data;
  },
};

