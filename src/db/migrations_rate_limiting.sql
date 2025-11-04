-- Migration: Rate Limiting Table
-- Purpose: Store per-user rate limiting data for distributed rate limiting
-- Run this in Supabase SQL editor or via migration tool

-- Create rate_limits table
CREATE TABLE IF NOT EXISTS public.rate_limits (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    window_start TIMESTAMPTZ NOT NULL,
    request_count INTEGER NOT NULL DEFAULT 0,
    reset_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure one record per user per window
    UNIQUE(user_id, window_start)
);

-- Create indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_rate_limits_user_id ON public.rate_limits(user_id);
CREATE INDEX IF NOT EXISTS idx_rate_limits_window_start ON public.rate_limits(window_start);
CREATE INDEX IF NOT EXISTS idx_rate_limits_user_window ON public.rate_limits(user_id, window_start);

-- Create index for cleanup queries (old records)
CREATE INDEX IF NOT EXISTS idx_rate_limits_reset_at ON public.rate_limits(reset_at);

-- Enable Row Level Security (optional, if using RLS)
-- ALTER TABLE public.rate_limits ENABLE ROW LEVEL SECURITY;

-- Function to clean up old rate limit records (older than 1 hour)
CREATE OR REPLACE FUNCTION cleanup_old_rate_limits()
RETURNS void AS $$
BEGIN
    DELETE FROM public.rate_limits
    WHERE reset_at < NOW() - INTERVAL '1 hour';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get or create rate limit record atomically
CREATE OR REPLACE FUNCTION get_or_create_rate_limit(
    p_user_id UUID,
    p_window_start TIMESTAMPTZ,
    p_reset_at TIMESTAMPTZ
)
RETURNS TABLE (
    request_count INTEGER,
    reset_at TIMESTAMPTZ
) AS $$
DECLARE
    v_count INTEGER;
    v_reset TIMESTAMPTZ;
BEGIN
    -- Try to get existing record
    SELECT rl.request_count, rl.reset_at
    INTO v_count, v_reset
    FROM public.rate_limits rl
    WHERE rl.user_id = p_user_id
      AND rl.window_start = p_window_start
    FOR UPDATE;  -- Lock the row
    
    -- If no record exists, create one
    IF v_count IS NULL THEN
        INSERT INTO public.rate_limits (user_id, window_start, request_count, reset_at)
        VALUES (p_user_id, p_window_start, 0, p_reset_at)
        ON CONFLICT (user_id, window_start) DO UPDATE
        SET updated_at = NOW()
        RETURNING request_count, reset_at INTO v_count, v_reset;
    END IF;
    
    RETURN QUERY SELECT v_count, v_reset;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to increment rate limit counter atomically
CREATE OR REPLACE FUNCTION increment_rate_limit(
    p_user_id UUID,
    p_window_start TIMESTAMPTZ
)
RETURNS INTEGER AS $$
DECLARE
    v_new_count INTEGER;
BEGIN
    UPDATE public.rate_limits
    SET request_count = request_count + 1,
        updated_at = NOW()
    WHERE user_id = p_user_id
      AND window_start = p_window_start
    RETURNING request_count INTO v_new_count;
    
    RETURN COALESCE(v_new_count, 0);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

