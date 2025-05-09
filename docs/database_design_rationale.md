# Database Design Rationale: Multiple Tables vs Single Table

## Current Design (Multiple Tables)
```sql
Patients
- patient_id (PK)
- first_name
- last_name
- date_of_birth
- gender

Admissions
- admission_id (PK)
- patient_id (FK)
- admission_date
- ward
- bed_number
- status

LabTests
- test_id (PK)
- patient_id (FK)
- admission_id (FK)
- test_type
- test_date
- result
- status
```

## Benefits of Multiple Tables

1. **Data Normalization**
   - Eliminates data redundancy (patient info stored once)
   - Reduces update anomalies
   - Ensures data consistency (e.g., patient details updated in one place)

2. **Storage Efficiency**
   - Patient data stored once, regardless of number of admissions/tests
   - Reduces database size
   - Lower memory usage for queries

3. **Data Integrity**
   - Foreign key constraints ensure referential integrity
   - Prevents orphaned records
   - Maintains data relationships

4. **Query Flexibility**
   - Can query each entity independently
   - Efficient joins for specific data needs
   - Better index utilization

5. **Maintenance Benefits**
   - Schema changes affect only relevant tables
   - Easier to add new fields to specific entities
   - Simpler backup and restore of specific data types

## Single Table Alternative
```sql
CombinedTable
- patient_id
- first_name
- last_name
- date_of_birth
- gender
- admission_id
- admission_date
- ward
- bed_number
- admission_status
- test_id
- test_type
- test_date
- test_result
- test_status
```

## Problems with Single Table Approach

1. **Data Redundancy**
   - Patient information repeated for each test
   - Wastes storage space
   - Increases risk of inconsistencies

2. **Update Anomalies**
   - Updating patient details requires multiple row updates
   - Higher risk of partial updates leading to inconsistent data
   - More complex transaction management

3. **Query Performance**
   - Larger table size impacts query performance
   - More complex indexing requirements
   - Inefficient for partial data retrieval

4. **Null Values**
   - Many columns would be null for different record types
   - Wastes space
   - Complicates queries

5. **Business Logic Complexity**
   - Harder to enforce data relationships
   - More complex application code
   - Difficult to maintain data integrity

## Real-world Impact Examples

1. **Patient Update Scenario**
   - Multiple Tables: Update one row in Patients table
   - Single Table: Update many rows wherever patient appears

2. **Storage Example**
   ```
   1000 patients
   avg 3 admissions per patient
   avg 5 tests per admission
   
   Multiple Tables:
   - Patients: 1000 rows
   - Admissions: 3000 rows
   - Tests: 15000 rows
   
   Single Table:
   - 15000 rows with duplicated patient/admission data
   ```

3. **Query Complexity**
   ```sql
   -- Multiple Tables: Clear and efficient
   SELECT p.first_name, p.last_name, COUNT(t.test_id) as test_count
   FROM patients p
   JOIN admissions a ON p.patient_id = a.patient_id
   LEFT JOIN lab_tests t ON a.admission_id = t.admission_id
   WHERE a.status = 'Active'
   GROUP BY p.patient_id;

   -- Single Table: More complex and less efficient
   SELECT first_name, last_name, COUNT(DISTINCT test_id) as test_count
   FROM combined_table
   WHERE admission_status = 'Active'
   GROUP BY patient_id, first_name, last_name;
   ```

## Conclusion

The multiple-table design provides better:
- Data integrity and consistency
- Query performance and flexibility
- Storage efficiency
- Maintenance and extensibility
- Schema evolution capabilities

While a single-table approach might seem simpler initially, it would create significant technical debt and scalability issues as the system grows. Our current multi-table design aligns with database best practices and provides a solid foundation for the hospital data integration system.