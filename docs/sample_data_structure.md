# Sample Data Structure

## Patient Management System (PMS) Data
Example data structure from PMS CSV files:

```csv
patient_id,first_name,last_name,date_of_birth,gender,admission_id,admission_date,ward,bed_number,status
P12345,John,Doe,1980-05-15,M,ADM789,2023-05-06T08:30:00,Cardiology,C-123,Active
P12346,Jane,Smith,1975-03-22,F,ADM790,2023-05-06T09:15:00,Neurology,N-456,Active
```

## Laboratory Information System (LIS) Data
Example data structure from LIS CSV files:

```csv
test_id,patient_id,admission_id,test_type,test_date,result,status,lab_location
T98765,P12345,ADM789,Blood Count,2023-05-06T10:30:00,Normal,Completed,Main Lab
T98766,P12345,ADM789,Metabolic Panel,2023-05-06T10:35:00,Abnormal,Completed,Main Lab
```

## Data Fields Description

### PMS Fields
- `patient_id`: Unique identifier for each patient
- `first_name`: Patient's first name
- `last_name`: Patient's last name
- `date_of_birth`: Patient's date of birth (YYYY-MM-DD)
- `gender`: Patient's gender (M/F)
- `admission_id`: Unique identifier for each admission
- `admission_date`: Date and time of admission (ISO 8601 format)
- `ward`: Hospital ward name
- `bed_number`: Bed identifier
- `status`: Current admission status (Active/Discharged)

### LIS Fields
- `test_id`: Unique identifier for each test
- `patient_id`: Reference to patient
- `admission_id`: Reference to admission
- `test_type`: Type of laboratory test
- `test_date`: Date and time of test (ISO 8601 format)
- `result`: Test result
- `status`: Test status (Ordered/In Progress/Completed)
- `lab_location`: Location where test was performed

## Update Frequency
- PMS data updates: Every few seconds when patient status changes
- LIS data updates: Every few seconds when new test results are available

## Data Relationships
- One patient can have multiple admissions
- One admission can have multiple tests
- Each test belongs to one admission and one patient