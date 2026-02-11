-- =============================================================================
-- FacPark - Performance Indexes
-- Run after 01_schema.sql and 02_seed.sql
-- =============================================================================

USE facpark;

-- =============================================================================
-- USERS
-- =============================================================================
-- Email lookups (already UNIQUE, but explicit index)
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_email_role ON users(email, role);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);


-- =============================================================================
-- VEHICLES
-- =============================================================================
-- Plate lookups for decision engine
CREATE INDEX IF NOT EXISTS idx_vehicles_plate_type ON vehicles(plate_type);
CREATE INDEX IF NOT EXISTS idx_vehicles_user_plate ON vehicles(user_id, plate);


-- =============================================================================
-- SUBSCRIPTIONS
-- =============================================================================
-- Active subscription lookups
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_active ON subscriptions(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_subscriptions_end_date ON subscriptions(end_date);
CREATE INDEX IF NOT EXISTS idx_subscriptions_type ON subscriptions(subscription_type);


-- =============================================================================
-- SLOTS
-- =============================================================================
-- Available slot queries
CREATE INDEX IF NOT EXISTS idx_slots_available ON slots(is_available);
CREATE INDEX IF NOT EXISTS idx_slots_zone ON slots(zone);
CREATE INDEX IF NOT EXISTS idx_slots_zone_available ON slots(zone, is_available);


-- =============================================================================
-- SLOT ASSIGNMENTS
-- =============================================================================
-- Active assignment lookups
CREATE INDEX IF NOT EXISTS idx_slot_assignments_user_active ON slot_assignments(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_slot_assignments_slot_active ON slot_assignments(slot_id, is_active);


-- =============================================================================
-- SUSPENSIONS
-- =============================================================================
-- Active suspension checks
CREATE INDEX IF NOT EXISTS idx_suspensions_user_dates ON suspensions(user_id, start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_suspensions_dates ON suspensions(start_date, end_date);


-- =============================================================================
-- ACCESS EVENTS
-- =============================================================================
-- Statistics and history queries
CREATE INDEX IF NOT EXISTS idx_access_events_created ON access_events(created_at);
CREATE INDEX IF NOT EXISTS idx_access_events_decision ON access_events(decision);
CREATE INDEX IF NOT EXISTS idx_access_events_user ON access_events(user_id);
CREATE INDEX IF NOT EXISTS idx_access_events_ref_code ON access_events(ref_code);
CREATE INDEX IF NOT EXISTS idx_access_events_date_decision ON access_events(created_at, decision);


-- =============================================================================
-- AUDIT LOGS
-- =============================================================================
-- Admin audit queries
CREATE INDEX IF NOT EXISTS idx_audit_logs_admin ON audit_logs(admin_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at);


-- =============================================================================
-- SECURITY EVENTS
-- =============================================================================
-- Security monitoring queries
CREATE INDEX IF NOT EXISTS idx_security_events_type ON security_events(event_type);
CREATE INDEX IF NOT EXISTS idx_security_events_user ON security_events(user_id);
CREATE INDEX IF NOT EXISTS idx_security_events_severity ON security_events(severity);
CREATE INDEX IF NOT EXISTS idx_security_events_created ON security_events(created_at);
CREATE INDEX IF NOT EXISTS idx_security_events_type_severity ON security_events(event_type, severity);


-- =============================================================================
-- ANALYZE TABLES FOR OPTIMIZER
-- =============================================================================
ANALYZE TABLE users;
ANALYZE TABLE vehicles;
ANALYZE TABLE subscriptions;
ANALYZE TABLE slots;
ANALYZE TABLE slot_assignments;
ANALYZE TABLE suspensions;
ANALYZE TABLE access_events;
ANALYZE TABLE audit_logs;
ANALYZE TABLE security_events;


-- =============================================================================
-- SHOW INDEX STATUS
-- =============================================================================
SELECT 'Indexes created successfully!' AS Status;

-- Show index counts per table
SELECT 
    TABLE_NAME,
    COUNT(*) AS IndexCount
FROM information_schema.STATISTICS 
WHERE TABLE_SCHEMA = 'facpark'
GROUP BY TABLE_NAME
ORDER BY TABLE_NAME;
