-- Migration script for user authentication and usage tracking
-- Run this in your Supabase SQL editor

-- Add subscription_tier and searches_used_this_month to profiles table
ALTER TABLE public.profiles
ADD COLUMN IF NOT EXISTS subscription_tier text DEFAULT 'free'::text CHECK (subscription_tier IN ('free', 'basic', 'pro', 'enterprise')),
ADD COLUMN IF NOT EXISTS searches_used_this_month integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_search_at timestamp with time zone;

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_profiles_subscription_tier ON public.profiles(subscription_tier);

-- Create search_history table (optional, for analytics)
CREATE TABLE IF NOT EXISTS public.search_history (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  job_id uuid REFERENCES public.jobs(id) ON DELETE SET NULL,
  company_name text NOT NULL,
  job_title text NOT NULL,
  people_found integer DEFAULT 0,
  sources_used text[],
  cost decimal(10, 4) DEFAULT 0,
  search_time_ms integer,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT search_history_pkey PRIMARY KEY (id)
);

-- Create indexes for search_history
CREATE INDEX IF NOT EXISTS idx_search_history_user_id ON public.search_history(user_id);
CREATE INDEX IF NOT EXISTS idx_search_history_job_id ON public.search_history(job_id);
CREATE INDEX IF NOT EXISTS idx_search_history_created_at ON public.search_history(created_at);

-- Ensure people_discoveries table exists with all required columns
-- If the table doesn't exist, create it; otherwise add missing columns
CREATE TABLE IF NOT EXISTS public.people_discoveries (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  job_id uuid REFERENCES public.jobs(id) ON DELETE SET NULL,
  user_id uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  person_type text NOT NULL,
  full_name text NOT NULL,
  title text,
  email text,
  linkedin_url text,
  confidence_score double precision,
  connection_path text,
  mutual_connections jsonb,
  notes text,
  contacted boolean DEFAULT false,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT people_discoveries_pkey PRIMARY KEY (id)
);

-- Add missing columns if they don't exist
ALTER TABLE public.people_discoveries
ADD COLUMN IF NOT EXISTS company text,
ADD COLUMN IF NOT EXISTS department text,
ADD COLUMN IF NOT EXISTS location text,
ADD COLUMN IF NOT EXISTS source text,
ADD COLUMN IF NOT EXISTS relevance_score double precision,
ADD COLUMN IF NOT EXISTS match_reasons text[];

-- Add indexes to existing people_discoveries table if they don't exist
CREATE INDEX IF NOT EXISTS idx_people_discoveries_job_id ON public.people_discoveries(job_id);
CREATE INDEX IF NOT EXISTS idx_people_discoveries_user_id ON public.people_discoveries(user_id);
CREATE INDEX IF NOT EXISTS idx_people_discoveries_person_type ON public.people_discoveries(person_type);
CREATE INDEX IF NOT EXISTS idx_people_discoveries_created_at ON public.people_discoveries(created_at);
CREATE INDEX IF NOT EXISTS idx_people_discoveries_company ON public.people_discoveries(company);
CREATE INDEX IF NOT EXISTS idx_people_discoveries_contacted ON public.people_discoveries(contacted);

-- Function to reset monthly search usage (can be run via cron)
CREATE OR REPLACE FUNCTION reset_monthly_usage()
RETURNS void AS $$
BEGIN
  UPDATE public.profiles
  SET searches_used_this_month = 0
  WHERE searches_used_this_month > 0;
END;
$$ LANGUAGE plpgsql;

-- Function to get user quota info
CREATE OR REPLACE FUNCTION get_user_quota(user_uuid uuid)
RETURNS json AS $$
DECLARE
  user_tier text;
  searches_used integer;
  tier_config json;
BEGIN
  SELECT subscription_tier, searches_used_this_month
  INTO user_tier, searches_used
  FROM public.profiles
  WHERE id = user_uuid;
  
  IF user_tier IS NULL THEN
    RETURN json_build_object('error', 'User not found');
  END IF;
  
  -- Tier configurations
  CASE user_tier
    WHEN 'free' THEN tier_config := json_build_object('searches_per_month', 10, 'rate_limit', 5);
    WHEN 'basic' THEN tier_config := json_build_object('searches_per_month', 50, 'rate_limit', 10);
    WHEN 'pro' THEN tier_config := json_build_object('searches_per_month', 200, 'rate_limit', 20);
    WHEN 'enterprise' THEN tier_config := json_build_object('searches_per_month', -1, 'rate_limit', 50);
    ELSE tier_config := json_build_object('searches_per_month', 10, 'rate_limit', 5);
  END CASE;
  
  RETURN json_build_object(
    'tier', user_tier,
    'searches_per_month', (tier_config->>'searches_per_month')::integer,
    'searches_used', searches_used,
    'searches_remaining', GREATEST(0, (tier_config->>'searches_per_month')::integer - searches_used),
    'rate_limit_per_minute', (tier_config->>'rate_limit')::integer
  );
END;
$$ LANGUAGE plpgsql;
