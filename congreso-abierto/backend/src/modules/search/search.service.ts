import { Injectable, OnModuleInit, Logger } from '@nestjs/common';
import { MeiliSearch } from 'meilisearch';
import { PrismaService } from '../prisma/prisma.service';

@Injectable()
export class SearchService implements OnModuleInit {
  private client: MeiliSearch;
  private readonly logger = new Logger(SearchService.name);

  constructor(private prisma: PrismaService) {
    this.client = new MeiliSearch({
      host: process.env.MEILI_HOST || 'http://localhost:7700',
      apiKey: process.env.MEILI_MASTER_KEY || 'congreso_search_dev_key',
    });
  }

  async onModuleInit() {
    try {
      await this.client.createIndex('legislators', { primaryKey: 'id' });
      await this.client.index('legislators').updateFilterableAttributes(['blockId', 'provinceId', 'isActive']);
      await this.client.index('legislators').updateSearchableAttributes(['fullName', 'firstName', 'lastName']);

      await this.client.createIndex('bills', { primaryKey: 'id' });
      await this.client.index('bills').updateFilterableAttributes(['status', 'type', 'period']);
      await this.client.index('bills').updateSearchableAttributes(['title', 'summary', 'externalId']);

      this.logger.log('Meilisearch indexes initialized');
    } catch (error) {
      this.logger.warn('Meilisearch initialization failed (will retry on search):', error.message);
    }
  }

  async indexLegislator(legislator: any) {
    try {
      await this.client.index('legislators').addDocuments([{
        id: legislator.id,
        fullName: legislator.fullName,
        firstName: legislator.firstName,
        lastName: legislator.lastName,
        blockId: legislator.blockId,
        provinceId: legislator.provinceId,
        isActive: legislator.isActive,
        photoUrl: legislator.photoUrl,
      }]);
    } catch (error) {
      this.logger.error(`Failed to index legislator ${legislator.id}:`, error.message);
    }
  }

  async indexBill(bill: any) {
    try {
      await this.client.index('bills').addDocuments([{
        id: bill.id,
        title: bill.title,
        summary: bill.summary,
        externalId: bill.externalId,
        status: bill.status,
        type: bill.type,
        period: bill.period,
      }]);
    } catch (error) {
      this.logger.error(`Failed to index bill ${bill.id}:`, error.message);
    }
  }

  async search(query: string, options?: { index?: string; filters?: string; limit?: number }) {
    const { index, filters, limit = 20 } = options || {};
    const searchParams: any = { limit };
    if (filters) searchParams.filter = filters;

    if (index) {
      const results = await this.client.index(index).search(query, searchParams);
      return { [index]: results };
    }

    const [legislators, bills] = await Promise.all([
      this.client.index('legislators').search(query, searchParams),
      this.client.index('bills').search(query, searchParams),
    ]);

    return { legislators, bills };
  }

  async reindexAll() {
    const legislators = await this.prisma.legislator.findMany({
      select: { id: true, fullName: true, firstName: true, lastName: true, blockId: true, provinceId: true, isActive: true, photoUrl: true },
    });
    const bills = await this.prisma.bill.findMany({
      select: { id: true, title: true, summary: true, externalId: true, status: true, type: true, period: true },
    });

    await this.client.index('legislators').addDocuments(legislators);
    await this.client.index('bills').addDocuments(bills);

    this.logger.log(`Reindexed ${legislators.length} legislators and ${bills.length} bills`);
    return { legislators: legislators.length, bills: bills.length };
  }
}
