import { Controller, Get, Param, Query, NotFoundException } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiQuery, ApiParam } from '@nestjs/swagger';
import { BillsService } from './bills.service';
import { BillStatus, BillType } from '@prisma/client';

@ApiTags('bills')
@Controller('bills')
export class BillsController {
  constructor(private readonly billsService: BillsService) {}

  @Get()
  @ApiOperation({ summary: 'List bills with filters' })
  @ApiQuery({ name: 'page', required: false, type: Number })
  @ApiQuery({ name: 'limit', required: false, type: Number })
  @ApiQuery({ name: 'status', required: false, enum: BillStatus })
  @ApiQuery({ name: 'type', required: false, enum: BillType })
  @ApiQuery({ name: 'search', required: false })
  @ApiQuery({ name: 'authorId', required: false })
  @ApiQuery({ name: 'period', required: false })
  async findAll(
    @Query('page') page?: number,
    @Query('limit') limit?: number,
    @Query('status') status?: BillStatus,
    @Query('type') type?: BillType,
    @Query('search') search?: string,
    @Query('authorId') authorId?: string,
    @Query('period') period?: string,
  ) {
    return this.billsService.findAll({
      page: page ? Number(page) : undefined,
      limit: limit ? Number(limit) : undefined,
      status,
      type,
      search,
      authorId,
      period,
    });
  }

  @Get(':id')
  @ApiOperation({ summary: 'Get bill details with movements' })
  @ApiParam({ name: 'id', description: 'Bill ID' })
  async findOne(@Param('id') id: string) {
    const bill = await this.billsService.findOne(id);
    if (!bill) throw new NotFoundException('Bill not found');
    return bill;
  }
}
