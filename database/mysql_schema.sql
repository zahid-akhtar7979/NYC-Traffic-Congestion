-- NYC Congestion Pricing Analytics - Star Schema (MySQL)
-- Dimension Tables

-- Date Dimension
CREATE TABLE Dim_Date (
    date_id INT PRIMARY KEY,
    full_date DATE,
    year INT,
    month INT,
    day INT,
    day_of_week VARCHAR(10)
) ENGINE=InnoDB;

-- Time Dimension
CREATE TABLE Dim_Time (
    time_id INT PRIMARY KEY,
    hour INT,
    minute INT,
    time_period VARCHAR(20)
) ENGINE=InnoDB;

-- Quarter Dimension
CREATE TABLE Dim_Quarter (
    quarter_id VARCHAR(10) PRIMARY KEY,
    year INT,
    quarter_number INT
) ENGINE=InnoDB;

-- Location Dimension
CREATE TABLE Dim_Location (
    location_id INT PRIMARY KEY,
    borough VARCHAR(50),
    street_name VARCHAR(100),
    intersection VARCHAR(100),
    latitude FLOAT,
    longitude FLOAT
) ENGINE=InnoDB;

-- Facility Dimension
CREATE TABLE Dim_Facility (
    facility_id INT PRIMARY KEY,
    facility_name VARCHAR(100),
    direction VARCHAR(50),
    payment_method VARCHAR(50)
) ENGINE=InnoDB;

-- Vehicle Class Dimension
CREATE TABLE Dim_Vehicle_Class (
    vehicle_class_id INT PRIMARY KEY,
    vehicle_class_name VARCHAR(50)
) ENGINE=InnoDB;

-- Vehicle Dimension
CREATE TABLE Dim_Vehicle (
    vehicle_id INT PRIMARY KEY,
    vehicle_body_type VARCHAR(50),
    vehicle_make VARCHAR(50),
    vehicle_year INT,
    registration_state VARCHAR(20)
) ENGINE=InnoDB;

-- Transport Mode Dimension
CREATE TABLE Dim_Transport_Mode (
    transport_mode_id INT PRIMARY KEY,
    transport_mode_name VARCHAR(50)
) ENGINE=InnoDB;

-- Violation Type Dimension
CREATE TABLE Dim_Violation_Type (
    violation_type_id INT PRIMARY KEY,
    violation_code VARCHAR(50),
    violation_description VARCHAR(200)
) ENGINE=InnoDB;

-- Issuer Dimension
CREATE TABLE Dim_Issuer (
    issuer_id INT PRIMARY KEY,
    issuing_agency VARCHAR(100)
) ENGINE=InnoDB;

-- Station Dimension
CREATE TABLE Dim_Station (
    station_id INT PRIMARY KEY,
    station_name VARCHAR(100),
    borough VARCHAR(50),
    line VARCHAR(50)
) ENGINE=InnoDB;

-- Entrance Dimension
CREATE TABLE Dim_Entrance (
    entrance_id INT PRIMARY KEY,
    station_id INT,
    entrance_type VARCHAR(50),
    entry_allowed TINYINT(1),
    exit_allowed TINYINT(1),
    latitude FLOAT,
    longitude FLOAT,
    FOREIGN KEY (station_id) REFERENCES Dim_Station(station_id)
) ENGINE=InnoDB;

-- Fact Tables

-- CRZ Entries Fact
CREATE TABLE Fact_CRZ_Entries (
    crz_entry_id INT PRIMARY KEY,
    date_id INT,
    time_id INT,
    location_id INT,
    vehicle_class_id INT,
    entry_count INT,
    FOREIGN KEY (date_id) REFERENCES Dim_Date(date_id),
    FOREIGN KEY (time_id) REFERENCES Dim_Time(time_id),
    FOREIGN KEY (location_id) REFERENCES Dim_Location(location_id),
    FOREIGN KEY (vehicle_class_id) REFERENCES Dim_Vehicle_Class(vehicle_class_id)
) ENGINE=InnoDB;

-- Bridge Tunnel Crossings Fact
CREATE TABLE Fact_Bridge_Tunnel_Crossings (
    crossing_fact_id INT PRIMARY KEY,
    date_id INT,
    time_id INT,
    facility_id INT,
    vehicle_class_id INT,
    traffic_count INT,
    FOREIGN KEY (date_id) REFERENCES Dim_Date(date_id),
    FOREIGN KEY (time_id) REFERENCES Dim_Time(time_id),
    FOREIGN KEY (facility_id) REFERENCES Dim_Facility(facility_id),
    FOREIGN KEY (vehicle_class_id) REFERENCES Dim_Vehicle_Class(vehicle_class_id)
) ENGINE=InnoDB;

-- Ridership Fact
CREATE TABLE Fact_Ridership (
    ridership_fact_id INT PRIMARY KEY,
    date_id INT,
    transport_mode_id INT,
    ridership_count INT,
    FOREIGN KEY (date_id) REFERENCES Dim_Date(date_id),
    FOREIGN KEY (transport_mode_id) REFERENCES Dim_Transport_Mode(transport_mode_id)
) ENGINE=InnoDB;

-- Fare Evasion Fact
CREATE TABLE Fact_Fare_Evasion (
    fare_evasion_fact_id INT PRIMARY KEY,
    quarter_id VARCHAR(10),
    fare_evasion_percent FLOAT,
    margin_of_error_percent FLOAT,
    FOREIGN KEY (quarter_id) REFERENCES Dim_Quarter(quarter_id)
) ENGINE=InnoDB;

-- Traffic Violations Fact
CREATE TABLE Fact_Traffic_Violation (
    violation_fact_id INT PRIMARY KEY,
    date_id INT,
    time_id INT,
    location_id INT,
    violation_type_id INT,
    vehicle_id INT,
    issuer_id INT,
    violation_count INT,
    FOREIGN KEY (date_id) REFERENCES Dim_Date(date_id),
    FOREIGN KEY (time_id) REFERENCES Dim_Time(time_id),
    FOREIGN KEY (location_id) REFERENCES Dim_Location(location_id),
    FOREIGN KEY (violation_type_id) REFERENCES Dim_Violation_Type(violation_type_id),
    FOREIGN KEY (vehicle_id) REFERENCES Dim_Vehicle(vehicle_id),
    FOREIGN KEY (issuer_id) REFERENCES Dim_Issuer(issuer_id)
) ENGINE=InnoDB;

-- Optional: Indexes for MySQL performance with 12M+ records
CREATE INDEX idx_crz_date ON Fact_CRZ_Entries(date_id);
CREATE INDEX idx_crz_vehicle_class ON Fact_CRZ_Entries(vehicle_class_id);
CREATE INDEX idx_ridership_date ON Fact_Ridership(date_id);
CREATE INDEX idx_violation_date ON Fact_Traffic_Violation(date_id);
