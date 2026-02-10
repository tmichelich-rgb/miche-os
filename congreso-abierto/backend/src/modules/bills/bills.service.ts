import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { BillStatus, BillType } from '@prisma/client';

@Injectable()
export class BillsService {
  constructor(private prisma: PrismaService) {}

  async findAll(params: {
    page?: number;
    limit?: number;
    status?: BillStatus;
    type?: BillType;
    search?: string;
    authorId?: string;
    period?: string;
  }) {
    const { page = 1, limit = 20, status, type, search, authorId, period } = params;
    const skip = (page - 1) * limit;

    const where: any = {};
    if (status) where.status = status;
    if (type) where.type = type;
    if (period) where.period = period;
    if (search) {
      where.OR = [
        { title: { contains: search, mode: 'insensitive' } },
        { externalId: { contains: search, mode: 'insensitive' } },
      ];
    }
    if (authorId) {
      where.authors = { some: { legislatorId: authorId } };
    }

    const [data, total] = await Promise.all([
      this.prisma.bill.findMany({
        where,
        skip,
        take: limit,
        include: {
          authors: {
            include: {
              legislator: {
                select: { id: true, fullName: true, photoUrl: true },
              },
            },
          },
          sourceRef: { select: { url: true, fetchedAt: true } },
        },
        orderBy: { presentedDate: 'desc' },
      }),
      this.prisma.bill.count({ where }),
    ]);

    return {
      data,
      meta: { total, page, limit, totalPages: Math.ceil(total / limit) },
    };
  }

  async findOne(id: string) {
    return this.prisma.bill.findUnique({
      where: { id },
      include: {
        authors: {
          include: {
            legislator: {
              select: {
                id: true,
                fullName: true,
                photoUrl: true,
                block: true,
                province: true,
              },
            },
          },
        },
        movements: {
          orderBy: { orderIndex: 'asc' },
          include: {
            sourceRef: { select: { url: true, fetchedAt: true } },
          },
        },
        sourceRef: { select: { url: true, fetchedAt: true } },
      },
    });
  }
}
