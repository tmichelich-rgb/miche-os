import * as fs from 'fs';
import * as path from 'path';

describe('Fixture Parsers', () => {
  const fixturesDir = path.join(__dirname, '../fixtures');

  describe('legislators.json', () => {
    let data: any[];

    beforeAll(() => {
      data = JSON.parse(fs.readFileSync(path.join(fixturesDir, 'legislators.json'), 'utf-8'));
    });

    it('should be a non-empty array', () => {
      expect(Array.isArray(data)).toBe(true);
      expect(data.length).toBeGreaterThan(0);
    });

    it('each legislator should have required fields', () => {
      for (const leg of data) {
        expect(leg.external_id).toBeDefined();
        expect(leg.first_name).toBeDefined();
        expect(leg.last_name).toBeDefined();
        expect(leg.province_code).toBeDefined();
        expect(leg.province_name).toBeDefined();
        expect(leg.block_name).toBeDefined();
      }
    });

    it('external_ids should be unique', () => {
      const ids = data.map(l => l.external_id);
      expect(new Set(ids).size).toBe(ids.length);
    });
  });

  describe('bills.json', () => {
    let data: any[];

    beforeAll(() => {
      data = JSON.parse(fs.readFileSync(path.join(fixturesDir, 'bills.json'), 'utf-8'));
    });

    it('should be a non-empty array', () => {
      expect(Array.isArray(data)).toBe(true);
      expect(data.length).toBeGreaterThan(0);
    });

    it('each bill should have required fields', () => {
      for (const bill of data) {
        expect(bill.external_id).toBeDefined();
        expect(bill.title).toBeDefined();
        expect(bill.authors).toBeDefined();
        expect(Array.isArray(bill.authors)).toBe(true);
        expect(bill.authors.length).toBeGreaterThan(0);
      }
    });

    it('authors should reference existing legislators', () => {
      const legislators = JSON.parse(fs.readFileSync(path.join(fixturesDir, 'legislators.json'), 'utf-8'));
      const legIds = new Set(legislators.map((l: any) => l.external_id));

      for (const bill of data) {
        for (const author of bill.authors) {
          expect(legIds.has(author.external_id)).toBe(true);
        }
      }
    });

    it('movements should be ordered chronologically', () => {
      for (const bill of data) {
        if (bill.movements && bill.movements.length > 1) {
          for (let i = 1; i < bill.movements.length; i++) {
            expect(new Date(bill.movements[i].date).getTime())
              .toBeGreaterThanOrEqual(new Date(bill.movements[i - 1].date).getTime());
          }
        }
      }
    });
  });

  describe('votes.json', () => {
    let data: any[];

    beforeAll(() => {
      data = JSON.parse(fs.readFileSync(path.join(fixturesDir, 'votes.json'), 'utf-8'));
    });

    it('each vote should have valid result values', () => {
      const validResults = ['APPROVED', 'REJECTED', 'TIED', 'NO_QUORUM', 'WITHDRAWN', null];
      for (const vote of data) {
        expect(validResults).toContain(vote.result);
      }
    });

    it('individual results should have valid vote values', () => {
      const validVotes = ['AFFIRMATIVE', 'NEGATIVE', 'ABSTENTION', 'ABSENT'];
      for (const vote of data) {
        if (vote.results) {
          for (const r of vote.results) {
            expect(validVotes).toContain(r.vote);
          }
        }
      }
    });
  });

  describe('attendance.json', () => {
    let data: any[];

    beforeAll(() => {
      data = JSON.parse(fs.readFileSync(path.join(fixturesDir, 'attendance.json'), 'utf-8'));
    });

    it('records should have valid status values', () => {
      const validStatuses = ['PRESENT', 'ABSENT', 'ON_LEAVE', 'UNAVAILABLE'];
      for (const session of data) {
        if (session.records) {
          for (const rec of session.records) {
            expect(validStatuses).toContain(rec.status);
          }
        }
      }
    });
  });
});
