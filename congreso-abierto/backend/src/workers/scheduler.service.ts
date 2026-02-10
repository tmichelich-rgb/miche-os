import { Injectable, Logger } from '@nestjs/common';
import { Cron } from '@nestjs/schedule';
import { InjectQueue } from '@nestjs/bullmq';
import { Queue } from 'bullmq';

@Injectable()
export class SchedulerService {
  private readonly logger = new Logger(SchedulerService.name);

  constructor(
    @InjectQueue('ingest') private ingestQueue: Queue,
    @InjectQueue('metrics') private metricsQueue: Queue,
  ) {}

  @Cron('0 */6 * * *')
  async scheduleIngestion() {
    this.logger.log('Scheduling periodic ingestion jobs');
    const sources = ['legislators', 'bills', 'votes', 'attendance'];
    for (const dataType of sources) {
      await this.ingestQueue.add('ingest-source', {
        sourceName: 'ckan-diputados', dataType, timestamp: new Date().toISOString(),
      }, { attempts: 3, backoff: { type: 'exponential', delay: 60000 }, removeOnComplete: 100, removeOnFail: 50 });
    }
  }

  @Cron('0 3 * * *')
  async scheduleMetricsRecompute() {
    this.logger.log('Scheduling daily metrics recomputation');
    await this.metricsQueue.add('recompute-all', { timestamp: new Date().toISOString() });
  }

  async triggerIngestion(dataType: string) {
    return this.ingestQueue.add('ingest-source', { sourceName: 'ckan-diputados', dataType, timestamp: new Date().toISOString() });
  }
}
