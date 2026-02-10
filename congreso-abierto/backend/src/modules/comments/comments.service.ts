import { Injectable, ForbiddenException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';

@Injectable()
export class CommentsService {
  constructor(private prisma: PrismaService) {}

  async findByPost(feedPostId: string, page = 1, limit = 20) {
    const skip = (page - 1) * limit;
    const [data, total] = await Promise.all([
      this.prisma.comment.findMany({
        where: { feedPostId, parentId: null, isHidden: false },
        skip,
        take: limit,
        include: {
          user: { select: { id: true, displayName: true, avatarUrl: true } },
          replies: {
            where: { isHidden: false },
            include: {
              user: { select: { id: true, displayName: true, avatarUrl: true } },
            },
            orderBy: { createdAt: 'asc' },
            take: 5,
          },
          _count: { select: { replies: true, reports: true } },
        },
        orderBy: { createdAt: 'desc' },
      }),
      this.prisma.comment.count({ where: { feedPostId, parentId: null, isHidden: false } }),
    ]);
    return { data, meta: { total, page, limit, totalPages: Math.ceil(total / limit) } };
  }

  async create(data: { body: string; feedPostId: string; userId: string; parentId?: string }) {
    // Basic content moderation: check for prohibited patterns
    const prohibitedPatterns = [
      /\b(dirección|domicilio|teléfono personal)\b.*\d/i, // potential doxxing
    ];
    for (const pattern of prohibitedPatterns) {
      if (pattern.test(data.body)) {
        throw new ForbiddenException('Comment contains potentially sensitive personal information');
      }
    }

    const comment = await this.prisma.comment.create({
      data,
      include: {
        user: { select: { id: true, displayName: true, avatarUrl: true } },
      },
    });

    // Auto-hide if user has strikes
    const user = await this.prisma.user.findUnique({ where: { id: data.userId } });
    if (user && user.strikes >= 3) {
      await this.prisma.comment.update({
        where: { id: comment.id },
        data: { isHidden: true },
      });
    }

    return comment;
  }

  async delete(id: string, userId: string) {
    const comment = await this.prisma.comment.findUnique({ where: { id } });
    if (!comment || comment.userId !== userId) {
      throw new ForbiddenException('Cannot delete this comment');
    }
    return this.prisma.comment.update({
      where: { id },
      data: { isHidden: true },
    });
  }

  async report(commentId: string, userId: string, reason: string, details?: string) {
    const report = await this.prisma.report.create({
      data: {
        commentId,
        userId,
        reason: reason as any,
        details,
      },
    });

    // Auto-hide if report threshold reached
    const reportCount = await this.prisma.report.count({
      where: { commentId, status: 'PENDING' },
    });
    if (reportCount >= 3) {
      await this.prisma.comment.update({
        where: { id: commentId },
        data: { isHidden: true },
      });
    }

    return report;
  }
}
