// PorkChop — TypeScript type definitions mirroring the SQLite schema

export interface Bill {
  id: number;
  congress: number;
  bill_type: string;
  bill_number: number;
  title: string | null;
  short_title: string | null;
  status: string | null;
  introduced_date: string | null;
  sponsors: string | null;
  cosponsors_count: number;
  subjects: string | null;
  summary: string | null;
  source: string | null;
  fetched_at: string;
}

export interface BillVersion {
  id: number;
  bill_id: number;
  version_code: string;
  version_name: string | null;
  raw_text: string | null;
  cleaned_text: string | null;
  xml_text: string | null;
  text_url: string | null;
  xml_url: string | null;
  fetched_at: string;
}

export interface Section {
  id: number;
  bill_id: number;
  version_id: number | null;
  section_number: string | null;
  title: string | null;
  text: string;
  parent_id: number | null;
  level: string | null;
  position: number;
}

export interface SpendingItem {
  id: number;
  section_id: number | null;
  bill_id: number;
  amount: string;
  amount_numeric: number | null;
  purpose: string | null;
  recipient: string | null;
  availability: string | null;
  fiscal_years: string | null;
  source_text: string | null;
}

export interface LegalReference {
  id: number;
  section_id: number | null;
  bill_id: number;
  ref_type: string;
  ref_text: string;
  title_code: string | null;
  section_code: string | null;
}

export interface Deadline {
  id: number;
  section_id: number | null;
  bill_id: number;
  date: string | null;
  action: string | null;
  responsible_entity: string | null;
  source_text: string | null;
}

export interface Entity {
  name: string;
  entity_type: string | null;
  role: string | null;
}

export interface Summary {
  id: number;
  bill_id: number;
  section_id: number | null;
  summary_text: string;
  model_used: string | null;
  created_at: string;
}

export interface PorkScore {
  id: number;
  spending_item_id: number;
  bill_id: number;
  score: number;
  reasons: string | null;
  flags: string | null;
  model_used: string | null;
  created_at: string;
  // Joined from spending_items
  amount?: string;
  purpose?: string;
  recipient?: string;
}

export interface Comparison {
  id: number;
  bill_id: number;
  from_version_id: number;
  to_version_id: number;
  additions_count: number;
  removals_count: number;
  changes_json: string | null;
  spending_diff_json: string | null;
  created_at: string;
}

export interface PorkSummary {
  scored_items: number;
  avg_score: number | null;
  max_score: number | null;
  high_pork_count: number;
}

export interface Stats {
  bills_analyzed: number;
  spending_items: number;
  total_spending: number;
  items_scored: number;
}

// API response wrapper
export interface ApiResponse<T> {
  data: T;
  meta: {
    timestamp: string;
    version: string;
  };
}

export interface ApiError {
  error: {
    code: string;
    message: string;
  };
}
