import { Module } from '@nestjs/common';
import { ThrottlerModule } from '@nestjs/throttler';
import { PrismaModule } from './modules/prisma/prisma.module';
import { LegislatorsModule } from './modules/legislators/legislators.module';
import { BillsModule } from './modules/bills/bills.module';
import { FeedModule } from './modules/feed/feed.module';
import { CommentsModule } from './modules/comments/comments.module';
import { ReactionsModule } from './modules/reactions/reactions.module';
import { SearchModule } from './modules/search/search.module';

// Workers and BullMQ are optional — only loaded if Redis is available
const optionalImports: any[] = [];

if (process.env.ENABLE_WORKERS === 'true') {
  try {
    const { ScheduleModule } = require('@nestjs/schedule');
    const { BullModule } = require('@nestjs/bullmq');
    const { WorkersModule } = require('./workers/workers.module');
    optionalImports.push(
      ScheduleModule.forRoot(),
      BullModule.forRoot({
        connection: {
          host: process.env.REDIS_HOST || 'localhost',
          port: parseInt(process.env.REDIS_PORT || '6379'),
        },
      }),
      WorkersModule,
    );
  } catch (e) {
    console.warn('⚠️  Workers/Redis not available, starting API-only mode');
  }
}

@Module({
  imports: [
    ThrottlerModule.forRoot([{
      ttl: parseInt(process.env.THROTTLE_TTL || '60') * 1000,
      limit: parseInt(process.env.THROTTLE_LIMIT || '100'),
    }]),
    PrismaModule,
    LegislatorsModule,
    BillsModule,
    FeedModule,
    CommentsModule,
    ReactionsModule,
    SearchModule,
    ...optionalImports,
  ],
})
export class AppModule {}
