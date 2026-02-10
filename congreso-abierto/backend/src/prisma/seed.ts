import { PrismaClient } from '@prisma/client';
import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';

const prisma = new PrismaClient();

async function main() {
  console.log('🌱 Seeding database...');

  // Clean existing data
  await prisma.reaction.deleteMany();
  await prisma.comment.deleteMany();
  await prisma.report.deleteMany();
  await prisma.feedPost.deleteMany();
  await prisma.legislatorMetric.deleteMany();
  await prisma.voteResult.deleteMany();
  await prisma.voteEvent.deleteMany();
  await prisma.attendance.deleteMany();
  await prisma.session.deleteMany();
  await prisma.billMovement.deleteMany();
  await prisma.billAuthor.deleteMany();
  await prisma.bill.deleteMany();
  await prisma.legislatorCommission.deleteMany();
  await prisma.commission.deleteMany();
  await prisma.legislator.deleteMany();
  await prisma.block.deleteMany();
  await prisma.province.deleteMany();
  await prisma.sourceRef.deleteMany();
  await prisma.ingestionRun.deleteMany();
  await prisma.user.deleteMany();

  console.log('  Cleaned existing data');

  // Create a seed source ref for traceability
  const seedSourceRef = await prisma.sourceRef.create({
    data: {
      url: 'seed/fixtures',
      fetchedAt: new Date(),
      checksum: crypto.createHash('sha256').update('seed-data').digest('hex'),
      rawLocation: 'test/fixtures/',
      sourceType: 'fixture',
      dataType: 'seed',
    },
  });

  // Load fixtures
  const fixturesDir = path.join(__dirname, '../../test/fixtures');

  // === LEGISLATORS ===
  const legislatorsRaw = JSON.parse(fs.readFileSync(path.join(fixturesDir, 'legislators.json'), 'utf-8'));
  
  const provinceMap = new Map<string, string>();
  const blockMap = new Map<string, string>();
  const legislatorMap = new Map<string, string>();

  for (const raw of legislatorsRaw) {
    if (!provinceMap.has(raw.province_code)) {
      const province = await prisma.province.create({
        data: { name: raw.province_name, code: raw.province_code },
      });
      provinceMap.set(raw.province_code, province.id);
    }

    if (!blockMap.has(raw.block_name)) {
      const block = await prisma.block.create({
        data: { name: raw.block_name, shortName: raw.block_short },
      });
      blockMap.set(raw.block_name, block.id);
    }

    const legislator = await prisma.legislator.create({
      data: {
        externalId: raw.external_id,
        firstName: raw.first_name,
        lastName: raw.last_name,
        fullName: raw.last_name + ', ' + raw.first_name,
        photoUrl: raw.photo_url || null,
        email: raw.email || null,
        chamber: 'DIPUTADOS',
        termStart: raw.term_start ? new Date(raw.term_start) : null,
        termEnd: raw.term_end ? new Date(raw.term_end) : null,
        isActive: raw.is_active !== false,
        provinceId: provinceMap.get(raw.province_code)!,
        blockId: blockMap.get(raw.block_name)!,
      },
    });
    legislatorMap.set(raw.external_id, legislator.id);
  }
  console.log('  Created ' + legislatorsRaw.length + ' legislators');

  // === COMMISSIONS ===
  const commissions = [
    { name: 'Comisión de Energía y Combustibles', externalId: 'COM-001' },
    { name: 'Comisión de Legislación Penal', externalId: 'COM-002' },
    { name: 'Comisión de Educación', externalId: 'COM-003' },
    { name: 'Comisión de Cultura', externalId: 'COM-004' },
    { name: 'Comisión de Presupuesto y Hacienda', externalId: 'COM-005' },
  ];

  for (const com of commissions) {
    const commission = await prisma.commission.create({ data: com });
    // Assign some legislators to commissions
    const assignments: { legExtId: string; comId: string; role: string }[] = [
      { legExtId: 'DIP-001', comId: commission.id, role: 'MEMBER' },
      { legExtId: 'DIP-003', comId: commission.id, role: 'MEMBER' },
    ];
    if (com.externalId === 'COM-001') {
      assignments.push({ legExtId: 'DIP-004', comId: commission.id, role: 'PRESIDENT' });
    }
    for (const a of assignments) {
      const legId = legislatorMap.get(a.legExtId);
      if (legId) {
        await prisma.legislatorCommission.create({
          data: { legislatorId: legId, commissionId: a.comId, role: a.role as any },
        });
      }
    }
  }
  console.log('  Created ' + commissions.length + ' commissions');

  // === BILLS ===
  const billsRaw = JSON.parse(fs.readFileSync(path.join(fixturesDir, 'bills.json'), 'utf-8'));

  for (const raw of billsRaw) {
    const bill = await prisma.bill.create({
      data: {
        externalId: raw.external_id,
        title: raw.title,
        summary: raw.summary || null,
        type: raw.type || 'PROJECT',
        status: raw.status || 'PRESENTED',
        presentedDate: raw.presented_date ? new Date(raw.presented_date) : null,
        chamber: 'DIPUTADOS',
        sourceUrl: raw.source_url || null,
        period: raw.period || null,
        sourceRefId: seedSourceRef.id,
      },
    });

    if (raw.authors) {
      for (const author of raw.authors) {
        const legId = legislatorMap.get(author.external_id);
        if (legId) {
          await prisma.billAuthor.create({
            data: { billId: bill.id, legislatorId: legId, role: author.role || 'AUTHOR' },
          });
        }
      }
    }

    if (raw.movements) {
      for (let i = 0; i < raw.movements.length; i++) {
        const mov = raw.movements[i];
        await prisma.billMovement.create({
          data: {
            date: new Date(mov.date),
            description: mov.description,
            fromStatus: mov.from_status || null,
            toStatus: mov.to_status || null,
            orderIndex: i,
            billId: bill.id,
            sourceRefId: seedSourceRef.id,
          },
        });
      }
    }

    // Create feed post for bill
    const firstAuthor = raw.authors?.[0];
    const legId = firstAuthor ? legislatorMap.get(firstAuthor.external_id) : null;
    
    await prisma.feedPost.create({
      data: {
        type: 'BILL_CREATED',
        title: 'Nuevo proyecto: ' + raw.external_id,
        body: raw.title,
        payload: { externalId: raw.external_id, title: raw.title, type: raw.type },
        entityType: 'bill',
        entityId: bill.id,
        billId: bill.id,
        tags: [raw.type || 'PROJECT', 'proyecto-nuevo'],
        isAutoGenerated: true,
        sourceRefId: seedSourceRef.id,
      },
    });
  }
  console.log('  Created ' + billsRaw.length + ' bills with movements');

  // === VOTES ===
  const votesRaw = JSON.parse(fs.readFileSync(path.join(fixturesDir, 'votes.json'), 'utf-8'));

  for (const raw of votesRaw) {
    let session = await prisma.session.findFirst({ where: { externalId: raw.session_external_id } });
    if (!session) {
      session = await prisma.session.create({
        data: {
          externalId: raw.session_external_id,
          date: new Date(raw.session_date),
          title: raw.session_title || null,
          chamber: 'DIPUTADOS',
          period: raw.period || null,
          sourceRefId: seedSourceRef.id,
        },
      });
    }

    const voteEvent = await prisma.voteEvent.create({
      data: {
        externalId: raw.external_id,
        title: raw.title,
        description: raw.description || null,
        date: new Date(raw.date),
        result: raw.result || null,
        affirmative: raw.affirmative || 0,
        negative: raw.negative || 0,
        abstention: raw.abstention || 0,
        absent: raw.absent || 0,
        sessionId: session.id,
        sourceRefId: seedSourceRef.id,
      },
    });

    if (raw.results) {
      for (const r of raw.results) {
        const legId = legislatorMap.get(r.legislator_external_id);
        if (legId) {
          await prisma.voteResult.create({
            data: { vote: r.vote, legislatorId: legId, voteEventId: voteEvent.id },
          });
        }
      }
    }

    // Feed post for vote
    await prisma.feedPost.create({
      data: {
        type: 'VOTE_RESULT',
        title: 'Votacion: ' + raw.title,
        body: 'Resultado: ' + (raw.result || 'N/A') + '. Afirmativos: ' + raw.affirmative + ', Negativos: ' + raw.negative,
        payload: { title: raw.title, result: raw.result, affirmative: raw.affirmative, negative: raw.negative },
        entityType: 'vote_event',
        entityId: voteEvent.id,
        voteEventId: voteEvent.id,
        tags: ['votacion', raw.result || 'pending'],
        isAutoGenerated: true,
        sourceRefId: seedSourceRef.id,
      },
    });
  }
  console.log('  Created ' + votesRaw.length + ' vote events');

  // === ATTENDANCE ===
  const attendanceRaw = JSON.parse(fs.readFileSync(path.join(fixturesDir, 'attendance.json'), 'utf-8'));

  for (const raw of attendanceRaw) {
    let session = await prisma.session.findFirst({ where: { externalId: raw.session_external_id } });
    if (!session) {
      session = await prisma.session.create({
        data: {
          externalId: raw.session_external_id,
          date: new Date(raw.session_date),
          title: raw.session_title || null,
          chamber: 'DIPUTADOS',
          sourceRefId: seedSourceRef.id,
        },
      });
    }

    if (raw.records) {
      for (const rec of raw.records) {
        const legId = legislatorMap.get(rec.legislator_external_id);
        if (legId) {
          await prisma.attendance.upsert({
            where: { legislatorId_sessionId: { legislatorId: legId, sessionId: session.id } },
            create: { status: rec.status, legislatorId: legId, sessionId: session.id, sourceRefId: seedSourceRef.id },
            update: { status: rec.status },
          });
        }
      }
    }

    // Feed post for attendance
    const present = raw.records?.filter((r: any) => r.status === 'PRESENT').length || 0;
    const total = raw.records?.length || 0;
    await prisma.feedPost.create({
      data: {
        type: 'ATTENDANCE_RECORD',
        title: 'Asistencia: ' + (raw.session_title || raw.session_date),
        body: 'Presentes: ' + present + '/' + total,
        payload: { present, total, date: raw.session_date },
        entityType: 'session',
        entityId: session.id,
        tags: ['asistencia'],
        isAutoGenerated: true,
        sourceRefId: seedSourceRef.id,
      },
    });
  }
  console.log('  Created attendance records');

  // === USERS (for social features) ===
  const user1 = await prisma.user.create({
    data: { email: 'ciudadano1@test.com', displayName: 'Juan Ciudadano', role: 'CITIZEN' },
  });
  const user2 = await prisma.user.create({
    data: { email: 'ciudadana2@test.com', displayName: 'María Ciudadana', role: 'CITIZEN' },
  });
  const mod = await prisma.user.create({
    data: { email: 'moderador@test.com', displayName: 'Moderador', role: 'MODERATOR' },
  });
  console.log('  Created 3 test users');

  // === SAMPLE COMMENTS AND REACTIONS ===
  const feedPosts = await prisma.feedPost.findMany({ take: 3 });
  
  for (const post of feedPosts) {
    await prisma.comment.create({
      data: { body: 'Muy importante que se le de seguimiento a esto.', feedPostId: post.id, userId: user1.id },
    });
    await prisma.comment.create({
      data: { body: 'Habría que ver los antecedentes de proyectos similares.', feedPostId: post.id, userId: user2.id },
    });
    await prisma.reaction.create({
      data: { type: 'INFORMATIVE', feedPostId: post.id, userId: user1.id },
    });
    await prisma.reaction.create({
      data: { type: 'IMPORTANT', feedPostId: post.id, userId: user2.id },
    });
  }
  console.log('  Created sample comments and reactions');

  // === COMPUTE METRICS ===
  console.log('  Computing metrics...');
  const period = new Date().getFullYear().toString();
  
  for (const [extId, legId] of legislatorMap) {
    const legislator = await prisma.legislator.findUnique({ where: { id: legId } });
    if (!legislator) continue;

    const billsAuthored = await prisma.billAuthor.count({ where: { legislatorId: legId, role: 'AUTHOR' } });
    const billsCosigned = await prisma.billAuthor.count({ where: { legislatorId: legId, role: 'COAUTHOR' } });
    const billsWithAdvancement = await prisma.bill.count({
      where: { authors: { some: { legislatorId: legId, role: 'AUTHOR' } }, status: { notIn: ['PRESENTED'] } },
    });
    const sessionsTotal = await prisma.attendance.count({ where: { legislatorId: legId } });
    const sessionsPresent = await prisma.attendance.count({ where: { legislatorId: legId, status: 'PRESENT' } });
    const voteEventsTotal = await prisma.voteResult.count({ where: { legislatorId: legId } });
    const voteEventsParticipated = await prisma.voteResult.count({ where: { legislatorId: legId, vote: { not: 'ABSENT' } } });
    const commissionsCount = await prisma.legislatorCommission.count({ where: { legislatorId: legId } });

    const termStart = legislator.termStart || legislator.createdAt;
    const monthsInOffice = Math.max(1, (new Date().getFullYear() - termStart.getFullYear()) * 12 + (new Date().getMonth() - termStart.getMonth()));

    await prisma.legislatorMetric.create({
      data: {
        legislatorId: legId,
        period,
        billsAuthored,
        billsCosigned,
        billsWithAdvancement,
        advancementRate: billsAuthored > 0 ? Math.round(billsWithAdvancement / billsAuthored * 10000) / 10000 : 0,
        sessionsTotal,
        sessionsPresent,
        attendanceRate: sessionsTotal > 0 ? Math.round(sessionsPresent / sessionsTotal * 10000) / 10000 : 0,
        voteEventsTotal,
        voteEventsParticipated,
        voteParticipationRate: voteEventsTotal > 0 ? Math.round(voteEventsParticipated / voteEventsTotal * 10000) / 10000 : 0,
        commissionsCount,
        monthsInOffice,
        normalizedProductivity: Math.round(billsAuthored / monthsInOffice * 10000) / 10000,
      },
    });
  }
  console.log('  Computed metrics for all legislators');

  console.log('✅ Seeding complete!');
}

main()
  .catch((e) => {
    console.error('Seeding failed:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
