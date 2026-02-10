'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { useParams } from 'next/navigation';

export default function BillPage() {
  const params = useParams();
  const [bill, setBill] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (params.id) api.bills.get(params.id as string).then(setBill).finally(() => setLoading(false));
  }, [params.id]);

  if (loading) return <div className="text-center py-12 text-gray-400">Cargando proyecto...</div>;
  if (!bill) return <div className="text-center py-12">Proyecto no encontrado</div>;

  const statusLabels: Record<string, string> = {
    PRESENTED: 'Presentado', IN_COMMITTEE: 'En comisión', APPROVED_COMMITTEE: 'Aprobado en comisión',
    APPROVED_CHAMBER: 'Aprobado en cámara', APPROVED: 'Aprobado', REJECTED: 'Rechazado',
  };

  return (
    <div>
      <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <div className="flex items-start justify-between mb-2">
          <span className="text-sm text-gray-500">{bill.externalId}</span>
          <span className="px-2 py-0.5 rounded bg-blue-100 text-blue-800 text-xs font-medium">{statusLabels[bill.status] || bill.status}</span>
        </div>
        <h1 className="text-xl font-bold mb-2">{bill.title}</h1>
        {bill.summary && <p className="text-gray-600 text-sm mb-3">{bill.summary}</p>}
        {bill.sourceUrl && <a href={bill.sourceUrl} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-500 hover:underline">Ver en sitio oficial</a>}
      </div>

      <section className="mb-6">
        <h2 className="font-semibold mb-2">Autores</h2>
        <div className="flex flex-wrap gap-2">
          {bill.authors?.map((a: any) => (
            <a key={a.legislator.id} href={'/legislator/' + a.legislator.id} className="bg-white rounded border px-3 py-1 text-sm hover:shadow-sm transition">
              {a.legislator.fullName} <span className="text-gray-400">({a.role})</span>
            </a>
          ))}
        </div>
      </section>

      <section>
        <h2 className="font-semibold mb-2">Historial de Movimientos</h2>
        <div className="relative">
          <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200"></div>
          <div className="space-y-4">
            {bill.movements?.map((mov: any, i: number) => (
              <div key={mov.id || i} className="relative pl-10">
                <div className="absolute left-2.5 top-1.5 w-3 h-3 rounded-full bg-congress-blue border-2 border-white"></div>
                <div className="bg-white rounded border p-3">
                  <div className="text-sm font-medium">{mov.description}</div>
                  <div className="text-xs text-gray-400 mt-1">{new Date(mov.date).toLocaleDateString('es-AR')}</div>
                  {mov.toStatus && <div className="text-xs mt-1"><span className="text-gray-400">Estado:</span> {statusLabels[mov.toStatus] || mov.toStatus}</div>}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
