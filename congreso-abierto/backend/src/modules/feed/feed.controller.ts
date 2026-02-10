import { Controller, Get, Param, Query, NotFoundException } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiQuery, ApiParam } from '@nestjs/swagger';
import { FeedService } from './feed.service';
import { FeedPostType } from '@prisma/client';

@ApiTags('feed')
@Controller('feed')
export class FeedController {
  constructor(private readonly feedService: FeedService) {}

  @Get()
  @ApiOperation({ summary: 'Get feed posts with filters' })
  @ApiQuery({ name: 'page', required: false, type: Number })
  @ApiQuery({ name: 'limit', required: false, type: Number })
  @ApiQuery({ name: 'type', required: false, enum: FeedPostType })
  @ApiQuery({ name: 'blockId', required: false })
  @ApiQuery({ name: 'provinceId', required: false })
  @ApiQuery({ name: 'tags', required: false, type: String, description: 'Comma-separated tags' })
  async getFeed(
    @Query('page') page?: number,
    @Query('limit') limit?: number,
    @Query('type') type?: FeedPostType,
    @Query('blockId') blockId?: string,
    @Query('provinceId') provinceId?: string,
    @Query('tags') tags?: string,
  ) {
    return this.feedService.getFeed({
      page: page ? Number(page) : undefined,
      limit: limit ? Number(limit) : undefined,
      type,
      blockId,
      provinceId,
      tags: tags ? tags.split(',') : undefined,
    });
  }

  @Get(':id')
  @ApiOperation({ summary: 'Get single feed post with details' })
  @ApiParam({ name: 'id' })
  async findOne(@Param('id') id: string) {
    const post = await this.feedService.findOne(id);
    if (!post) throw new NotFoundException('Feed post not found');
    return post;
  }
}
