import { Controller, Get, Post, Param, Body } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiParam, ApiBody } from '@nestjs/swagger';
import { ReactionsService } from './reactions.service';
import { ReactionType } from '@prisma/client';

@ApiTags('reactions')
@Controller('reactions')
export class ReactionsController {
  constructor(private readonly reactionsService: ReactionsService) {}

  @Get('post/:feedPostId')
  @ApiOperation({ summary: 'Get reaction counts for a feed post' })
  @ApiParam({ name: 'feedPostId' })
  async getByPost(@Param('feedPostId') feedPostId: string) {
    return this.reactionsService.getByPost(feedPostId);
  }

  @Post('toggle')
  @ApiOperation({ summary: 'Toggle a reaction (add or remove)' })
  @ApiBody({ schema: { properties: { feedPostId: { type: 'string' }, userId: { type: 'string' }, type: { type: 'string', enum: ['INFORMATIVE', 'IMPORTANT', 'CONCERNING', 'POSITIVE'] } } } })
  async toggle(@Body() data: { feedPostId: string; userId: string; type: ReactionType }) {
    return this.reactionsService.toggle(data.feedPostId, data.userId, data.type);
  }
}
