'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { useParams } from 'next/navigation';

export default function LegislatorPage() {
  const params = useParams();
  const [legislator, setLegislator] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (params.id) {
      api.legislators.get(params.id as string).then(setLegislator).finally(() => setLoading(false));
    }
  }, [params.id]);

  if (loading) return <div className="text-center py-12 text-gray-400">Cargando perfil...</div>;
  if (!legislator) return <div className="text-center py-12">Diputado no encontrado</div>;

  const metric = legislator.metrics?.[0];

  return (
    <div>
      <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <div className="flex items-start gap-4">
          <div className="w-20 h-20 bg-gray-200 rounded-full flex items-center justify-center text-2xl text-gray-400">
            {legislator.firstName?.[0]}{legislator.lastName?.[0]}
          </div>
          <div>
            <h1 className="text-2xl font-bold">{legislator.fullName}</h1>
            <p className="text-gray-600">{legislator.block?.name} — {legislator.province?.name}</p>
            <p className="text-sm text-gray-400">Cámara de Diputados</p>
          </div>
        </div>
      </div>

      {metric && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow-sm border p-4 text-center">
            <div className="text-2xl font-bold text-congress-blue">{metric.billsAuthored}</div>
            <div className="text-xs text-gray-500">Proyectos (autor)</div>
          </div>
          <div className="bg-white rounded-lg shadow-sm border p-4 text-center">
            <div className="text-2xl font-bold text-congress-blue">{Math.round(metric.attendanceRate * 100)}%</div>
            <div className="text-xs text-gray-500">Asistencia</div>
          </div>
          <div className="bg-white rounded-lg shadow-sm border p-4 text-center">
            <div className="text-2xl font-bold text-congress-blue">{Math.round(metric.voteParticipationRate * 100)}%</div>
            <div className="text-xs text-gray-500">Participación en votaciones</div>
          </div>
          <div className="bg-white rounded-lg shadow-sm border p-4 text-center">
            <div className="text-2xl font-bold text-congress-blue">{Math.round(metric.advancementRate * 100)}%</div>
            <div className="text-xs text-gray-500">Tasa de avance</div>
          </div>
        </div>
      )}

      {legislator.commissions?.length > 0 && (
        <section className="mb-6">
          <h2 className="font-semibold mb-2">Comisiones</h2>
          <div className="space-y-1">
            {legislator.commissions.map((c: any) => (
              <div key={c.id} className="bg-white rounded border p-2 text-sm">
                {c.commission.name} <span className="text-gray-400">({c.role})</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {legislator.billAuthors?.length > 0 && (
        <section className="mb-6">
          <h2 className="font-semibold mb-2">Últimos Proyectos</h2>
          <div className="space-y-2">
            {legislator.billAuthors.map((ba: any) => (
              <a key={ba.bill.id} href={'/bill/' + ba.bill.id} className="block bg-white rounded border p-3 hover:shadow-sm transition">
                <div className="font-medium text-sm">{ba.bill.externalId}: {ba.bill.title}</div>
                <div className="text-xs text-gray-400">{ba.role} — Estado: {ba.bill.status}</div>
              </a>
            ))}
          </div>
        </section>
      )}

      {legislator.voteResults?.length > 0 && (
        <section>
          <h2 className="font-semibold mb-2">Últimas Votaciones</h2>
          <div className="space-y-2">
            {legislator.voteResults.map((vr: any) => (
              <div key={vr.id} className="bg-white rounded border p-3 text-sm">
                <div className="font-medium">{vr.voteEvent?.title}</div>
                <div className="text-xs text-gray-400">
                  Votó: <span className="font-medium">{vr.vote}</span> — Resultado: {vr.voteEvent?.result}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
