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
  getAll: async (company?: string, limit: number = 100): Promise<Contact[]> => {
    const response = await api.get<Contact[]>('/api/contacts', {
      params: { company, limit },
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

