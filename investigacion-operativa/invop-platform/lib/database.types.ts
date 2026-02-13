// ═══ Supabase Database Types — INVOP.ai ═══

export type Plan = 'free' | 'starter' | 'pro';
export type SyncStatus = 'pending' | 'syncing' | 'synced' | 'error';
export type ReportType = 'weekly' | 'monthly' | 'stock_alert' | 'custom';
export type NotifChannel = 'email' | 'in_app';
export type Module = 'LP' | 'STOCK' | 'QUEUE' | 'INVEST' | 'FORECAST' | 'RENTABILIDAD' | 'FLUJO_CAJA';

export interface Database {
  public: {
    Tables: {
      users: {
        Row: {
          id: string;
          email: string;
          name: string;
          picture: string | null;
          plan: Plan;
          plan_since: string | null;
          stripe_customer_id: string | null;
          fingerprint: string | null;
          solve_count: number;
          created_at: string;
          updated_at: string;
        };
        Insert: Omit<Database['public']['Tables']['users']['Row'], 'id' | 'created_at' | 'updated_at' | 'solve_count'>;
        Update: Partial<Database['public']['Tables']['users']['Insert']>;
      };
      stores: {
        Row: {
          id: string;
          user_id: string;
          shop_domain: string;
          access_token: string; // encrypted
          scopes: string;
          sync_status: SyncStatus;
          last_sync: string | null;
          products_count: number;
          orders_count: number;
          installed_at: string;
        };
        Insert: Omit<Database['public']['Tables']['stores']['Row'], 'id' | 'installed_at' | 'products_count' | 'orders_count'>;
        Update: Partial<Database['public']['Tables']['stores']['Insert']>;
      };
      products: {
        Row: {
          id: string;
          store_id: string;
          shopify_id: string;
          title: string;
          vendor: string | null;
          product_type: string | null;
          status: string;
          variants: VariantData[];
          tags: string[];
          cost_per_item: number | null;
          price: number | null;
          inventory_quantity: number;
          created_at: string;
          synced_at: string;
        };
        Insert: Omit<Database['public']['Tables']['products']['Row'], 'id' | 'synced_at'>;
        Update: Partial<Database['public']['Tables']['products']['Insert']>;
      };
      orders: {
        Row: {
          id: string;
          store_id: string;
          shopify_id: string;
          order_number: number;
          total_price: number;
          subtotal_price: number;
          total_tax: number;
          total_discounts: number;
          currency: string;
          financial_status: string;
          fulfillment_status: string | null;
          line_items: LineItemData[];
          customer_email: string | null;
          order_date: string;
          created_at: string;
          synced_at: string;
        };
        Insert: Omit<Database['public']['Tables']['orders']['Row'], 'id' | 'synced_at'>;
        Update: Partial<Database['public']['Tables']['orders']['Insert']>;
      };
      inventory: {
        Row: {
          id: string;
          store_id: string;
          product_id: string;
          variant_id: string;
          sku: string | null;
          quantity: number;
          location_id: string | null;
          updated_at: string;
        };
        Insert: Omit<Database['public']['Tables']['inventory']['Row'], 'id' | 'updated_at'>;
        Update: Partial<Database['public']['Tables']['inventory']['Insert']>;
      };
      analyses: {
        Row: {
          id: string;
          user_id: string;
          store_id: string | null;
          module: Module;
          input_data: Record<string, unknown>;
          output_data: Record<string, unknown>;
          ai_insights: string | null;
          source: 'manual' | 'shopify_auto' | 'shopify_manual';
          solve_time_ms: number | null;
          created_at: string;
        };
        Insert: Omit<Database['public']['Tables']['analyses']['Row'], 'id' | 'created_at'>;
        Update: Partial<Database['public']['Tables']['analyses']['Insert']>;
      };
      reports: {
        Row: {
          id: string;
          user_id: string;
          store_id: string;
          name: string;
          type: ReportType;
          modules: Module[];
          schedule_cron: string | null; // null = one-time
          config: Record<string, unknown>;
          last_run: string | null;
          next_run: string | null;
          enabled: boolean;
          created_at: string;
        };
        Insert: Omit<Database['public']['Tables']['reports']['Row'], 'id' | 'created_at'>;
        Update: Partial<Database['public']['Tables']['reports']['Insert']>;
      };
      notifications: {
        Row: {
          id: string;
          user_id: string;
          type: string;
          channel: NotifChannel;
          title: string;
          message: string;
          data: Record<string, unknown> | null;
          sent_at: string;
          read_at: string | null;
        };
        Insert: Omit<Database['public']['Tables']['notifications']['Row'], 'id' | 'sent_at'>;
        Update: Partial<Database['public']['Tables']['notifications']['Insert']>;
      };
    };
  };
}

// ═══ Shopify Data Subtypes ═══

export interface VariantData {
  id: string;
  title: string;
  price: number;
  compare_at_price: number | null;
  sku: string | null;
  inventory_quantity: number;
  cost: number | null;
  weight: number | null;
}

export interface LineItemData {
  product_id: string;
  variant_id: string;
  title: string;
  quantity: number;
  price: number;
  total_discount: number;
  sku: string | null;
}
