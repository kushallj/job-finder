import { describe, it, expect } from 'vitest';
import {
  formatDate,
  formatDateTime,
  formatRelativeTime,
  formatNumber,
  formatPercentage,
  formatScore,
  truncateText,
  capitalizeFirst,
  formatStatus,
  formatSource,
} from '../formatters';

describe('formatters utility module', () => {
  describe('formatDate', () => {
    it('returns N/A for null or empty input', () => {
      expect(formatDate(null)).toBe('N/A');
      expect(formatDate('')).toBe('N/A');
    });

    it('formats a valid ISO date string correctly', () => {
      const formatted = formatDate('2026-08-31T10:00:00Z');
      expect(formatted).toBe('Aug 31, 2026');
    });

    it('returns Invalid date for malformed string', () => {
      expect(formatDate('invalid-date-string')).toBe('Invalid date');
    });
  });

  describe('formatDateTime', () => {
    it('returns N/A for null or empty input', () => {
      expect(formatDateTime(null)).toBe('N/A');
      expect(formatDateTime('')).toBe('N/A');
    });

    it('formats a valid ISO datetime string correctly', () => {
      const formatted = formatDateTime('2026-08-31T15:30:00Z');
      expect(formatted).toContain('Aug 31, 2026');
    });

    it('returns Invalid date for malformed input', () => {
      expect(formatDateTime('not-a-date')).toBe('Invalid date');
    });
  });

  describe('formatRelativeTime', () => {
    it('returns N/A for null or empty string', () => {
      expect(formatRelativeTime(null)).toBe('N/A');
      expect(formatRelativeTime('')).toBe('N/A');
    });

    it('formats relative distance with suffix', () => {
      const now = new Date().toISOString();
      const formatted = formatRelativeTime(now);
      expect(formatted).toContain('ago');
    });

    it('returns Invalid date for malformed string', () => {
      expect(formatRelativeTime('not-a-date')).toBe('Invalid date');
    });
  });

  describe('formatNumber', () => {
    it('returns 0 for null, undefined, or 0', () => {
      expect(formatNumber(null)).toBe('0');
      expect(formatNumber(undefined)).toBe('0');
      expect(formatNumber(0)).toBe('0');
    });

    it('formats large numbers with commas', () => {
      expect(formatNumber(1250000)).toBe('1,250,000');
      expect(formatNumber(42)).toBe('42');
    });
  });

  describe('formatPercentage', () => {
    it('returns 0% for null or undefined', () => {
      expect(formatPercentage(null)).toBe('0%');
      expect(formatPercentage(undefined)).toBe('0%');
    });

    it('formats percentage with specified decimals', () => {
      expect(formatPercentage(85.678, 1)).toBe('85.7%');
      expect(formatPercentage(85.678, 2)).toBe('85.68%');
      expect(formatPercentage(100, 0)).toBe('100%');
    });
  });

  describe('formatScore', () => {
    it('returns N/A and grey color for null or undefined', () => {
      expect(formatScore(null)).toEqual({ value: 'N/A', color: 'text.grey' });
      expect(formatScore(undefined)).toEqual({ value: 'N/A', color: 'text.grey' });
    });

    it('returns success.main for score >= 80', () => {
      expect(formatScore(95)).toEqual({ value: '95%', color: 'success.main' });
      expect(formatScore(80)).toEqual({ value: '80%', color: 'success.main' });
    });

    it('returns warning.main for score >= 60 and < 80', () => {
      expect(formatScore(75)).toEqual({ value: '75%', color: 'warning.main' });
      expect(formatScore(60)).toEqual({ value: '60%', color: 'warning.main' });
    });

    it('returns error.main for score < 60', () => {
      expect(formatScore(45)).toEqual({ value: '45%', color: 'error.main' });
      expect(formatScore(0)).toEqual({ value: '0%', color: 'error.main' });
    });
  });

  describe('truncateText', () => {
    it('returns empty string for null or empty input', () => {
      expect(truncateText(null)).toBe('');
      expect(truncateText('')).toBe('');
    });

    it('returns untouched text if length is <= maxLength', () => {
      expect(truncateText('Short text', 50)).toBe('Short text');
    });

    it('truncates and appends ellipsis if length > maxLength', () => {
      expect(truncateText('This is a longer text string that needs truncation', 15)).toBe('This is a longe...');
    });
  });

  describe('capitalizeFirst', () => {
    it('returns empty string for null or empty input', () => {
      expect(capitalizeFirst(null)).toBe('');
      expect(capitalizeFirst('')).toBe('');
    });

    it('capitalizes first letter and lowercases remainder', () => {
      expect(capitalizeFirst('hello')).toBe('Hello');
      expect(capitalizeFirst('WORLD')).toBe('World');
      expect(capitalizeFirst('jAVA sCRIPT')).toBe('Java script');
    });
  });

  describe('formatStatus', () => {
    it('returns default for null or unknown status', () => {
      expect(formatStatus(null)).toEqual({ label: 'Unknown', color: 'default' });
      expect(formatStatus('custom_state')).toEqual({ label: 'Custom_state', color: 'default' });
    });

    it('maps known statuses correctly', () => {
      expect(formatStatus('sent')).toEqual({ label: 'Sent', color: 'success' });
      expect(formatStatus('bounced')).toEqual({ label: 'Bounced', color: 'error' });
      expect(formatStatus('replied')).toEqual({ label: 'Replied', color: 'success' });
      expect(formatStatus('no_response')).toEqual({ label: 'No Response', color: 'warning' });
      expect(formatStatus('failed')).toEqual({ label: 'Failed', color: 'error' });
      expect(formatStatus('followed_up')).toEqual({ label: 'Followed Up', color: 'success' });
      expect(formatStatus('pending')).toEqual({ label: 'Pending', color: 'default' });
      expect(formatStatus('applied')).toEqual({ label: 'Applied', color: 'success' });
      expect(formatStatus('rejected')).toEqual({ label: 'Rejected', color: 'error' });
      expect(formatStatus('interview')).toEqual({ label: 'Interview', color: 'success' });
    });

    it('handles uppercase status strings', () => {
      expect(formatStatus('SENT')).toEqual({ label: 'Sent', color: 'success' });
      expect(formatStatus('REPLIED')).toEqual({ label: 'Replied', color: 'success' });
    });
  });

  describe('formatSource', () => {
    it('returns Unknown for null or empty string', () => {
      expect(formatSource(null)).toBe('Unknown');
      expect(formatSource('')).toBe('Unknown');
    });

    it('capitalizes source name', () => {
      expect(formatSource('linkedin')).toBe('Linkedin');
      expect(formatSource('GREENHOUSE')).toBe('Greenhouse');
    });
  });
});
