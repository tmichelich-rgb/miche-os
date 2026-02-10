import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { ReactionType } from '@prisma/client';

@Injectable()
export class ReactionsService {
  constructor(private prisma: PrismaService) {}

  async getByPost(feedPostId: string) {
    const counts = await this.prisma.reaction.groupBy({
      by: ['type'],
      where: { feedPostId },
      _count: true,
    });

    const result: Record<string, number> = {};
    for (const c of counts) {
      result[c.type] = c._count;
    }
    return { feedPostId, counts: result, total: Object.values(result).reduce((a, b) => a + b, 0) };
  }

  async toggle(feedPostId: string, userId: string, type: ReactionType) {
    const existing = await this.prisma.reaction.findUnique({
      where: { userId_feedPostId_type: { userId, feedPostId, type } },
    });

    if (existing) {
      await this.prisma.reaction.delete({ where: { id: existing.id } });
      return { action: 'removed', type };
    }

    await this.prisma.reaction.create({ data: { feedPostId, userId, type } });
    return { action: 'added', type };
  }
}
