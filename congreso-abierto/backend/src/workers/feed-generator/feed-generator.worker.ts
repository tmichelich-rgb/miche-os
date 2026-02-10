import { Processor, WorkerHost } from '@nestjs/bullmq';
import { Logger } from '@nestjs/common';
import { Job } from 'bullmq';
import { PrismaService } from '../../modules/prisma/prisma.service';
import { FeedService } from '../../modules/feed/feed.service';
import { FeedPostType } from '@prisma/client';

interface FeedGenJobData { type: FeedPostType; entityType: string; entityId: string; sourceRefId?: string; }

@Processor('feed-generator')
export class FeedGeneratorWorker extends WorkerHost {
  private readonly logger = new Logger(FeedGeneratorWorker.name);
  constructor(private prisma: PrismaService, private feedService: FeedService) { super(); }

  async process(job: Job<FeedGenJobData>) {
    const { type, entityType, entityId, sourceRefId } = job.data;
    this.logger.log('Generating feed post: ' + type + ' for ' + entityType + '/' + entityId);
    switch (type) {
      case 'BILL_CREATED': return this.genBillCreated(entityId, sourceRefId);
      case 'BILL_MOVEMENT': return this.genBillMovement(entityId, sourceRefId);
      case 'VOTE_RESULT': return this.genVoteResult(entityId, sourceRefId);
      case 'ATTENDANCE_RECORD': return this.genAttendance(entityId, sourceRefId);
    }
  }

  private async genBillCreated(billId: string, sourceRefId?: string) {
    const bill = await this.prisma.bill.findUnique({ where: { id: billId }, include: { authors: { include: { legislator: { include: { block: true, province: true } } } } } });
    if (!bill) return;
    const authorNames = bill.authors.filter(a => a.role === 'AUTHOR').map(a => a.legislator.fullName).join(', ');
    const first = bill.authors.find(a => a.role === 'AUTHOR')?.legislator;
    return this.feedService.createAutoPost({
      type: 'BILL_CREATED', title: 'Nuevo proyecto: ' + bill.externalId,
      body: authorNames + (bill.authors.length > 1 ? ' presentaron' : ' presento') + ' "' + bill.title + '"',
      payload: { billId: bill.id, externalId: bill.externalId, title: bill.title, type: bill.type },
      entityType: 'bill', entityId: bill.id, billId: bill.id,
      blockId: first?.blockId, provinceId: first?.provinceId,
      tags: [bill.type, 'proyecto-nuevo'], sourceRefId,
    });
  }

  private async genBillMovement(billId: string, sourceRefId?: string) {
    const bill = await this.prisma.bill.findUnique({ where: { id: billId }, include: { movements: { orderBy: { orderIndex: 'desc' }, take: 1 }, authors: { include: { legislator: true }, where: { role: 'AUTHOR' }, take: 1 } } });
    if (!bill || !bill.movements.length) return;
    const mov = bill.movements[0];
    return this.feedService.createAutoPost({
      type: 'BILL_MOVEMENT', title: 'Movimiento en ' + bill.externalId,
      body: mov.description + '. Estado: ' + bill.status,
      payload: { billId: bill.id, movement: mov.description, newStatus: bill.status },
      entityType: 'bill', entityId: bill.id, billId: bill.id,
      blockId: bill.authors[0]?.legislator?.blockId, tags: ['movimiento', bill.status], sourceRefId,
    });
  }

  private async genVoteResult(voteEventId: string, sourceRefId?: string) {
    const ve = await this.prisma.voteEvent.findUnique({ where: { id: voteEventId }, include: { session: true } });
    if (!ve) return;
    return this.feedService.createAutoPost({
      type: 'VOTE_RESULT', title: 'Votacion: ' + ve.title,
      body: (ve.result ? 'Resultado: ' + ve.result + '. ' : '') + 'Afirmativos: ' + ve.affirmative + ', Negativos: ' + ve.negative + ', Abstenciones: ' + ve.abstention,
      payload: { voteEventId: ve.id, title: ve.title, result: ve.result, affirmative: ve.affirmative, negative: ve.negative, abstention: ve.abstention, absent: ve.absent },
      entityType: 'vote_event', entityId: ve.id, voteEventId: ve.id,
      tags: ['votacion', ve.result || 'pending'], sourceRefId,
    });
  }

  private async genAttendance(sessionId: string, sourceRefId?: string) {
    const session = await this.prisma.session.findUnique({ where: { id: sessionId }, include: { attendances: true } });
    if (!session) return;
    const present = session.attendances.filter(a => a.status === 'PRESENT').length;
    const absent = session.attendances.filter(a => a.status === 'ABSENT').length;
    const total = session.attendances.length;
    return this.feedService.createAutoPost({
      type: 'ATTENDANCE_RECORD', title: 'Asistencia: Sesion del ' + session.date.toISOString().split('T')[0],
      body: 'Presentes: ' + present + '/' + total + ' (' + (total > 0 ? Math.round(present/total*100) : 0) + '%). Ausentes: ' + absent,
      payload: { sessionId: session.id, date: session.date, present, absent, total },
      entityType: 'session', entityId: session.id, tags: ['asistencia'], sourceRefId,
    });
  }
}
