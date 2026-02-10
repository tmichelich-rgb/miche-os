'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

export default function ExplorerPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any>(null);
  const [legislators, setLegislators] = useState<any[]>([]);

  useEffect(() => {
    api.legislators.list({ limit: '50' }).then((res: any) => setLegislators(res.data));
  }, []);

  const handleSearch = async () => {
    if (!query.trim()) return;
    const res = await api.search(query);
    setResults(res);
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Explorar</h1>

      <div className="flex gap-2 mb-6">
        <input type="text" value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleSearch()} placeholder="Buscar diputados, proyectos..." className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-congress-blue" />
        <button onClick={handleSearch} className="px-6 py-2 bg-congress-blue text-white rounded-lg hover:bg-blue-800 transition">Buscar</button>
      </div>

      {results && (
        <div className="mb-8">
          <h2 className="font-semibold mb-2">Resultados de búsqueda</h2>
          {results.legislators?.hits?.length > 0 && (
            <div className="mb-4">
              <h3 className="text-sm text-gray-500 mb-1">Diputados</h3>
              {results.legislators.hits.map((leg: any) => (
                <a key={leg.id} href={'/legislator/' + leg.id} className="block p-2 hover:bg-gray-50 rounded">{leg.fullName}</a>
              ))}
            </div>
          )}
          {results.bills?.hits?.length > 0 && (
            <div>
              <h3 className="text-sm text-gray-500 mb-1">Proyectos</h3>
              {results.bills.hits.map((bill: any) => (
                <a key={bill.id} href={'/bill/' + bill.id} className="block p-2 hover:bg-gray-50 rounded">{bill.externalId} — {bill.title}</a>
              ))}
            </div>
          )}
        </div>
      )}

      <h2 className="font-semibold mb-3">Diputados</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {legislators.map((leg: any) => (
          <a key={leg.id} href={'/legislator/' + leg.id} className="bg-white rounded-lg shadow-sm border p-3 hover:shadow-md transition">
            <div className="font-medium">{leg.fullName}</div>
            <div className="text-sm text-gray-500">{leg.block?.name} — {leg.province?.name}</div>
          </a>
        ))}
      </div>
    </div>
  );
}
