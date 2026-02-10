import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication } from '@nestjs/common';
import { FastifyAdapter, NestFastifyApplication } from '@nestjs/platform-fastify';
import * as request from 'supertest';
import { AppModule } from '../../src/app.module';

describe('API Integration Tests', () => {
  let app: INestApplication;

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      imports: [AppModule],
    }).compile();

    app = moduleFixture.createNestApplication<NestFastifyApplication>(new FastifyAdapter());
    app.setGlobalPrefix('api/v1');
    await app.init();
    await (app as NestFastifyApplication).getHttpAdapter().getInstance().ready();
  });

  afterAll(async () => {
    await app.close();
  });

  describe('GET /api/v1/legislators', () => {
    it('should return paginated legislators', async () => {
      const res = await request(app.getHttpServer()).get('/api/v1/legislators');
      expect(res.status).toBe(200);
      expect(res.body).toHaveProperty('data');
      expect(res.body).toHaveProperty('meta');
      expect(Array.isArray(res.body.data)).toBe(true);
    });
  });

  describe('GET /api/v1/bills', () => {
    it('should return paginated bills', async () => {
      const res = await request(app.getHttpServer()).get('/api/v1/bills');
      expect(res.status).toBe(200);
      expect(res.body).toHaveProperty('data');
      expect(res.body).toHaveProperty('meta');
    });
  });

  describe('GET /api/v1/feed', () => {
    it('should return feed posts', async () => {
      const res = await request(app.getHttpServer()).get('/api/v1/feed');
      expect(res.status).toBe(200);
      expect(res.body).toHaveProperty('data');
      expect(Array.isArray(res.body.data)).toBe(true);
    });
  });

  describe('GET /api/v1/search', () => {
    it('should search across indexes', async () => {
      const res = await request(app.getHttpServer()).get('/api/v1/search?q=test');
      expect([200, 502]).toContain(res.status); // 502 if meilisearch not running
    });
  });
});
