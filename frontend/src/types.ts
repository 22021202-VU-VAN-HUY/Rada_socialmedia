export type User = {
  id: string;
  email: string;
  is_active: boolean;
  created_at: string | null;
};

export type AuthResult = {
  access_token: string;
  token_type: string;
  expires_at: string;
  user: User;
};

export type ContentItem = {
  id: string;
  source_id: string;
  source_name: string;
  platform: string;
  item_type: "post" | "comment" | "reply";
  external_id: string | null;
  parent_external_id: string | null;
  author: string | null;
  content: string;
  permalink: string | null;
  published_at: string | null;
  collected_at: string | null;
  published_label: string | null;
  group_name: string | null;
  reaction_count: number;
  reported_comment_count: number;
  collected_comment_count: number;
  topic: string | null;
  matched_terms: string[];
  is_reply: boolean;
};

export type ContentPage = {
  items: ContentItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export type Job = {
  id: string;
  run_configuration_id: string;
  source_id: string;
  platform: string;
  status: "queued" | "running" | "completed" | "failed";
  trigger: "manual" | "scheduled";
  started_at: string | null;
  completed_at: string | null;
  posts_collected: number;
  comments_collected: number;
  replies_collected: number;
  records_inserted: number;
  duplicates_skipped: number;
  output_path: string | null;
  error_summary: string | null;
  created_at: string | null;
};

export type Overview = {
  posts: number;
  comments: number;
  active_jobs: number;
  saved_configurations: number;
  connected_platforms: number;
};

export type Source = {
  id: string;
  platform: string;
  external_id: string | null;
  source_kind: string;
  source_name: string;
  handle: string | null;
  source_url: string | null;
  enabled: boolean;
  lookback_hours: number;
};

export type Connection = {
  id: string;
  platform: string;
  status: string;
  auth_method: string;
  last_connected_at: string | null;
  last_checked_at: string | null;
  last_error: string | null;
  profile_directory: string | null;
  profile_name: string | null;
  profile_account_name: string | null;
  connected_account_id: string | null;
  connected_account_name: string | null;
};

export type ConnectionResult = {
  connection: Connection;
  message: string;
};

export type RunConfiguration = {
  id: string;
  connection_id: string;
  source_id: string;
  max_posts: number;
  max_comments_per_post: number;
  lookback_hours: number;
  include_replies: boolean;
  filters: Record<string, unknown>;
  last_run_at: string | null;
  last_status: string;
  last_error: string | null;
  created_at: string | null;
};
