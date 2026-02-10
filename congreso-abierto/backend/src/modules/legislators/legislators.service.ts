import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';

@Injectable()
export class LegislatorsService {
  constructor(private prisma: PrismaService) {}

  async findAll(params: {
    page?: number;
    limit?: number;
    blockId?: string;
    provinceId?: string;
    search?: string;
    isActive?: boolean;
  }) {
    const { page = 1, limit = 20, blockId, provinceId, search, isActive = true } = params;
    const skip = (page - 1) * limit;

    const where: any = { isActive };
    if (blockId) where.blockId = blockId;
    if (provinceId) where.provinceId = provinceId;
    if (search) {
      where.fullName = { contains: search, mode: 'insensitive' };
    }

    const [data, total] = await Promise.all([
      this.prisma.legislator.findMany({
        where,
        skip,
        take: limit,
        include: {
          province: true,
          block: true,
        },
        orderBy: { lastName: 'asc' },
      }),
      this.prisma.legislator.count({ where }),
    ]);

    return {
      data,
      meta: { total, page, limit, totalPages: Math.ceil(total / limit) },
    };
  }

  async findOne(id: string) {
    const legislator = await this.prisma.legislator.findUnique({
      where: { id },
      include: {
        province: true,
        block: true,
        commissions: {
          include: { commission: true },
        },
        metrics: {
          orderBy: { computedAt: 'desc' },
          take: 1,
        },
        billAuthors: {
          include: {
            bill: {
              select: {
                id: true,
                title: true,
                status: true,
                presentedDate: true,
                externalId: true,
              },
            },
          },
          orderBy: { createdAt: 'desc' },
          take: 20,
        },
        voteResults: {
          include: {
            voteEvent: {
              select: {
                id: true,
                title: true,
                date: true,
                result: true,
              },
            },
          },
          orderBy: { createdAt: 'desc' },
          take: 20,
        },
      },
    });

    return legislator;
  }

  async getMetrics(id: string, period?: string) {
    const where: any = { legislatorId: id };
    if (period) where.period = period;

    return this.prisma.legislatorMetric.findMany({
      where,
      orderBy: { computedAt: 'desc' },
    });
  }

  async getActivity(id: string, page = 1, limit = 20) {
    const skip = (page - 1) * limit;

    const [bills, votes, attendances] = await Promise.all([
      this.prisma.billAuthor.findMany({
        where: { legislatorId: id },
        include: {
          bill: {
            include: { movements: { orderBy: { date: 'desc' }, take: 1 } },
          },
        },
        orderBy: { createdAt: 'desc' },
        skip,
        take: limit,
      }),
      this.prisma.voteResult.findMany({
        where: { legislatorId: id },
        include: { voteEvent: true },
        orderBy: { createdAt: 'desc' },
        skip,
        take: limit,
      }),
      this.prisma.attendance.findMany({
        where: { legislatorId: id },
        include: { session: true },
        orderBy: { createdAt: 'desc' },
        skip,
        take: limit,
      }),
    ]);

    return { bills, votes, attendances };
  }
}
