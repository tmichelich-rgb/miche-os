export default function ComoFuncionaPage() {
  const stages = [
    { name: 'Presentación', desc: 'El diputado presenta el proyecto en Mesa de Entradas', color: 'bg-green-100' },
    { name: 'Comisiones', desc: 'Se gira a comisiones temáticas para estudio y dictamen', color: 'bg-blue-100' },
    { name: 'Dictamen', desc: 'Las comisiones emiten dictamen favorable o desfavorable', color: 'bg-yellow-100' },
    { name: 'Recinto', desc: 'Se debate y vota en la Cámara de Diputados', color: 'bg-purple-100' },
    { name: 'Cámara revisora', desc: 'Pasa al Senado para su tratamiento', color: 'bg-orange-100' },
    { name: 'Promulgación', desc: 'El Poder Ejecutivo promulga o veta la ley', color: 'bg-red-100' },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Cómo Funciona el Congreso</h1>
      <p className="text-gray-600 mb-8">El proceso legislativo argentino tiene varias etapas. Acá te explicamos cada una de forma simple.</p>

      <div className="space-y-4">
        {stages.map((stage, i) => (
          <div key={stage.name} className={'rounded-lg p-4 ' + stage.color}>
            <div className="flex items-center gap-3">
              <span className="text-2xl font-bold text-gray-400">{i + 1}</span>
              <div>
                <h3 className="font-semibold">{stage.name}</h3>
                <p className="text-sm text-gray-600">{stage.desc}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 bg-white rounded-lg border p-6">
        <h2 className="font-semibold mb-3">Estados de un Proyecto</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-sm">
          <div className="p-2 bg-gray-50 rounded"><strong>Presentado:</strong> Ingresado en mesa de entradas</div>
          <div className="p-2 bg-gray-50 rounded"><strong>En comisión:</strong> Siendo estudiado por comisiones</div>
          <div className="p-2 bg-gray-50 rounded"><strong>Con dictamen:</strong> Comisiones se pronunciaron</div>
          <div className="p-2 bg-gray-50 rounded"><strong>Aprobado:</strong> Votado favorablemente</div>
          <div className="p-2 bg-gray-50 rounded"><strong>Rechazado:</strong> Votado desfavorablemente</div>
          <div className="p-2 bg-gray-50 rounded"><strong>Archivado:</strong> Perdió estado parlamentario</div>
        </div>
      </div>
    </div>
  );
}
