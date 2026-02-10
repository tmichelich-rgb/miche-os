import { Processor, WorkerHost } from '@nestjs/bullmq';
import { Logger } from '@nestjs/common';
import { Job } from 'bullmq';
import { PrismaService } from '../../modules/prisma/prisma.service';
import { InjectQueue } from '@nestjs/bullmq';
import { Queue } from 'bullmq';
import * as crypto from 'crypto';
import * as fs from 'fs';
import * as path from 'path';

interface IngestJobData { sourceName: string; dataType: string; timestamp: string; }

@Processor('ingest')
export class IngestWorker extends WorkerHost {
  private readonly logger = new Logger(IngestWorker.name);
  private readonly rawStoragePath: string;

  constructor(private prisma: PrismaService, @InjectQueue('normalize') private normalizeQueue: Queue) {
    super();
    this.rawStoragePath = process.env.RAW_STORAGE_PATH || './storage/raw';
    if (!fs.existsSync(this.rawStoragePath)) fs.mkdirSync(this.rawStoragePath, { recursive: true });
  }

  async process(job: Job<IngestJobData>) {
    const { sourceName, dataType } = job.data;
    this.logger.log('Starting ingestion: ' + sourceName + '/' + dataType);

    const run = await this.prisma.ingestionRun.create({ data: { sourceName, dataType, status: 'RUNNING' } });

    try {
      const rawData = await this.fetchFromSource(sourceName, dataType);
      const rawJson = JSON.stringify(rawData);
      const checksum = crypto.createHash('sha256').update(rawJson).digest('hex');

      const existingRef = await this.prisma.sourceRef.findFirst({
        where: { url: sourceName + '/' + dataType, checksum }, orderBy: { fetchedAt: 'desc' },
      });

      if (existingRef) {
        this.logger.log('Data unchanged, skipping');
        await this.prisma.ingestionRun.update({ where: { id: run.id }, data: { status: 'COMPLETED', completedAt: new Date(), recordsSkipped: 1 } });
        return { status: 'skipped', reason: 'unchanged' };
      }

      const rawFileName = dataType + '_' + Date.now() + '.json';
      const rawFilePath = path.join(this.rawStoragePath, rawFileName);
      fs.writeFileSync(rawFilePath, rawJson);

      const sourceRef = await this.prisma.sourceRef.create({
        data: { url: sourceName + '/' + dataType, fetchedAt: new Date(), checksum, rawLocation: rawFilePath, sourceType: 'fixture', dataType, ingestionRunId: run.id },
      });

      const recordCount = Array.isArray(rawData) ? rawData.length : 1;
      await this.prisma.ingestionRun.update({ where: { id: run.id }, data: { status: 'COMPLETED', completedAt: new Date(), recordsProcessed: recordCount } });

      await this.normalizeQueue.add('normalize', { sourceRefId: sourceRef.id, dataType, rawLocation: rawFilePath }, { attempts: 3, backoff: { type: 'exponential', delay: 30000 } });

      this.logger.log('Ingestion complete: ' + recordCount + ' records');
      return { status: 'completed', records: recordCount, sourceRefId: sourceRef.id };
    } catch (error: any) {
      this.logger.error('Ingestion failed', error.stack);
      await this.prisma.ingestionRun.update({ where: { id: run.id }, data: { status: 'FAILED', completedAt: new Date(), errors: 1, errorDetails: { message: error.message } } });
      throw error;
    }
  }

  private async fetchFromSource(sourceName: string, dataType: string): Promise<any[]> {
    this.logger.log('Fetching from source adapter: ' + sourceName + ' / ' + dataType);
    await new Promise(resolve => setTimeout(resolve, 100));
    const fixturePath = path.join(__dirname, '../../..', 'test/fixtures', dataType + '.json');
    if (fs.existsSync(fixturePath)) return JSON.parse(fs.readFileSync(fixturePath, 'utf-8'));
    this.logger.warn('No fixture data found for ' + dataType);
    return [];
  }
}
