-- =============================================================================
-- FacPark - Database Schema (MySQL/XAMPP)
-- Version: 2.0.0
-- 
-- IMPORTANT: 
-- - Uses is_active (1 or NULL) + UNIQUE for "one active per user" constraint
-- - Triggers enforce business rules (max 3 vehicles, one active sub/slot)
-- - UTF8MB4 for full French character support
-- =============================================================================

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- Drop existing database if needed (comment out in production)
-- DROP DATABASE IF EXISTS facpark;

CREATE DATABASE IF NOT EXISTS facpark
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE facpark;

-- =============================================================================
-- TABLE: users
-- Stores both ADMIN and STUDENT accounts
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role ENUM('ADMIN', 'STUDENT') NOT NULL DEFAULT 'STUDENT',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- TABLE: vehicles
-- Max 3 per student (enforced by trigger)
-- =============================================================================
CREATE TABLE IF NOT EXISTS vehicles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    plate VARCHAR(20) NOT NULL,
    plate_type ENUM('TN', 'RS', 'ETAT') NOT NULL DEFAULT 'TN',
    make VARCHAR(100) NULL,
    model VARCHAR(100) NULL,
    color VARCHAR(50) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uq_vehicles_plate (plate),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- TABLE: subscriptions
-- Only ONE active subscription per user (is_active=1 + UNIQUE)
-- =============================================================================
CREATE TABLE IF NOT EXISTS subscriptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    subscription_type ENUM('MENSUEL', 'SEMESTRIEL', 'ANNUEL') NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_active TINYINT NULL DEFAULT 1,  -- 1=active, NULL=inactive
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Only one active subscription per user (NULL is ignored by UNIQUE)
    UNIQUE KEY uq_user_active_subscription (user_id, is_active),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- TABLE: slots
-- Parking slots with unique codes
-- =============================================================================
CREATE TABLE IF NOT EXISTS slots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(10) NOT NULL,
    zone VARCHAR(50) NOT NULL DEFAULT 'GENERAL',
    is_available BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uq_slots_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- TABLE: slot_assignments
-- Links user to slot. Only ONE active per user (is_active=1 + UNIQUE)
-- =============================================================================
CREATE TABLE IF NOT EXISTS slot_assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    slot_id INT NOT NULL,
    is_active TINYINT NULL DEFAULT 1,  -- 1=active, NULL=inactive
    assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    released_at DATETIME NULL,
    
    -- Only one active slot per user
    UNIQUE KEY uq_user_active_slot (user_id, is_active),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (slot_id) REFERENCES slots(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- TABLE: suspensions
-- Student access suspensions
-- =============================================================================
CREATE TABLE IF NOT EXISTS suspensions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    reason TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    created_by INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- TABLE: access_events
-- Decision Engine logs (every check_plate_access call)
-- =============================================================================
CREATE TABLE IF NOT EXISTS access_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plate VARCHAR(20) NOT NULL,
    decision ENUM('ALLOW', 'DENY') NOT NULL,
    ref_code VARCHAR(10) NOT NULL,
    message TEXT NULL,
    user_id INT NULL,
    checked_by INT NULL,
    ip_address VARCHAR(45) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (checked_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- TABLE: audit_logs
-- Admin action logs (every write operation by admin)
-- =============================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT NOT NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INT NULL,
    details TEXT NULL,
    ip_address VARCHAR(45) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- TABLE: security_events
-- Security incidents (prompt injection, RBAC violations, etc.)
-- SEPARATE FROM audit_logs
-- =============================================================================
CREATE TABLE IF NOT EXISTS security_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    user_id INT NULL,
    description TEXT NOT NULL,
    payload TEXT NULL,
    pattern_matched VARCHAR(255) NULL,
    severity ENUM('LOW', 'MEDIUM', 'HIGH', 'CRITICAL') NOT NULL DEFAULT 'MEDIUM',
    ip_address VARCHAR(45) NULL,
    user_agent VARCHAR(500) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- TRIGGERS
-- =============================================================================

-- Trigger: Limit vehicles to 3 per student
DELIMITER //
CREATE TRIGGER trg_vehicles_max_3
BEFORE INSERT ON vehicles
FOR EACH ROW
BEGIN
    DECLARE vehicle_count INT;
    SELECT COUNT(*) INTO vehicle_count FROM vehicles WHERE user_id = NEW.user_id;
    IF vehicle_count >= 3 THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = 'Maximum 3 véhicules par étudiant atteint.';
    END IF;
END//
DELIMITER ;


-- Trigger: Deactivate old subscription when new one is created with is_active=1
DELIMITER //
CREATE TRIGGER trg_subscriptions_one_active
BEFORE INSERT ON subscriptions
FOR EACH ROW
BEGIN
    IF NEW.is_active = 1 THEN
        UPDATE subscriptions 
        SET is_active = NULL 
        WHERE user_id = NEW.user_id AND is_active = 1;
    END IF;
END//
DELIMITER ;


-- Trigger: Deactivate old slot assignment when new one is created
DELIMITER //
CREATE TRIGGER trg_slot_assignments_one_active
BEFORE INSERT ON slot_assignments
FOR EACH ROW
BEGIN
    DECLARE old_slot_id INT;
    
    IF NEW.is_active = 1 THEN
        -- Find existing active assignment
        SELECT slot_id INTO old_slot_id 
        FROM slot_assignments 
        WHERE user_id = NEW.user_id AND is_active = 1
        LIMIT 1;
        
        -- Deactivate old assignment
        UPDATE slot_assignments 
        SET is_active = NULL, released_at = NOW()
        WHERE user_id = NEW.user_id AND is_active = 1;
        
        -- Mark old slot as available
        IF old_slot_id IS NOT NULL THEN
            UPDATE slots SET is_available = TRUE WHERE id = old_slot_id;
        END IF;
    END IF;
END//
DELIMITER ;


-- Trigger: Mark slot as unavailable when assigned
DELIMITER //
CREATE TRIGGER trg_slot_assignments_mark_unavailable
AFTER INSERT ON slot_assignments
FOR EACH ROW
BEGIN
    IF NEW.is_active = 1 THEN
        UPDATE slots SET is_available = FALSE WHERE id = NEW.slot_id;
    END IF;
END//
DELIMITER ;

-- =============================================================================
-- END OF SCHEMA
-- =============================================================================
