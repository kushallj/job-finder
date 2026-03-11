import { format, formatDistanceToNow, parseISO, isValid } from 'date-fns';

// Date formatting utilities
export const formatDate = (dateString: string | null): string => {
  if (!dateString) return 'N/A';
  try {
    const date = parseISO(dateString);
    if (!isValid(date)) return 'Invalid date';
    return format(date, 'MMM d, yyyy');
  } catch {
    return 'Invalid date';
  }
};

export const formatDateTime = (dateString: string | null): string => {
  if (!dateString) return 'N/A';
  try {
    const date = parseISO(dateString);
    if (!isValid(date)) return 'Invalid date';
    return format(date, 'MMM d, yyyy h:mm a');
  } catch {
    return 'Invalid date';
  }
};

export const formatRelativeTime = (dateString: string | null): string => {
  if (!dateString) return 'N/A';
  try {
    const date = parseISO(dateString);
    if (!isValid(date)) return 'Invalid date';
    return formatDistanceToNow(date, { addSuffix: true });
  } catch {
    return 'Invalid date';
  }
};

// Number formatting utilities
export const formatNumber = (num: number | null | undefined): string => {
  if (num === null || num === undefined) return '0';
  return new Intl.NumberFormat('en-US').format(num);
};

export const formatPercentage = (num: number | null | undefined, decimals: number = 1): string => {
  if (num === null || num === undefined) return '0%';
  return `${num.toFixed(decimals)}%`;
};

// Score formatting
export const formatScore = (score: number | null | undefined): { value: string; color: string } => {
  if (score === null || score === undefined) {
    return { value: 'N/A', color: 'text.grey' };
  }
  if (score >= 80) {
    return { value: `${score}%`, color: 'success.main' };
  } else if (score >= 60) {
    return { value: `${score}%`, color: 'warning.main' };
  } else {
    return { value: `${score}%`, color: 'error.main' };
  }
};

// Text utilities
export const truncateText = (text: string | null, maxLength: number = 100): string => {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '...';
};

export const capitalizeFirst = (text: string | null): string => {
  if (!text) return '';
  return text.charAt(0).toUpperCase() + text.slice(1).toLowerCase();
};

// Status formatting
export const formatStatus = (status: string | null): { label: string; color: 'success' | 'warning' | 'error' | 'default' } => {
  if (!status) return { label: 'Unknown', color: 'default' };
  
  const statusMap: Record<string, { label: string; color: 'success' | 'warning' | 'error' | 'default' }> = {
    sent: { label: 'Sent', color: 'success' },
    bounced: { label: 'Bounced', color: 'error' },
    replied: { label: 'Replied', color: 'success' },
    no_response: { label: 'No Response', color: 'warning' },
    failed: { label: 'Failed', color: 'error' },
    followed_up: { label: 'Followed Up', color: 'success' },
    pending: { label: 'Pending', color: 'default' },
    applied: { label: 'Applied', color: 'success' },
    rejected: { label: 'Rejected', color: 'error' },
    interview: { label: 'Interview', color: 'success' },
  };
  
  return statusMap[status.toLowerCase()] || { label: capitalizeFirst(status), color: 'default' };
};

// Source formatting
export const formatSource = (source: string | null): string => {
  if (!source) return 'Unknown';
  return capitalizeFirst(source);
};

