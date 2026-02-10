import { Module } from '@nestjs/common';
import { BullModule } from '@nestjs/bullmq';
import { IngestWorker } from './ingest/ingest.worker';
import { NormalizeWorker } from './normalize/normalize.worker';
import { MetricsWorker } from './metrics/metrics.worker';
import { FeedGeneratorWorker } from './feed-generator/feed-generator.worker';
import { SchedulerService } from './scheduler.service';
import { FeedModule } from '../modules/feed/feed.module';
import { SearchModule } from '../modules/search/search.module';

@Module({
  imports: [
    BullModule.registerQueue(
      { name: 'ingest' },
      { name: 'normalize' },
      { name: 'metrics' },
      { name: 'feed-generator' },
    ),
    FeedModule,
    SearchModule,
  ],
  providers: [IngestWorker, NormalizeWorker, MetricsWorker, FeedGeneratorWorker, SchedulerService],
  exports: [SchedulerService],
})
export class WorkersModule {}
