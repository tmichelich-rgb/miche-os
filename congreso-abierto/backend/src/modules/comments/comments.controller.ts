import { Controller, Get, Post, Delete, Param, Query, Body, NotFoundException } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiQuery, ApiParam, ApiBody } from '@nestjs/swagger';
import { CommentsService } from './comments.service';

@ApiTags('comments')
@Controller('comments')
export class CommentsController {
  constructor(private readonly commentsService: CommentsService) {}

  @Get('post/:feedPostId')
  @ApiOperation({ summary: 'Get comments for a feed post' })
  @ApiParam({ name: 'feedPostId' })
  @ApiQuery({ name: 'page', required: false, type: Number })
  @ApiQuery({ name: 'limit', required: false, type: Number })
  async findByPost(
    @Param('feedPostId') feedPostId: string,
    @Query('page') page?: number,
    @Query('limit') limit?: number,
  ) {
    return this.commentsService.findByPost(feedPostId, page ? Number(page) : 1, limit ? Number(limit) : 20);
  }

  @Post()
  @ApiOperation({ summary: 'Create a comment' })
  @ApiBody({ schema: { properties: { body: { type: 'string' }, feedPostId: { type: 'string' }, userId: { type: 'string' }, parentId: { type: 'string' } } } })
  async create(@Body() data: { body: string; feedPostId: string; userId: string; parentId?: string }) {
    return this.commentsService.create(data);
  }

  @Delete(':id')
  @ApiOperation({ summary: 'Delete (hide) a comment' })
  @ApiParam({ name: 'id' })
  async delete(@Param('id') id: string, @Body('userId') userId: string) {
    return this.commentsService.delete(id, userId);
  }

  @Post(':id/report')
  @ApiOperation({ summary: 'Report a comment' })
  @ApiParam({ name: 'id' })
  @ApiBody({ schema: { properties: { userId: { type: 'string' }, reason: { type: 'string' }, details: { type: 'string' } } } })
  async report(
    @Param('id') id: string,
    @Body() data: { userId: string; reason: string; details?: string },
  ) {
    return this.commentsService.report(id, data.userId, data.reason, data.details);
  }
}
