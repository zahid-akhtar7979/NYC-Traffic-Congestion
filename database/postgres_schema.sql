-- NYC Congestion Pricing Analytics - Star Schema (PostgreSQL)
-- Dimension Tables

-- Date Dimension
CREATE TABLE Dim_Date (
    date_id INT PRIMARY KEY,
    full_date DATE,
    year INT,
    month INT,
    day INT,
    day_of_week VARCHAR(10)
);

-- Time Dimension
CREATE TABLE Dim_Time (
    time_id INT PRIMARY KEY,
    hour INT,
    minute INT,
    time_period VARCHAR(20)
);

-- Quarter Dimension
CREATE TABLE Dim_Quarter (
    quarter_id VARCHAR(10) PRIMARY KEY,
    year INT,
    quarter_number INT
);

-- Location Dimension
CREATE TABLE Dim_Location (
    location_id INT PRIMARY KEY,
    borough VARCHAR(50),
    street_name VARCHAR(100),
    intersection VARCHAR(100),
    latitude FLOAT,
    longitude FLOAT
);

-- Facility Dimension
CREATE TABLE Dim_Facility (
    facility_id INT PRIMARY KEY,
    facility_name VARCHAR(100),
    direction VARCHAR(50),
    payment_method VARCHAR(50)
);

-- Vehicle Class Dimension
CREATE TABLE Dim_Vehicle_Class (
    vehicle_class_id INT PRIMARY KEY,
    vehicle_class_name VARCHAR(50)
);

-- Vehicle Dimension
CREATE TABLE Dim_Vehicle (
    vehicle_id INT PRIMARY KEY,
    vehicle_body_type VARCHAR(50),
    vehicle_make VARCHAR(50),
    vehicle_year INT,
    registration_state VARCHAR(20)
);

-- Transport Mode Dimension
CREATE TABLE Dim_Transport_Mode (
    transport_mode_id INT PRIMARY KEY,
    transport_mode_name VARCHAR(50)
);

-- Violation Type Dimension
CREATE TABLE Dim_Violation_Type (
    violation_type_id INT PRIMARY KEY,
    violation_code VARCHAR(50),
    violation_description VARCHAR(200)
);

-- Issuer Dimension
CREATE TABLE Dim_Issuer (
    issuer_id INT PRIMARY KEY,
    issuing_agency VARCHAR(100)
);

-- Station Dimension
CREATE TABLE Dim_Station (
    station_id INT PRIMARY KEY,
    station_name VARCHAR(100),
    borough VARCHAR(50),
    line VARCHAR(50)
);

-- Entrance Dimension
CREATE TABLE Dim_Entrance (
    entrance_id INT PRIMARY KEY,
    station_id INT REFERENCES Dim_Station(station_id),
    entrance_type VARCHAR(50),
    entry_allowed BOOLEAN,
    exit_allowed BOOLEAN,
    latitude FLOAT,
    longitude FLOAT
);

-- Fact Tables

-- CRZ Entries Fact
CREATE TABLE Fact_CRZ_Entries (
    crz_entry_id INT PRIMARY KEY,
    date_id INT REFERENCES Dim_Date(date_id),
    time_id INT REFERENCES Dim_Time(time_id),
    location_id INT REFERENCES Dim_Location(location_id),
    vehicle_class_id INT REFERENCES Dim_Vehicle_Class(vehicle_class_id),
    entry_count INT
);

-- Bridge Tunnel Crossings Fact
CREATE TABLE Fact_Bridge_Tunnel_Crossings (
    crossing_fact_id INT PRIMARY KEY,
    date_id INT REFERENCES Dim_Date(date_id),
    time_id INT REFERENCES Dim_Time(time_id),
    facility_id INT REFERENCES Dim_Facility(facility_id),
    vehicle_class_id INT REFERENCES Dim_Vehicle_Class(vehicle_class_id),
    traffic_count INT
);

-- Ridership Fact
CREATE TABLE Fact_Ridership (
    ridership_fact_id INT PRIMARY KEY,
    date_id INT REFERENCES Dim_Date(date_id),
    transport_mode_id INT REFERENCES Dim_Transport_Mode(transport_mode_id),
    ridership_count INT
);

-- Fare Evasion Fact
CREATE TABLE Fact_Fare_Evasion (
    fare_evasion_fact_id INT PRIMARY KEY,
    quarter_id VARCHAR(10) REFERENCES Dim_Quarter(quarter_id),
    fare_evasion_percent FLOAT,
    margin_of_error_percent FLOAT
);

-- Traffic Violations Fact
CREATE TABLE Fact_Traffic_Violation (
    violation_fact_id INT PRIMARY KEY,
    date_id INT REFERENCES Dim_Date(date_id),
    time_id INT REFERENCES Dim_Time(time_id),
    location_id INT REFERENCES Dim_Location(location_id),
    violation_type_id INT REFERENCES Dim_Violation_Type(violation_type_id),
    vehicle_id INT REFERENCES Dim_Vehicle(vehicle_id),
    issuer_id INT REFERENCES Dim_Issuer(issuer_id),
    violation_count INT
);

-- Optional: Indexes for PostgreSQL performance with 12M+ records
CREATE INDEX idx_crz_date ON Fact_CRZ_Entries(date_id);
CREATE INDEX idx_crz_vehicle_class ON Fact_CRZ_Entries(vehicle_class_id);
CREATE INDEX idx_ridership_date ON Fact_Ridership(date_id);
CREATE INDEX idx_violation_date ON Fact_Traffic_Violation(date_id);
