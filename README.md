
Perfect! Let me create a simple yet powerful comparator that gives you complete details in both HTML and JSON formats.

## 🚀 Simple MITO.DB Comparator

### 1. **Main Script** (`mito_simple_comparator.py`)

```python
import sqlite3
import pandas as pd
import json
import os
from datetime import datetime

class SimpleMITOComparator:
    def __init__(self, db1_path, db2_path):
        self.db1_path = db1_path
        self.db2_path = db2_path
        self.results = {
            'comparison_date': datetime.now().isoformat(),
            'db1': db1_path,
            'db2': db2_path,
            'tables': {}
        }
    
    def compare_table(self, table_name):
        """Compare a single table and return complete differences"""
        print(f"🔍 Comparing table: {table_name}")
        
        try:
            # Read both tables
            df1 = self._read_table(self.db1_path, table_name)
            df2 = self._read_table(self.db2_path, table_name)
            
            # Store basic info
            table_result = {
                'db1_row_count': len(df1) if df1 is not None else 0,
                'db2_row_count': len(df2) if df2 is not None else 0,
                'status': 'COMPARED'
            }
            
            # Find differences
            differences = self._find_complete_differences(df1, df2, table_name)
            table_result.update(differences)
            
            self.results['tables'][table_name] = table_result
            return table_result
            
        except Exception as e:
            error_result = {
                'status': 'ERROR',
                'error': str(e)
            }
            self.results['tables'][table_name] = error_result
            return error_result
    
    def _read_table(self, db_path, table_name):
        """Read table from database"""
        try:
            conn = sqlite3.connect(db_path)
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
            conn.close()
            return df
        except:
            return None
    
    def _find_complete_differences(self, df1, df2, table_name):
        """Find all differences between two dataframes"""
        result = {}
        
        # Case 1: One or both tables missing
        if df1 is None and df2 is None:
            result['differences'] = {'status': 'BOTH_TABLES_MISSING'}
            return result
        elif df1 is None:
            result['differences'] = {
                'status': 'TABLE_MISSING_IN_DB1',
                'db2_data': df2.to_dict('records')
            }
            return result
        elif df2 is None:
            result['differences'] = {
                'status': 'TABLE_MISSING_IN_DB2', 
                'db1_data': df1.to_dict('records')
            }
            return result
        
        # Case 2: Both tables exist - find complete differences
        # Convert to dictionaries for easy comparison
        records1 = df1.to_dict('records')
        records2 = df2.to_dict('records')
        
        # Find added records (in db2 but not in db1)
        added = [r for r in records2 if r not in records1]
        
        # Find removed records (in db1 but not in db2)
        removed = [r for r in records1 if r not in records2]
        
        # Find common records
        common = [r for r in records1 if r in records2]
        
        result['differences'] = {
            'status': 'COMPLETE_DIFFERENCES',
            'added_records': added,
            'removed_records': removed, 
            'common_records': common,
            'added_count': len(added),
            'removed_count': len(removed),
            'common_count': len(common)
        }
        
        return result
    
    def generate_json_report(self, output_file=None):
        """Generate JSON report with complete data"""
        if not output_file:
            output_file = f"mito_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"📄 JSON report saved: {output_file}")
        return output_file
    
    def generate_html_report(self, output_file=None):
        """Generate simple HTML report"""
        if not output_file:
            output_file = f"mito_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        html_content = self._create_html_content()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"🌐 HTML report saved: {output_file}")
        return output_file
    
    def _create_html_content(self):
        """Create HTML report content"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>MITO.DB Comparison Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .table {{ margin: 20px 0; border: 1px solid #ddd; padding: 15px; }}
                .added {{ background-color: #e8f5e8; border-left: 4px solid #4CAF50; }}
                .removed {{ background-color: #ffe8e8; border-left: 4px solid #f44336; }}
                .common {{ background-color: #e8f4fd; border-left: 4px solid #2196F3; }}
                .record {{ margin: 10px 0; padding: 10px; border: 1px solid #ccc; }}
                .summary {{ background-color: #f5f5f5; padding: 15px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <h1>🔍 MITO.DB Comparison Report</h1>
            <div class="summary">
                <p><strong>Comparison Date:</strong> {self.results['comparison_date']}</p>
                <p><strong>DB1:</strong> {self.results['db1']}</p>
                <p><strong>DB2:</strong> {self.results['db2']}</p>
            </div>
        """
        
        for table_name, table_data in self.results['tables'].items():
            html += f"""
            <div class="table">
                <h2>📊 Table: {table_name}</h2>
                <p><strong>Status:</strong> {table_data['status']}</p>
                <p><strong>Rows in DB1:</strong> {table_data.get('db1_row_count', 0)}</p>
                <p><strong>Rows in DB2:</strong> {table_data.get('db2_row_count', 0)}</p>
            """
            
            if 'differences' in table_data:
                diff = table_data['differences']
                
                if diff['status'] == 'COMPLETE_DIFFERENCES':
                    # Added Records
                    html += f"""
                    <div class="added">
                        <h3>➕ Added Records ({diff['added_count']})</h3>
                    """
                    for record in diff['added_records']:
                        html += f"<div class='record'><pre>{json.dumps(record, indent=2)}</pre></div>"
                    html += "</div>"
                    
                    # Removed Records  
                    html += f"""
                    <div class="removed">
                        <h3>➖ Removed Records ({diff['removed_count']})</h3>
                    """
                    for record in diff['removed_records']:
                        html += f"<div class='record'><pre>{json.dumps(record, indent=2)}</pre></div>"
                    html += "</div>"
                    
                    # Common Records
                    html += f"""
                    <div class="common">
                        <h3>✅ Common Records ({diff['common_count']})</h3>
                        <p><em>Showing first 3 common records:</em></p>
                    """
                    for record in diff['common_records'][:3]:
                        html += f"<div class='record'><pre>{json.dumps(record, indent=2)}</pre></div>"
                    html += "</div>"
                
                elif diff['status'] == 'TABLE_MISSING_IN_DB1':
                    html += f"""
                    <div class="removed">
                        <h3>❌ Table missing in DB1</h3>
                        <p>DB2 data:</p>
                    """
                    for record in diff['db2_data'][:5]:  # Show first 5 records
                        html += f"<div class='record'><pre>{json.dumps(record, indent=2)}</pre></div>"
                    html += "</div>"
                
                elif diff['status'] == 'TABLE_MISSING_IN_DB2':
                    html += f"""
                    <div class="removed">
                        <h3>❌ Table missing in DB2</h3>
                        <p>DB1 data:</p>
                    """
                    for record in diff['db1_data'][:5]:
                        html += f"<div class='record'><pre>{json.dumps(record, indent=2)}</pre></div>"
                    html += "</div>"
            
            html += "</div>"
        
        html += """
        </body>
        </html>
        """
        
        return html

def main():
    """Simple command line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Simple MITO.DB Comparator')
    parser.add_argument('db1', help='First MITO.DB file path')
    parser.add_argument('db2', help='Second MITO.DB file path')
    parser.add_argument('--tables', nargs='+', required=True, help='Tables to compare')
    parser.add_argument('--json', help='Output JSON file name')
    parser.add_argument('--html', help='Output HTML file name')
    
    args = parser.parse_args()
    
    # Initialize comparator
    comparator = SimpleMITOComparator(args.db1, args.db2)
    
    # Compare each table
    for table in args.tables:
        comparator.compare_table(table)
    
    # Generate reports
    if args.json:
        comparator.generate_json_report(args.json)
    else:
        comparator.generate_json_report()
    
    if args.html:
        comparator.generate_html_report(args.html)
    else:
        comparator.generate_html_report()
    
    print("✅ Comparison completed! Check the generated reports.")

if __name__ == "__main__":
    main()
```

### 2. **Usage Examples**

```bash
# Basic usage - compare specific tables
python mito_simple_comparator.py sprint15.mito.db sprint16.mito.db --tables diagram_config components signals

# With custom output files
python mito_simple_comparator.py old.mito.db new.mito.db --tables table1 table2 --json my_report.json --html my_report.html

# Compare multiple tables
python mito_simple_comparator.py v1.mito.db v2.mito.db --tables users settings projects metadata
```

### 3. **Table Discovery Script** (`discover_tables.py`)

```python
import sqlite3
import sys

def list_tables(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print(f"📋 Tables in {db_path}:")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"  {table[0]} ({count} rows)")
    
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python discover_tables.py <mito.db>")
        sys.exit(1)
    list_tables(sys.argv[1])
```

## 🎯 **What You Get:**

### **JSON Report:**
- Complete record-level differences
- Added, removed, and common records
- Easy to parse for automation

### **HTML Report:**
- Visual color-coded differences
- Added records in green
- Removed records in red  
- Common records in blue
- Full record details displayed

### **Sample Output:**
```
🔍 Comparing table: diagram_configurations
🔍 Comparing table: components
📄 JSON report saved: mito_comparison_20231201_143022.json
🌐 HTML report saved: mito_comparison_20231201_143022.html
✅ Comparison completed! Check the generated reports.
```

## 🚀 **Quick Start:**

1. **First, discover tables:**
   ```bash
   python discover_tables.py sprint15.mito.db
   ```

2. **Then compare:**
   ```bash
   python mito_simple_comparator.py sprint15.mito.db sprint16.mito.db --tables diagram_config components
   ```

The tool will show you **every single record** that was added, removed, or stayed the same - no summaries, just complete details!
