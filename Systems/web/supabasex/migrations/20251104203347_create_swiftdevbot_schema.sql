/*
  # SwiftDevBot Database Schema

  ## Overview
  Complete database schema for SwiftDevBot admin dashboard with authentication,
  user management, module tracking, logs, and statistics.

  ## New Tables
  
  ### 1. `profiles`
  - `id` (uuid, FK to auth.users) - User profile ID
  - `email` (text) - User email
  - `full_name` (text) - User's full name
  - `role` (text) - User role: 'user' or 'admin'
  - `avatar_url` (text) - Profile avatar URL
  - `created_at` (timestamptz) - Account creation timestamp
  - `updated_at` (timestamptz) - Last update timestamp

  ### 2. `bot_modules`
  - `id` (uuid, PK) - Module ID
  - `name` (text) - Module name
  - `description` (text) - Module description
  - `status` (text) - Module status: 'active' or 'inactive'
  - `icon` (text) - Lucide icon name
  - `color` (text) - Theme color for UI
  - `config` (jsonb) - Module configuration
  - `created_at` (timestamptz) - Creation timestamp
  - `updated_at` (timestamptz) - Last update timestamp

  ### 3. `bot_logs`
  - `id` (uuid, PK) - Log entry ID
  - `level` (text) - Log level: 'info', 'warning', 'error', 'success'
  - `message` (text) - Log message
  - `module` (text) - Related module name
  - `metadata` (jsonb) - Additional log data
  - `created_at` (timestamptz) - Log timestamp

  ### 4. `bot_statistics`
  - `id` (uuid, PK) - Statistics ID
  - `metric_name` (text) - Metric name
  - `value` (numeric) - Metric value
  - `timestamp` (timestamptz) - Measurement timestamp
  - `metadata` (jsonb) - Additional metric data

  ### 5. `bot_users`
  - `id` (uuid, PK) - Bot user ID
  - `telegram_id` (bigint) - Telegram user ID
  - `username` (text) - Telegram username
  - `full_name` (text) - User's full name
  - `is_blocked` (boolean) - Block status
  - `interaction_count` (int) - Total interactions
  - `last_active` (timestamptz) - Last activity timestamp
  - `created_at` (timestamptz) - Registration timestamp

  ## Security
  - RLS enabled on all tables
  - Policies for authenticated users based on roles
  - Admin-only access for sensitive operations
*/

-- Create profiles table
CREATE TABLE IF NOT EXISTS profiles (
  id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email text UNIQUE NOT NULL,
  full_name text NOT NULL,
  role text NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
  avatar_url text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own profile"
  ON profiles FOR SELECT
  TO authenticated
  USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
  ON profiles FOR UPDATE
  TO authenticated
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- Create bot_modules table
CREATE TABLE IF NOT EXISTS bot_modules (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text UNIQUE NOT NULL,
  description text NOT NULL,
  status text NOT NULL DEFAULT 'inactive' CHECK (status IN ('active', 'inactive')),
  icon text NOT NULL DEFAULT 'Box',
  color text NOT NULL DEFAULT '#3B82F6',
  config jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE bot_modules ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view modules"
  ON bot_modules FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Only admins can modify modules"
  ON bot_modules FOR ALL
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE profiles.id = auth.uid()
      AND profiles.role = 'admin'
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE profiles.id = auth.uid()
      AND profiles.role = 'admin'
    )
  );

-- Create bot_logs table
CREATE TABLE IF NOT EXISTS bot_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  level text NOT NULL CHECK (level IN ('info', 'warning', 'error', 'success')),
  message text NOT NULL,
  module text,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE bot_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view logs"
  ON bot_logs FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Only admins can insert logs"
  ON bot_logs FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE profiles.id = auth.uid()
      AND profiles.role = 'admin'
    )
  );

-- Create bot_statistics table
CREATE TABLE IF NOT EXISTS bot_statistics (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  metric_name text NOT NULL,
  value numeric NOT NULL,
  timestamp timestamptz DEFAULT now(),
  metadata jsonb DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_bot_statistics_metric ON bot_statistics(metric_name, timestamp DESC);

ALTER TABLE bot_statistics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view statistics"
  ON bot_statistics FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Only admins can insert statistics"
  ON bot_statistics FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE profiles.id = auth.uid()
      AND profiles.role = 'admin'
    )
  );

-- Create bot_users table
CREATE TABLE IF NOT EXISTS bot_users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  telegram_id bigint UNIQUE NOT NULL,
  username text,
  full_name text NOT NULL,
  is_blocked boolean DEFAULT false,
  interaction_count int DEFAULT 0,
  last_active timestamptz DEFAULT now(),
  created_at timestamptz DEFAULT now()
);

ALTER TABLE bot_users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view bot users"
  ON bot_users FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Only admins can modify bot users"
  ON bot_users FOR ALL
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE profiles.id = auth.uid()
      AND profiles.role = 'admin'
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE profiles.id = auth.uid()
      AND profiles.role = 'admin'
    )
  );

-- Insert sample data for modules
INSERT INTO bot_modules (name, description, status, icon, color) VALUES
  ('AI Chat', 'Intelligent conversation module with GPT integration', 'active', 'MessageSquare', '#06B6D4'),
  ('Code Review', 'Automated code analysis and suggestions', 'active', 'Code', '#8B5CF6'),
  ('Task Manager', 'Project and task tracking system', 'inactive', 'CheckSquare', '#10B981'),
  ('Analytics', 'Real-time data analytics and reporting', 'active', 'BarChart3', '#F59E0B'),
  ('Notifications', 'Smart notification delivery system', 'active', 'Bell', '#EF4444'),
  ('File Manager', 'Document storage and management', 'inactive', 'Folder', '#6366F1')
ON CONFLICT (name) DO NOTHING;

-- Insert sample logs
INSERT INTO bot_logs (level, message, module) VALUES
  ('success', 'Bot successfully started and connected to Telegram API', 'System'),
  ('info', 'AI Chat module initialized with GPT-4 model', 'AI Chat'),
  ('warning', 'High memory usage detected: 85% of allocated resources', 'System'),
  ('success', 'Code Review completed for repository: swift-project', 'Code Review'),
  ('info', 'Analytics report generated: 1,247 active users', 'Analytics'),
  ('error', 'Failed to send notification: Network timeout', 'Notifications');