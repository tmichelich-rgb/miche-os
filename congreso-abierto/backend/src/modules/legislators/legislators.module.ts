import { Module } from '@nestjs/common';
import { LegislatorsController } from './legislators.controller';
import { LegislatorsService } from './legislators.service';

@Module({
  controllers: [LegislatorsController],
  providers: [LegislatorsService],
  exports: [LegislatorsService],
})
export class LegislatorsModule {}
