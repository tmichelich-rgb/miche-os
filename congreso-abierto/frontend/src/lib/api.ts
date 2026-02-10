const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000/api/v1';

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(API_BASE + endpoint, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) throw new Error('API error: ' + res.status + ' ' + res.statusText);
  return res.json();
}

export const api = {
  legislators: {
    list: (params?: Record<string, string>) => {
      const qs = params ? '?' + new URLSearchParams(params).toString() : '';
      return fetchAPI<any>('/legislators' + qs);
    },
    get: (id: string) => fetchAPI<any>('/legislators/' + id),
    metrics: (id: string) => fetchAPI<any>('/legislators/' + id + '/metrics'),
  },
  bills: {
    list: (params?: Record<string, string>) => {
      const qs = params ? '?' + new URLSearchParams(params).toString() : '';
      return fetchAPI<any>('/bills' + qs);
    },
    get: (id: string) => fetchAPI<any>('/bills/' + id),
  },
  feed: {
    list: (params?: Record<string, string>) => {
      const qs = params ? '?' + new URLSearchParams(params).toString() : '';
      return fetchAPI<any>('/feed' + qs);
    },
    get: (id: string) => fetchAPI<any>('/feed/' + id),
  },
  comments: {
    byPost: (postId: string) => fetchAPI<any>('/comments/post/' + postId),
    create: (data: any) => fetchAPI<any>('/comments', { method: 'POST', body: JSON.stringify(data) }),
  },
  reactions: {
    byPost: (postId: string) => fetchAPI<any>('/reactions/post/' + postId),
    toggle: (data: any) => fetchAPI<any>('/reactions/toggle', { method: 'POST', body: JSON.stringify(data) }),
  },
  search: (q: string) => fetchAPI<any>('/search?q=' + encodeURIComponent(q)),
};
