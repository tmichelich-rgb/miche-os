import { Controller, Get, Post, Query } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiQuery } from '@nestjs/swagger';
import { SearchService } from './search.service';

@ApiTags('search')
@Controller('search')
export class SearchController {
  constructor(private readonly searchService: SearchService) {}

  @Get()
  @ApiOperation({ summary: 'Search legislators and bills' })
  @ApiQuery({ name: 'q', required: true, description: 'Search query' })
  @ApiQuery({ name: 'index', required: false, description: 'Specific index: legislators or bills' })
  @ApiQuery({ name: 'limit', required: false, type: Number })
  async search(
    @Query('q') query: string,
    @Query('index') index?: string,
    @Query('limit') limit?: number,
  ) {
    return this.searchService.search(query, { index, limit: limit ? Number(limit) : undefined });
  }

  @Post('reindex')
  @ApiOperation({ summary: 'Reindex all data in Meilisearch' })
  async reindex() {
    return this.searchService.reindexAll();
  }
}
