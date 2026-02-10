import { Controller, Get, Param, Query, NotFoundException } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiQuery, ApiParam } from '@nestjs/swagger';
import { LegislatorsService } from './legislators.service';

@ApiTags('legislators')
@Controller('legislators')
export class LegislatorsController {
  constructor(private readonly legislatorsService: LegislatorsService) {}

  @Get()
  @ApiOperation({ summary: 'List legislators with filters' })
  @ApiQuery({ name: 'page', required: false, type: Number })
  @ApiQuery({ name: 'limit', required: false, type: Number })
  @ApiQuery({ name: 'blockId', required: false })
  @ApiQuery({ name: 'provinceId', required: false })
  @ApiQuery({ name: 'search', required: false })
  @ApiQuery({ name: 'isActive', required: false, type: Boolean })
  async findAll(
    @Query('page') page?: number,
    @Query('limit') limit?: number,
    @Query('blockId') blockId?: string,
    @Query('provinceId') provinceId?: string,
    @Query('search') search?: string,
    @Query('isActive') isActive?: boolean,
  ) {
    return this.legislatorsService.findAll({
      page: page ? Number(page) : undefined,
      limit: limit ? Number(limit) : undefined,
      blockId,
      provinceId,
      search,
      isActive: isActive !== undefined ? Boolean(isActive) : undefined,
    });
  }

  @Get(':id')
  @ApiOperation({ summary: 'Get legislator profile with KPIs' })
  @ApiParam({ name: 'id', description: 'Legislator ID' })
  async findOne(@Param('id') id: string) {
    const legislator = await this.legislatorsService.findOne(id);
    if (!legislator) throw new NotFoundException('Legislator not found');
    return legislator;
  }

  @Get(':id/metrics')
  @ApiOperation({ summary: 'Get legislator metrics' })
  @ApiParam({ name: 'id' })
  @ApiQuery({ name: 'period', required: false })
  async getMetrics(@Param('id') id: string, @Query('period') period?: string) {
    return this.legislatorsService.getMetrics(id, period);
  }

  @Get(':id/activity')
  @ApiOperation({ summary: 'Get legislator activity timeline' })
  @ApiParam({ name: 'id' })
  @ApiQuery({ name: 'page', required: false, type: Number })
  @ApiQuery({ name: 'limit', required: false, type: Number })
  async getActivity(
    @Param('id') id: string,
    @Query('page') page?: number,
    @Query('limit') limit?: number,
  ) {
    return this.legislatorsService.getActivity(id, page ? Number(page) : 1, limit ? Number(limit) : 20);
  }
}
