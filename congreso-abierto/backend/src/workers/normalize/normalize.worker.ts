import { Processor, WorkerHost } from '@nestjs/bullmq';
import { Logger } from '@nestjs/common';
import { Job } from 'bullmq';
import { PrismaService } from '../../modules/prisma/prisma.service';
import { InjectQueue } from '@nestjs/bullmq';
import { Queue } from 'bullmq';
import { SearchService } from '../../modules/search/search.service';
import * as fs from 'fs';

interface NormalizeJobData { sourceRefId: string; dataType: string; rawLocation: string; }

@Processor('normalize')
export class NormalizeWorker extends WorkerHost {
  private readonly logger = new Logger(NormalizeWorker.name);

  constructor(
    private prisma: PrismaService,
    private searchService: SearchService,
    @InjectQueue('metrics') private metricsQueue: Queue,
    @InjectQueue('feed-generator') private feedQueue: Queue,
  ) { super(); }

  async process(job: Job<NormalizeJobData>) {
    const { sourceRefId, dataType, rawLocation } = job.data;
    this.logger.log('Normalizing: ' + dataType);
    const rawData = JSON.parse(fs.readFileSync(rawLocation, 'utf-8'));

    switch (dataType) {
      case 'legislators': await this.normalizeLegislators(rawData, sourceRefId); break;
      case 'bills': await this.normalizeBills(rawData, sourceRefId); break;
      case 'votes': await this.normalizeVotes(rawData, sourceRefId); break;
      case 'attendance': await this.normalizeAttendance(rawData, sourceRefId); break;
      default: this.logger.warn('Unknown data type: ' + dataType);
    }
    return { status: 'normalized', dataType, records: rawData.length };
  }

  private async normalizeLegislators(data: any[], sourceRefId: string) {
    for (const raw of data) {
      const province = await this.prisma.province.upsert({
        where: { code: raw.province_code },
        create: { name: raw.province_name, code: raw.province_code },
        update: { name: raw.province_name },
      });
      const block = await this.prisma.block.upsert({
        where: { name: raw.block_name },
        create: { name: raw.block_name, shortName: raw.block_short },
        update: { shortName: raw.block_short },
      });
      const legislator = await this.prisma.legislator.upsert({
        where: { externalId: raw.external_id },
        create: {
          externalId: raw.external_id, firstName: raw.first_name, lastName: raw.last_name,
          fullName: raw.last_name + ', ' + raw.first_name, photoUrl: raw.photo_url || null,
          email: raw.email || null, chamber: 'DIPUTADOS',
          termStart: raw.term_start ? new Date(raw.term_start) : null,
          termEnd: raw.term_end ? new Date(raw.term_end) : null,
          isActive: raw.is_active !== false, provinceId: province.id, blockId: block.id,
        },
        update: {
          firstName: raw.first_name, lastName: raw.last_name,
          fullName: raw.last_name + ', ' + raw.first_name, photoUrl: raw.photo_url || null,
          blockId: block.id, isActive: raw.is_active !== false,
        },
      });
      await this.searchService.indexLegislator(legislator);
    }
    this.logger.log('Normalized ' + data.length + ' legislators');
  }

  private async normalizeBills(data: any[], sourceRefId: string) {
    const affected = new Set<string>();
    for (const raw of data) {
      const existing = await this.prisma.bill.findUnique({ where: { externalId: raw.external_id } });
      const bill = await this.prisma.bill.upsert({
        where: { externalId: raw.external_id },
        create: {
          externalId: raw.external_id, title: raw.title, summary: raw.summary || null,
          type: raw.type || 'PROJECT', status: raw.status || 'PRESENTED',
          presentedDate: raw.presented_date ? new Date(raw.presented_date) : null,
          chamber: 'DIPUTADOS', sourceUrl: raw.source_url || null,
          period: raw.period || null, sourceRefId,
        },
        update: { title: raw.title, summary: raw.summary || null, status: raw.status || undefined, sourceRefId },
      });
      if (raw.authors) {
        for (const author of raw.authors) {
          const leg = await this.prisma.legislator.findUnique({ where: { externalId: author.external_id } });
          if (leg) {
            await this.prisma.billAuthor.upsert({
              where: { billId_legislatorId: { billId: bill.id, legislatorId: leg.id } },
              create: { billId: bill.id, legislatorId: leg.id, role: author.role || 'AUTHOR' },
              update: { role: author.role || 'AUTHOR' },
            });
            affected.add(leg.id);
          }
        }
      }
      if (raw.movements) {
        for (let i = 0; i < raw.movements.length; i++) {
          const mov = raw.movements[i];
          await this.prisma.billMovement.create({
            data: { date: new Date(mov.date), description: mov.description, fromStatus: mov.from_status || null, toStatus: mov.to_status || null, orderIndex: i, billId: bill.id, sourceRefId },
          });
        }
      }
      if (!existing) await this.feedQueue.add('generate', { type: 'BILL_CREATED', entityType: 'bill', entityId: bill.id, sourceRefId });
      else if (raw.movements?.length > 0) await this.feedQueue.add('generate', { type: 'BILL_MOVEMENT', entityType: 'bill', entityId: bill.id, sourceRefId });
      await this.searchService.indexBill(bill);
    }
    for (const id of affected) await this.metricsQueue.add('recompute-legislator', { legislatorId: id });
    this.logger.log('Normalized ' + data.length + ' bills');
  }

  private async normalizeVotes(data: any[], sourceRefId: string) {
    const affected = new Set<string>();
    for (const raw of data) {
      let session = await this.prisma.session.findFirst({ where: { externalId: raw.session_external_id } });
      if (!session) {
        session = await this.prisma.session.create({
          data: { externalId: raw.session_external_id, date: new Date(raw.session_date), title: raw.session_title || null, chamber: 'DIPUTADOS', period: raw.period || null, sourceRefId },
        });
      }
      const ve = await this.prisma.voteEvent.upsert({
        where: { externalId: raw.external_id },
        create: {
          externalId: raw.external_id, title: raw.title, description: raw.description || null,
          date: new Date(raw.date), result: raw.result || null,
          affirmative: raw.affirmative || 0, negative: raw.negative || 0,
          abstention: raw.abstention || 0, absent: raw.absent || 0,
          sessionId: session.id, sourceRefId,
        },
        update: { title: raw.title, result: raw.result || null, affirmative: raw.affirmative || 0, negative: raw.negative || 0 },
      });
      if (raw.results) {
        for (const r of raw.results) {
          const leg = await this.prisma.legislator.findUnique({ where: { externalId: r.legislator_external_id } });
          if (leg) {
            await this.prisma.voteResult.upsert({
              where: { legislatorId_voteEventId: { legislatorId: leg.id, voteEventId: ve.id } },
              create: { vote: r.vote, legislatorId: leg.id, voteEventId: ve.id },
              update: { vote: r.vote },
            });
            affected.add(leg.id);
          }
        }
      }
      await this.feedQueue.add('generate', { type: 'VOTE_RESULT', entityType: 'vote_event', entityId: ve.id, sourceRefId });
    }
    for (const id of affected) await this.metricsQueue.add('recompute-legislator', { legislatorId: id });
    this.logger.log('Normalized ' + data.length + ' vote events');
  }

  private async normalizeAttendance(data: any[], sourceRefId: string) {
    for (const raw of data) {
      let session = await this.prisma.session.findFirst({ where: { externalId: raw.session_external_id } });
      if (!session) {
        session = await this.prisma.session.create({
          data: { externalId: raw.session_external_id, date: new Date(raw.session_date), title: raw.session_title || null, chamber: 'DIPUTADOS', sourceRefId },
        });
      }
      if (raw.records) {
        for (const rec of raw.records) {
          const leg = await this.prisma.legislator.findUnique({ where: { externalId: rec.legislator_external_id } });
          if (leg) {
            await this.prisma.attendance.upsert({
              where: { legislatorId_sessionId: { legislatorId: leg.id, sessionId: session.id } },
              create: { status: rec.status, legislatorId: leg.id, sessionId: session.id, sourceRefId },
              update: { status: rec.status },
            });
          }
        }
      }
      await this.feedQueue.add('generate', { type: 'ATTENDANCE_RECORD', entityType: 'session', entityId: session.id, sourceRefId });
    }
    this.logger.log('Normalized ' + data.length + ' attendance records');
  }
}
