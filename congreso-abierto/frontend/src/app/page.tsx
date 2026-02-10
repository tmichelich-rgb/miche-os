'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { FeedPost, PaginatedResponse } from '@/types';

export default function HomePage() {
  const [feed, setFeed] = useState<FeedPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('');

  useEffect(() => {
    const params: Record<string, string> = {};
    if (filter) params.type = filter;
    api.feed.list(params).then((res: PaginatedResponse<FeedPost>) => {
      setFeed(res.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [filter]);

  const typeLabels: Record<string, string> = {
    BILL_CREATED: 'Nuevo Proyecto',
    BILL_MOVEMENT: 'Movimiento',
    VOTE_RESULT: 'Votación',
    ATTENDANCE_RECORD: 'Asistencia',
  };

  const typeColors: Record<string, string> = {
    BILL_CREATED: 'bg-green-100 text-green-800',
    BILL_MOVEMENT: 'bg-blue-100 text-blue-800',
    VOTE_RESULT: 'bg-purple-100 text-purple-800',
    ATTENDANCE_RECORD: 'bg-yellow-100 text-yellow-800',
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Feed Parlamentario</h1>

      <div className="flex gap-2 mb-6 flex-wrap">
        <button onClick={() => setFilter('')} className={'px-3 py-1 rounded-full text-sm ' + (!filter ? 'bg-congress-blue text-white' : 'bg-gray-200')}>Todos</button>
        {Object.entries(typeLabels).map(([key, label]) => (
          <button key={key} onClick={() => setFilter(key)} className={'px-3 py-1 rounded-full text-sm ' + (filter === key ? 'bg-congress-blue text-white' : 'bg-gray-200')}>{label}</button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-400">Cargando feed...</div>
      ) : feed.length === 0 ? (
        <div className="text-center py-12 text-gray-400">No hay eventos para mostrar</div>
      ) : (
        <div className="space-y-4">
          {feed.map((post) => (
            <article key={post.id} className="bg-white rounded-lg shadow-sm border p-4 hover:shadow-md transition">
              <div className="flex items-start justify-between mb-2">
                <span className={'inline-block px-2 py-0.5 rounded text-xs font-medium ' + (typeColors[post.type] || 'bg-gray-100')}>{typeLabels[post.type] || post.type}</span>
                <time className="text-xs text-gray-400">{new Date(post.createdAt).toLocaleDateString('es-AR')}</time>
              </div>
              <h3 className="font-semibold text-gray-900 mb-1">{post.title}</h3>
              <p className="text-sm text-gray-600 mb-3">{post.body}</p>
              <div className="flex items-center gap-4 text-xs text-gray-400">
                <span>{post._count?.comments || 0} comentarios</span>
                <span>{post._count?.reactions || 0} reacciones</span>
                {post.sourceRef && <a href={post.sourceRef.url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">Fuente oficial</a>}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
