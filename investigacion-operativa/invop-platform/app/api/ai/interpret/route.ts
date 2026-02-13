import { NextRequest, NextResponse } from 'next/server';
import { getAnthropic } from '@/lib/anthropic';

// POST /api/ai/interpret — AI interprets solver results into actionable insights
export async function POST(request: NextRequest) {
  try {
    const { module, input_data, output_data, store_name } = await request.json();

    if (!module || !output_data) {
      return NextResponse.json({ error: 'module and output_data required' }, { status: 400 });
    }

    const message = await getAnthropic().messages.create({
      model: 'claude-sonnet-4-5-20250514',
      max_tokens: 2000,
      messages: [
        {
          role: 'user',
          content: `Sos un consultor de negocios que explica resultados de optimización a emprendedores sin conocimiento técnico.

## Contexto
${store_name ? `Tienda: ${store_name}` : 'Negocio del cliente'}
Módulo: ${module}

## Datos de Entrada
${JSON.stringify(input_data, null, 2)}

## Resultado del Solver
${JSON.stringify(output_data, null, 2)}

## Instrucciones
Generá una interpretación en JSON con esta estructura:
{
  "summary": "Resumen ejecutivo en 1-2 oraciones. Empezá con el resultado principal.",
  "key_metrics": [
    {"label": "Nombre de la métrica", "value": "Valor formateado", "trend": "up|down|neutral"}
  ],
  "actions": [
    "Acción concreta que el merchant debe tomar"
  ],
  "explanation": "Explicación detallada en lenguaje simple, sin fórmulas. Explicá el POR QUÉ de cada recomendación.",
  "risk_notes": "Advertencias o supuestos importantes a tener en cuenta"
}

### Reglas:
- Hablá en español rioplatense (vos, tuteá)
- Usá números redondeados y moneda local ($)
- Las acciones deben ser específicas y accionables
- No uses jerga técnica (no digas "lote económico", decí "cantidad óptima a pedir")
- Si detectás riesgos o anomalías en los datos, mencionalo
- Respondé SOLO con JSON válido`,
        },
      ],
    });

    const aiText = message.content[0].type === 'text' ? message.content[0].text : '';
    let interpretation;
    try {
      interpretation = JSON.parse(aiText);
    } catch {
      const jsonMatch = aiText.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        interpretation = JSON.parse(jsonMatch[0]);
      } else {
        throw new Error('Claude did not return valid JSON');
      }
    }

    return NextResponse.json({
      success: true,
      interpretation,
      tokens_used: message.usage.input_tokens + message.usage.output_tokens,
    });
  } catch (e) {
    console.error('[AI Interpret Error]', e);
    return NextResponse.json(
      { error: 'AI interpretation failed', detail: (e as Error).message },
      { status: 500 }
    );
  }
}
