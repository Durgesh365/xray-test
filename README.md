
Perfect! Let's build a focused DB comparator that takes two MITO.DB files and specific tables, then generates a clean comparison report.

## 🚀 MITO.DB Table Comparator

### 1. **Main Comparison Script**

```python
# mito_db_comparator.py
import sqlite3
import pandas as pd
import argparse
import json
from datetime import datetime
import sys

class MITODBComparator:
    def __init__(self, db1_path, db2_path, tables_to_compare):
        self.db1_path = db1_path
        self.db2_path = db2_path
        self.tables_to_compare = tables_to_compare
        self.results = {}
    
    def compare_databases(self):
        """Main comparison method"""
        print(f"🔍 Comparing {len(self.tables_to_compare)} tables...")
        print(f"📁 DB1: {self.db1_path}")
        print(f"📁 DB2: {self.db2_path}")
        print("-" * 50)
        
        for table in self.tables_to_compare:
            print(f"📊 Comparing table: {table}")
            self.results[table] = self._compare_table(table)
        
        return self.results
    
    def _compare_table(self, table_name):
        """Compare a single table between two databases"""
        try:
            # Read tables from both databases
            df1 = self._read_table(self.db1_path, table_name)
            df2 = self._read_table(self.db2_path, table_name)
            
            comparison_result = {
                'table_name': table_name,
                'db1_row_count': len(df1) if df1 is not None else 0,
                'db2_row_count': len(df2) if df2 is not None else 0,
                'schema_changes': self._compare_schema(table_name),
                'data_changes': self._compare_table_data(df1, df2, table_name),
                'status': 'COMPARED'
            }
            
            return comparison_result
            
        except Exception as e:
            return {
                'table_name': table_name,
                'status': 'ERROR',
                'error_message': str(e)
            }
    
    def _read_table(self, db_path, table_name):
        """Read a table from SQLite database"""
        try:
            conn = sqlite3.connect(db_path)
            query = f"SELECT * FROM {table_name}"
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except Exception as e:
            print(f"⚠️  Could not read table {table_name} from {db_path}: {e}")
            return None
    
    def _compare_schema(self, table_name):
        """Compare table schema between two databases"""
        try:
            schema1 = self._get_table_schema(self.db1_path, table_name)
            schema2 = self._get_table_schema(self.db2_path, table_name)
            
            if schema1 != schema2:
                return {
                    'has_changes': True,
                    'db1_schema': schema1,
                    'db2_schema': schema2
                }
            else:
                return {'has_changes': False}
                
        except Exception as e:
            return {'has_changes': False, 'error': str(e)}
    
    def _get_table_schema(self, db_path, table_name):
        """Get table schema information"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get column information
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        # Get primary key information
        cursor.execute(f"PRAGMA index_list({table_name})")
        indexes = cursor.fetchall()
        
        schema = {
            'columns': columns,
            'indexes': indexes
        }
        
        conn.close()
        return schema
    
    def _compare_table_data(self, df1, df2, table_name):
        """Compare actual data between two tables"""
        if df1 is None and df2 is None:
            return {'status': 'BOTH_TABLES_MISSING'}
        elif df1 is None:
            return {'status': 'TABLE_MISSING_IN_DB1', 'db2_rows': len(df2)}
        elif df2 is None:
            return {'status': 'TABLE_MISSING_IN_DB2', 'db1_rows': len(df1)}
        
        # Find common columns
        common_columns = list(set(df1.columns) & set(df2.columns))
        
        if not common_columns:
            return {'status': 'NO_COMMON_COLUMNS'}
        
        # Use common columns for comparison
        df1_common = df1[common_columns] if len(df1) > 0 else pd.DataFrame(columns=common_columns)
        df2_common = df2[common_columns] if len(df2) > 0 else pd.DataFrame(columns=common_columns)
        
        # Find differences
        merged = pd.merge(df1_common, df2_common, how='outer', indicator=True, on=common_columns)
        
        added = merged[merged['_merge'] == 'right_only']
        removed = merged[merged['_merge'] == 'left_only']
        
        # Find modified rows (present in both but different)
        if len(common_columns) > 0:
            both = merged[merged['_merge'] == 'both']
            # For simplicity, we'll consider rows with same values in common columns as unchanged
            # In a more advanced version, you might want to compare all columns
        
        return {
            'status': 'COMPARED',
            'common_columns': common_columns,
            'added_rows': len(added),
            'removed_rows': len(removed),
            'total_changes': len(added) + len(removed),
            'sample_added': added.head(3).to_dict('records') if len(added) > 0 else [],
            'sample_removed': removed.head(3).to_dict('records') if len(removed) > 0 else []
        }
    
    def generate_report(self, output_format='console'):
        """Generate comparison report"""
        if output_format == 'console':
            self._print_console_report()
        elif output_format == 'json':
            self._generate_json_report()
        elif output_format == 'html':
            self._generate_html_report()
    
    def _print_console_report(self):
        """Print results to console"""
        print("\n" + "="*60)
        print("📋 MITO.DB COMPARISON REPORT")
        print("="*60)
        
        total_changes = 0
        tables_with_changes = 0
        
        for table, result in self.results.items():
            print(f"\n📁 Table: {table}")
            print(f"   Status: {result.get('status', 'UNKNOWN')}")
            
            if result['status'] == 'COMPARED':
                data_changes = result.get('data_changes', {})
                schema_changes = result.get('schema_changes', {})
                
                # Row counts
                print(f"   Rows in DB1: {result.get('db1_row_count', 0)}")
                print(f"   Rows in DB2: {result.get('db2_row_count', 0)}")
                
                # Schema changes
                if schema_changes.get('has_changes', False):
                    print("   🚨 SCHEMA CHANGES DETECTED!")
                    tables_with_changes += 1
                
                # Data changes
                changes_count = data_changes.get('total_changes', 0)
                if changes_count > 0:
                    print(f"   📈 Data Changes: {changes_count}")
                    print(f"      ➕ Added rows: {data_changes.get('added_rows', 0)}")
                    print(f"      ➖ Removed rows: {data_changes.get('removed_rows', 0)}")
                    total_changes += changes_count
                    tables_with_changes += 1
                else:
                    print("   ✅ No data changes")
            
            elif result['status'].startswith('ERROR'):
                print(f"   ❌ Error: {result.get('error_message', 'Unknown error')}")
        
        print("\n" + "="*60)
        print(f"📊 SUMMARY:")
        print(f"   Tables compared: {len(self.results)}")
        print(f"   Tables with changes: {tables_with_changes}")
        print(f"   Total row changes: {total_changes}")
        print("="*60)

def main():
    parser = argparse.ArgumentParser(description='Compare two MITO.DB files')
    parser.add_argument('db1', help='Path to first MITO.DB file')
    parser.add_argument('db2', help='Path to second MITO.DB file')
    parser.add_argument('--tables', nargs='+', required=True, help='Tables to compare')
    parser.add_argument('--output', choices=['console', 'json', 'html'], default='console', help='Output format')
    
    args = parser.parse_args()
    
    # Initialize comparator
    comparator = MITODBComparator(args.db1, args.db2, args.tables)
    
    # Perform comparison
    results = comparator.compare_databases()
    
    # Generate report
    comparator.generate_report(args.output)

if __name__ == "__main__":
    main()
```

### 2. **Usage Examples**

**Basic Usage:**
```bash
# Compare specific tables between two sprints
python mito_db_comparator.py sprint15.mito.db sprint16.mito.db --tables diagram_configurations component_definitions signal_connections

# Compare with JSON output
python mito_db_comparator.py sprint15.mito.db sprint16.mito.db --tables diagram_configurations cbr_rules --output json
```

**Advanced Usage:**
```bash
# Compare all critical tables
python mito_db_comparator.py old.mito.db new.mito.db --tables diagram_configurations component_definitions signal_connections project_metadata cbr_rules_applied
```

### 3. **Quick Discovery Script** (to find available tables)

```python
# discover_tables.py
import sqlite3
import sys

def list_tables(db_path):
    """List all tables in the MITO.DB"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print(f"📋 Tables in {db_path}:")
        for table in tables:
            # Get row count for each table
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            row_count = cursor.fetchone()[0]
            print(f"  - {table[0]} ({row_count} rows)")
        
        conn.close()
        
    except Exception as e:
        print(f"Error reading database: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python discover_tables.py <path_to_mito.db>")
        sys.exit(1)
    
    list_tables(sys.argv[1])
```

### 4. **Sample Output**

```
🔍 Comparing 3 tables...
📁 DB1: sprint15.mito.db
📁 DB2: sprint16.mito.db
--------------------------------------------------
📊 Comparing table: diagram_configurations
📊 Comparing table: component_definitions  
📊 Comparing table: signal_connections

============================================================
📋 MITO.DB COMPARISON REPORT
============================================================

📁 Table: diagram_configurations
   Status: COMPARED
   Rows in DB1: 150
   Rows in DB2: 152
   📈 Data Changes: 2
      ➕ Added rows: 2
      ➖ Removed rows: 0

📁 Table: component_definitions
   Status: COMPARED  
   Rows in DB1: 89
   Rows in DB2: 89
   ✅ No data changes

📁 Table: signal_connections
   Status: COMPARED
   Rows in DB1: 450
   Rows in DB2: 445
   📈 Data Changes: 5
      ➕ Added rows: 0
      ➖ Removed rows: 5

============================================================
📊 SUMMARY:
   Tables compared: 3
   Tables with changes: 2
   Total row changes: 7
============================================================
```

## 🚀 **How to Get Started:**

1. **First, discover your tables:**
   ```bash
   python discover_tables.py sprint15.mito.db
   ```

2. **Then compare specific tables:**
   ```bash
   python mito_db_comparator.py sprint15.mito.db sprint16.mito.db --tables table1 table2 table3
   ```

Would you like me to create a more advanced version that automatically detects primary keys for better comparison, or should we enhance the reporting format?
