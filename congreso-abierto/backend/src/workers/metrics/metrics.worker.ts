import { Processor, WorkerHost } from '@nestjs/bullmq';
import { Logger } from '@nestjs/common';
import { Job } from 'bullmq';
import { PrismaService } from '../../modules/prisma/prisma.service';

@Processor('metrics')
export class MetricsWorker extends WorkerHost {
  private readonly logger = new Logger(MetricsWorker.name);
  constructor(private prisma: PrismaService) { super(); }

  async process(job: Job) {
    if (job.name === 'recompute-all') return this.recomputeAll();
    if (job.name === 'recompute-legislator') return this.computeMetrics(job.data.legislatorId);
  }

  private async recomputeAll() {
    this.logger.log('Recomputing all legislator metrics');
    const legislators = await this.prisma.legislator.findMany({ where: { isActive: true }, select: { id: true } });
    for (const { id } of legislators) await this.computeMetrics(id);
    this.logger.log('Recomputed metrics for ' + legislators.length + ' legislators');
    return { computed: legislators.length };
  }

  private async computeMetrics(legislatorId: string) {
    const period = new Date().getFullYear().toString();
    const legislator = await this.prisma.legislator.findUnique({ where: { id: legislatorId } });
    if (!legislator) return;

    const billsAuthored = await this.prisma.billAuthor.count({ where: { legislatorId, role: 'AUTHOR' } });
    const billsCosigned = await this.prisma.billAuthor.count({ where: { legislatorId, role: 'COAUTHOR' } });
    const billsWithAdvancement = await this.prisma.bill.count({
      where: { authors: { some: { legislatorId, role: 'AUTHOR' } }, movements: { some: {} }, status: { notIn: ['PRESENTED'] } },
    });
    const advancementRate = billsAuthored > 0 ? billsWithAdvancement / billsAuthored : 0;
    const sessionsTotal = await this.prisma.attendance.count({ where: { legislatorId } });
    const sessionsPresent = await this.prisma.attendance.count({ where: { legislatorId, status: 'PRESENT' } });
    const attendanceRate = sessionsTotal > 0 ? sessionsPresent / sessionsTotal : 0;
    const voteEventsTotal = await this.prisma.voteResult.count({ where: { legislatorId } });
    const voteEventsParticipated = await this.prisma.voteResult.count({ where: { legislatorId, vote: { not: 'ABSENT' } } });
    const voteParticipationRate = voteEventsTotal > 0 ? voteEventsParticipated / voteEventsTotal : 0;
    const commissionsCount = await this.prisma.legislatorCommission.count({ where: { legislatorId } });
    const termStart = legislator.termStart || legislator.createdAt;
    const now = new Date();
    const monthsInOffice = Math.max(1, (now.getFullYear() - termStart.getFullYear()) * 12 + (now.getMonth() - termStart.getMonth()));
    const normalizedProductivity = billsAuthored / monthsInOffice;

    const r = (n: number) => Math.round(n * 10000) / 10000;
    await this.prisma.legislatorMetric.upsert({
      where: { legislatorId_period: { legislatorId, period } },
      create: { legislatorId, period, billsAuthored, billsCosigned, billsWithAdvancement, advancementRate: r(advancementRate), sessionsTotal, sessionsPresent, attendanceRate: r(attendanceRate), voteEventsTotal, voteEventsParticipated, voteParticipationRate: r(voteParticipationRate), commissionsCount, monthsInOffice, normalizedProductivity: r(normalizedProductivity) },
      update: { billsAuthored, billsCosigned, billsWithAdvancement, advancementRate: r(advancementRate), sessionsTotal, sessionsPresent, attendanceRate: r(attendanceRate), voteEventsTotal, voteEventsParticipated, voteParticipationRate: r(voteParticipationRate), commissionsCount, monthsInOffice, normalizedProductivity: r(normalizedProductivity) },
    });
  }
}
