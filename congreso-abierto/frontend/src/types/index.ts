export interface Legislator {
  id: string;
  externalId: string;
  firstName: string;
  lastName: string;
  fullName: string;
  photoUrl: string | null;
  email: string | null;
  chamber: 'DIPUTADOS' | 'SENADO';
  isActive: boolean;
  province: Province;
  block: Block;
  metrics?: LegislatorMetric[];
}

export interface Province {
  id: string;
  name: string;
  code: string;
}

export interface Block {
  id: string;
  name: string;
  shortName: string | null;
}

export interface Bill {
  id: string;
  externalId: string;
  title: string;
  summary: string | null;
  type: string;
  status: string;
  presentedDate: string | null;
  sourceUrl: string | null;
  authors: BillAuthor[];
  movements: BillMovement[];
}

export interface BillAuthor {
  role: 'AUTHOR' | 'COAUTHOR';
  legislator: Pick<Legislator, 'id' | 'fullName' | 'photoUrl'>;
}

export interface BillMovement {
  id: string;
  date: string;
  description: string;
  fromStatus: string | null;
  toStatus: string | null;
  orderIndex: number;
}

export interface FeedPost {
  id: string;
  type: 'BILL_CREATED' | 'BILL_MOVEMENT' | 'VOTE_RESULT' | 'ATTENDANCE_RECORD';
  title: string;
  body: string;
  payload: any;
  createdAt: string;
  sourceRef?: { url: string; fetchedAt: string };
  _count: { comments: number; reactions: number };
}

export interface LegislatorMetric {
  period: string;
  billsAuthored: number;
  billsCosigned: number;
  billsWithAdvancement: number;
  advancementRate: number;
  attendanceRate: number;
  voteParticipationRate: number;
  commissionsCount: number;
  normalizedProductivity: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: { total: number; page: number; limit: number; totalPages: number };
}
