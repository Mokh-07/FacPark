-- =============================================================================
-- FacPark - Seed Data (Demo/Test Data)
-- Run after 01_schema.sql
-- =============================================================================

USE facpark;

-- =============================================================================
-- ADMIN USERS
-- Password: admin123 (hashed with bcrypt)
-- =============================================================================
INSERT INTO users (email, password_hash, full_name, role, is_active) VALUES
('admin@fac.tn', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4/3s5wU8iJ.vHPfO', 'Administrateur Principal', 'ADMIN', TRUE),
('gestionnaire@fac.tn', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4/3s5wU8iJ.vHPfO', 'Gestionnaire Parking', 'ADMIN', TRUE);


-- =============================================================================
-- STUDENT USERS
-- Password: student123 (hashed with bcrypt)
-- =============================================================================
INSERT INTO users (email, password_hash, full_name, role, is_active) VALUES
('ahmed.benali@etudiant.fac.tn', '$2b$12$vI8aWBnW3fID.ZQ4/zo1G.q1lRps.9cGLcZEiGDMVr5yUP1KUOYTa', 'Ahmed Ben Ali', 'STUDENT', TRUE),
('fatma.trabelsi@etudiant.fac.tn', '$2b$12$vI8aWBnW3fID.ZQ4/zo1G.q1lRps.9cGLcZEiGDMVr5yUP1KUOYTa', 'Fatma Trabelsi', 'STUDENT', TRUE),
('mohamed.gharbi@etudiant.fac.tn', '$2b$12$vI8aWBnW3fID.ZQ4/zo1G.q1lRps.9cGLcZEiGDMVr5yUP1KUOYTa', 'Mohamed Gharbi', 'STUDENT', TRUE),
('salma.mansour@etudiant.fac.tn', '$2b$12$vI8aWBnW3fID.ZQ4/zo1G.q1lRps.9cGLcZEiGDMVr5yUP1KUOYTa', 'Salma Mansour', 'STUDENT', TRUE),
('youssef.hamdi@etudiant.fac.tn', '$2b$12$vI8aWBnW3fID.ZQ4/zo1G.q1lRps.9cGLcZEiGDMVr5yUP1KUOYTa', 'Youssef Hamdi', 'STUDENT', TRUE),
('leila.bouazizi@etudiant.fac.tn', '$2b$12$vI8aWBnW3fID.ZQ4/zo1G.q1lRps.9cGLcZEiGDMVr5yUP1KUOYTa', 'Leila Bouazizi', 'STUDENT', TRUE),
('karim.sassi@etudiant.fac.tn', '$2b$12$vI8aWBnW3fID.ZQ4/zo1G.q1lRps.9cGLcZEiGDMVr5yUP1KUOYTa', 'Karim Sassi', 'STUDENT', TRUE),
('nour.jaziri@etudiant.fac.tn', '$2b$12$vI8aWBnW3fID.ZQ4/zo1G.q1lRps.9cGLcZEiGDMVr5yUP1KUOYTa', 'Nour Jaziri', 'STUDENT', TRUE);


-- =============================================================================
-- VEHICLES
-- Tunisian plate formats: 
--   TN: 123 تونس 4567
--   RS: RS 123 456
--   ETAT: similar format for government vehicles
-- =============================================================================
-- Ahmed Ben Ali (3 vehicles - max allowed)
INSERT INTO vehicles (user_id, plate, plate_type, make, model, color) VALUES
(3, '123 تونس 4567', 'TN', 'Peugeot', '208', 'Blanc'),
(3, '234 تونس 5678', 'TN', 'Renault', 'Clio', 'Gris'),
(3, '345 تونس 6789', 'TN', 'Volkswagen', 'Polo', 'Noir');

-- Fatma Trabelsi (2 vehicles)
INSERT INTO vehicles (user_id, plate, plate_type, make, model, color) VALUES
(4, '456 تونس 7890', 'TN', 'Toyota', 'Yaris', 'Rouge'),
(4, '567 تونس 8901', 'TN', 'Hyundai', 'i20', 'Bleu');

-- Mohamed Gharbi (1 vehicle)
INSERT INTO vehicles (user_id, plate, plate_type, make, model, color) VALUES
(5, '678 تونس 9012', 'TN', 'Kia', 'Picanto', 'Argent');

-- Salma Mansour (1 vehicle - dealer plate)
INSERT INTO vehicles (user_id, plate, plate_type, make, model, color) VALUES
(6, 'RS 789 012', 'RS', 'BMW', '320i', 'Noir');

-- Youssef Hamdi (1 vehicle)
INSERT INTO vehicles (user_id, plate, plate_type, make, model, color) VALUES
(7, '890 تونس 0123', 'TN', 'Fiat', '500', 'Orange');

-- Leila Bouazizi (1 vehicle)
INSERT INTO vehicles (user_id, plate, plate_type, make, model, color) VALUES
(8, '901 تونس 1234', 'TN', 'Citroen', 'C3', 'Vert');

-- Karim Sassi (no vehicle yet)

-- Nour Jaziri (1 vehicle - TEST: Nissan Note from demo image)
INSERT INTO vehicles (user_id, plate, plate_type, make, model, color) VALUES
(10, '190 تونس 2765', 'TN', 'Nissan', 'Note', 'Rouge');


-- =============================================================================
-- PARKING SLOTS
-- Zones: A (proche entrée), B (standard), C (fond)
-- =============================================================================
INSERT INTO slots (code, zone, is_available) VALUES
-- Zone A (Premium - near entrance)
('A01', 'A - Premium', FALSE),
('A02', 'A - Premium', FALSE),
('A03', 'A - Premium', FALSE),
('A04', 'A - Premium', TRUE),
('A05', 'A - Premium', TRUE),

-- Zone B (Standard)
('B01', 'B - Standard', FALSE),
('B02', 'B - Standard', FALSE),
('B03', 'B - Standard', TRUE),
('B04', 'B - Standard', TRUE),
('B05', 'B - Standard', TRUE),
('B06', 'B - Standard', TRUE),
('B07', 'B - Standard', TRUE),
('B08', 'B - Standard', TRUE),
('B09', 'B - Standard', TRUE),
('B10', 'B - Standard', TRUE),

-- Zone C (Economy - back)
('C01', 'C - Economique', TRUE),
('C02', 'C - Economique', TRUE),
('C03', 'C - Economique', TRUE),
('C04', 'C - Economique', TRUE),
('C05', 'C - Economique', TRUE);


-- =============================================================================
-- SUBSCRIPTIONS
-- =============================================================================
-- Ahmed: Annual subscription (active)
INSERT INTO subscriptions (user_id, subscription_type, start_date, end_date, is_active) VALUES
(3, 'ANNUEL', '2026-01-01', '2026-12-31', 1);

-- Fatma: Semester subscription (active)
INSERT INTO subscriptions (user_id, subscription_type, start_date, end_date, is_active) VALUES
(4, 'SEMESTRIEL', '2026-01-15', '2026-07-15', 1);

-- Mohamed: Monthly subscription (expired - for testing)
INSERT INTO subscriptions (user_id, subscription_type, start_date, end_date, is_active) VALUES
(5, 'MENSUEL', '2025-12-01', '2025-12-31', 1);

-- Salma: Annual subscription (active)
INSERT INTO subscriptions (user_id, subscription_type, start_date, end_date, is_active) VALUES
(6, 'ANNUEL', '2025-09-01', '2026-08-31', 1);

-- Youssef: Monthly subscription (active)
INSERT INTO subscriptions (user_id, subscription_type, start_date, end_date, is_active) VALUES
(7, 'MENSUEL', '2026-01-05', '2026-02-05', 1);

-- Leila: No active subscription (for testing)
-- Karim: No subscription

-- Nour: Annual subscription (active - for demo)
INSERT INTO subscriptions (user_id, subscription_type, start_date, end_date, is_active) VALUES
(10, 'ANNUEL', '2026-01-01', '2026-12-31', 1);


-- =============================================================================
-- SLOT ASSIGNMENTS
-- =============================================================================
-- Ahmed -> A01
INSERT INTO slot_assignments (user_id, slot_id, is_active) VALUES
(3, 1, 1);

-- Fatma -> A02
INSERT INTO slot_assignments (user_id, slot_id, is_active) VALUES
(4, 2, 1);

-- Mohamed -> A03
INSERT INTO slot_assignments (user_id, slot_id, is_active) VALUES
(5, 3, 1);

-- Salma -> B01
INSERT INTO slot_assignments (user_id, slot_id, is_active) VALUES
(6, 6, 1);

-- Youssef -> B02
INSERT INTO slot_assignments (user_id, slot_id, is_active) VALUES
(7, 7, 1);

-- Leila: No slot (for testing no-slot scenario)
-- Karim: No slot

-- Nour -> C01 (for demo)
INSERT INTO slot_assignments (user_id, slot_id, is_active) VALUES
(10, 15, 1);


-- =============================================================================
-- SUSPENSIONS
-- =============================================================================
-- Leila is suspended (for testing)
INSERT INTO suspensions (user_id, reason, start_date, end_date, created_by) VALUES
(8, 'Prêt de badge à un tiers - Article R6', '2026-01-15', '2026-01-22', 1);


-- =============================================================================
-- SAMPLE ACCESS EVENTS
-- =============================================================================
INSERT INTO access_events (plate, decision, ref_code, message, user_id, checked_by) VALUES
('123 تونس 4567', 'ALLOW', 'REF-00', 'Accès autorisé. Place: A01', 3, 1),
('456 تونس 7890', 'ALLOW', 'REF-00', 'Accès autorisé. Place: A02', 4, 1),
('FAKE12345', 'DENY', 'REF-02', 'Plaque non enregistrée', NULL, 1),
('901 تونس 1234', 'DENY', 'REF-04', 'Étudiant suspendu', 8, 1);


-- =============================================================================
-- SAMPLE AUDIT LOGS
-- =============================================================================
INSERT INTO audit_logs (admin_id, action, entity_type, entity_id, details) VALUES
(1, 'CREATE_STUDENT', 'user', 3, '{"email": "ahmed.benali@etudiant.fac.tn"}'),
(1, 'ADD_VEHICLE', 'vehicle', 1, '{"plate": "123 تونس 4567"}'),
(1, 'CREATE_SUBSCRIPTION', 'subscription', 1, '{"type": "ANNUEL"}'),
(1, 'ASSIGN_SLOT', 'slot_assignment', 1, '{"slot_code": "A01"}'),
(1, 'SUSPEND_ACCESS', 'suspension', 1, '{"student": "leila.bouazizi@etudiant.fac.tn", "days": 7}');


-- =============================================================================
-- END OF SEED DATA
-- =============================================================================

SELECT 'Seed data inserted successfully!' AS Status;
SELECT COUNT(*) AS TotalUsers FROM users;
SELECT COUNT(*) AS TotalVehicles FROM vehicles;
SELECT COUNT(*) AS TotalSlots FROM slots;
SELECT COUNT(*) AS TotalSubscriptions FROM subscriptions;
