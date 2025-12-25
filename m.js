1. The Framework Structure
Here is the directory structure. Create these folders and files.
Plaintext
mito-automation/
├── package.json                # Dependencies
├── playwright.config.js        # Global Configuration
├── testdata/
│   └── execution-data.json     # INPUT: Log names, diagram names, etc.
├── lib/                        # Low-level utilities
│   ├── db-manager.js           # Handles SQLite connection
│   └── jar-parser.js           # Handles ZIP opening and XML parsing
├── validators/                 # BUSINESS LOGIC (The "Brains")
│   ├── BaseValidator.js        # Shared logic
│   ├── LogValidator.js         # Logic for Test Case 1 (Logs)
│   └── ConnectionValidator.js  # Logic for Test Case 2 (Connectors)
└── tests/
    └── backend.spec.js         # THE TEST FILE (Clean & Readable)
________________________________________
2. File Implementations
1. package.json
Run npm init -y and install dependencies:
Bash
npm install @playwright/test better-sqlite3 adm-zip cheerio
2. playwright.config.js
Defines the location of your application files (DB and JAR).
JavaScript
// playwright.config.js
const { defineConfig } = require('@playwright/test');
const path = require('path'); // Built-in, no install needed

// Parse CLI args (e.g., --MITO_DB_PATH=/path/to/db)
const parseArg = (flag) => {
  const index = process.argv.indexOf(flag);
  return index !== -1 ? process.argv[index + 1] : undefined;
};

module.exports = defineConfig({
  testDir: './tests',
  globalSetup: require.resolve('./global-setup.js'),
  timeout: 60000,
  use: {
    // Global paths (Change these to your actual Windows paths)
    const dbPath = parseArg('--MITO_DB_PATH') || process.env.MITO_DB_PATH || 'C:/MITO/Projects/Project1/MITO.db';
const jarPath = parseArg('--MITO_JAR_PATH') || process.env.MITO_JAR_PATH || 'C:/MITO/Projects/Project1/Generated.jar';
  },
  reporter: [['html'], ['list']],
});
3. testdata/execution-data.json
Your specific input data for the current run.
JSON
{
  "logVerification": {
    "logName": "Import PCS7 Diagram-24-12-2025, 05:32 PM"
  },
  "connectionVerification": {
    "diagramName": "=7BHA01GH001"
  }
}
4. lib/db-manager.js
A wrapper to make running SQL queries easy.
JavaScript
const Database = require('better-sqlite3');

class DbManager {
  constructor(dbPath) {
    this.db = new Database(dbPath, { readonly: true });
  }

  query(sql, params = []) {
    const stmt = this.db.prepare(sql);
    return stmt.all(params);
  }

  close() {
    this.db.close();
  }
}
module.exports = { DbManager };
5. lib/jar-parser.js
A wrapper to extract XMLs without unzipping manually.
JavaScript
const AdmZip = require('adm-zip');
const cheerio = require('cheerio');

class JarParser {
  constructor(jarPath) {
    this.zip = new AdmZip(jarPath);
  }

  /**
   * Returns a Cheerio object ($) for the ic_diagram.xml of a specific diagram
   */
  getDiagramXml(diagramName) {
  // Try folder structure first
  let entryName = `${diagramName}/ic_diagram.xml`;
  let entry = this.zip.getEntry(entryName);
  if (!entry) {
    // Fallback: root ic_diagram.xml if single-diagram JAR
    entryName = 'ic_diagram.xml';
    entry = this.zip.getEntry(entryName);
  }
  if (!entry) throw new Error(`ic_diagram.xml not found for ${diagramName}`);
  const xmlContent = entry.getData().toString('utf8');
  return cheerio.load(xmlContent, { xmlMode: true });
}
// Add: getAllDiagramNames() to scan ZIP entries
getAllDiagramNames() {
  return this.zip.getEntries()
    .filter(e => e.entryName.endsWith('/ic_diagram.xml'))
    .map(e => e.entryName.split('/')[0]);
}
module.exports = { JarParser };
6. validators/LogValidator.js
Contains the complex SQL logic for your "Log" test case.
JavaScript
const { expect } = require('@playwright/test');
const { DbManager } = require('../lib/db-manager');

class LogValidator {
  constructor(dbPath) {
    this.db = new DbManager(dbPath);
  }

  verifyPortUnavailableLogs(logName) {
    // The Complex SQL Query
    const sql = `
      WITH LogData AS ( SELECT diagram_name, mito_block, instance_port, description FROM logsummary WHERE log_name = ? ), 
      SplitPort AS ( SELECT diagram_name, mito_block, instance_port, description, SUBSTR(instance_port, 1, INSTR(instance_port, '/') - 1) AS block_name, SUBSTR(instance_port, INSTR(instance_port, '/') + 1) AS port_name FROM LogData ), 
      DiagramParam AS ( SELECT s.diagram_name, s.mito_block, s.instance_port, s.description, s.block_name, s.port_name, dp.block_type FROM SplitPort s JOIN diagram_parameter dp ON s.diagram_name = dp.diagram_name AND s.block_name = dp.block AND s.port_name = dp.i_o_name ), 
      FunctionMapping AS ( SELECT d.diagram_name, d.mito_block, d.instance_port, d.description, d.block_name, d.port_name, d.block_type, fm.source_target_symbol, fm.source_port_id FROM DiagramParam d LEFT JOIN functionmappinginfo fm ON d.block_type = fm.source_target_symbol AND d.port_name = fm.source_port_id ) 
      SELECT s.diagram_name, s.mito_block, s.instance_port, s.description, 
      CASE WHEN fm.source_target_symbol IS NULL THEN CASE WHEN s.description = 'THE PORT IS NOT AVAILABLE IN THE CURRENT LIBRARY AND THEREFORE CANNOT BE EVALUATED!!!' THEN 'PASS' ELSE 'FAIL: No mapping found, but description is incorrect.' END ELSE CASE WHEN s.description = 'THE PORT IS NOT AVAILABLE IN THE CURRENT LIBRARY AND THEREFORE CANNOT BE EVALUATED!!!' THEN 'FAIL: Mapping found, but description is incorrect.' ELSE 'PASS' END END AS result 
      FROM SplitPort s LEFT JOIN FunctionMapping fm ON s.diagram_name = fm.diagram_name AND s.block_name = fm.block_name AND s.port_name = fm.port_name;
    `;

    const results = this.db.query(sql, [logName]);

    // Validation Logic
    console.log(`Validating ${results.length} log entries...`);
    for (const row of results) {
      expect(row.result, 
        `Error in Diagram: ${row.diagram_name}, Block: ${row.mito_block}, Port: ${row.instance_port}`
      ).toBe('PASS');
    }
  }
}
module.exports = { LogValidator };
7. validators/ConnectionValidator.js
Contains the "Case I vs Case II" logic for connections.
JavaScript
const { expect } = require('@playwright/test');
const { DbManager } = require('../lib/db-manager');
const { JarParser } = require('../lib/jar-parser');

class ConnectionValidator {
  constructor(dbPath, jarPath) {
    this.db = new DbManager(dbPath);
    this.jar = new JarParser(jarPath);
  }

  verifyNegationConnectors(diagramNameFilter) {
    // 1. Get relevant data from diagram_parameter
    // Note: Added filter by diagram name from input data
    const negations = this.db.query(`
      SELECT diagram_name, block, port_name, block_type, source_port_id, interconnection 
      FROM diagram_parameter 
      WHERE diagram_name = ? AND interconnection LIKE '%-%'`, 
      [diagramNameFilter]
    );

    if (negations.length === 0) console.log("No negation connections found to test.");

    for (const row of negations) {
        this.validateSingleConnection(row);
    }
  }

  validateSingleConnection(row) {
    // A. Parse Interconnection String
    const match = row.interconnection.match(/-" "(.*?)\\([^.]+)\.([^)]+)/);
if (!match) {
  this.logError(`Invalid interconnection format: ${row.interconnection}`);
  return;
}
    const [_, srcDiagram, srcBlock, srcPortId] = matches;

    // B. Determine Case (SQL Check)
    const mappingRes = this.db.query(
      `SELECT dest_param_id FROM functionmappinginfo 
       WHERE source_target_symbol = ? AND source_port_id = ?`, 
      [row.block_type, srcPortId]
    );

    let isCaseII = false;
    let destParamIdNumeric = null;

    if (mappingRes.length > 0) {
      const destParamId = mappingRes[0].dest_param_id;
      const numMatch = destParamId ? destParamId.match(/\d+/) : null;
      if (numMatch) {
        isCaseII = true;
        destParamIdNumeric = numMatch[0];
      }
    }

    // C. XML Validation
    // If destParamIdNumeric is null (Case I), you might need to query 'temp_generated_jar' 
    // Before XML check
if (!destParamIdNumeric) {
  const tempRes = this.db.query(
    `SELECT port FROM temp_generated_jar WHERE port LIKE '%${row.port_name}%' AND block = ?`,
    [row.block]
  );
  if (tempRes.length > 0) {
    destParamIdNumeric = tempRes[0].port.match(/\d+/)?.[0] || '10'; // Extract numeric
  }
}
    const $ = this.jar.getDiagramXml(row.diagram_name);
    
    // Construct the item name to search: <block>.NEG.<id>
    const searchItem = `${row.block}.NEG.${destParamIdNumeric}`;
    const blockNode = $(`name[item$="${searchItem}"]`).parent('afi');

    expect(blockNode.length, `Block ${row.block} with negation ${searchItem} not found in XML`).toBeGreaterThan(0);

    const specificPort = blockNode.find(`portIdentifier portId:contains("${destParamIdNumeric}")`).closest('port');

    if (isCaseII) {
       // Expect Connection
       const hasConnection = specificPort.find('connection').length > 0;
       expect(hasConnection, `[Case II] Block ${row.block}: Expected <connection> node`).toBeTruthy();
    } else {
       // Expect Connector
       const hasConnector = specificPort.find('sigdef connector').length > 0;
       expect(hasConnector, `[Case I] Block ${row.block}: Expected <connector> node`).toBeTruthy();
    }
  }
}
module.exports = { ConnectionValidator };
8. tests/backend.spec.js
The actual test file. Notice how clean it is. It focuses on intent, not implementation.
JavaScript
const { test } = require('@playwright/test');
const { LogValidator } = require('../validators/LogValidator');
const { ConnectionValidator } = require('../validators/ConnectionValidator');
const testData = require('../testdata/execution-data.json');

test.describe('MITO Backend Automation', () => {

  test('Verify Log Summary Errors (Port Unavailable)', async ({ config }) => {
    const validator = new LogValidator(config.use.dbPath);
    
    // Execute logic using data from JSON
    validator.verifyPortUnavailableLogs(testData.logVerification.logName);
  });

  test('Verify Negation Connectors & Connections in XML', async ({ config }) => {
    const validator = new ConnectionValidator(config.use.dbPath, config.use.jarPath);
    
    // Execute logic
    validator.verifyNegationConnectors(testData.connectionVerification.diagramName);
  });

});

9. global-setup.js:JavaScript// global-setup.js
const { chromium } = require('@playwright/test'); // Not used, but keeps Playwright happy
const fs = require('fs');
const path = require('path');

module.exports = async () => {
  // Pre-run validation: Check if DB/JAR paths exist
  const config = require('./playwright.config.js').use;
  if (!fs.existsSync(config.dbPath)) throw new Error(`DB not found: ${config.dbPath}`);
  if (!fs.existsSync(config.jarPath)) throw new Error(`JAR not found: ${config.jarPath}`);
  console.log('Global setup: Inputs validated.');
};

10. // validators/BaseValidator.js (new file, extendable)
const winston = require('winston');
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.simple(),
  transports: [new winston.transports.Console()],
});

class BaseValidator {
  logInfo(msg) { logger.info(msg); }
  logError(msg) { logger.error(msg); }
}
module.exports = { BaseValidator };

