1. Updated testdata/execution-data.json
Each test case now owns its specific file paths.

JSON

{
  "logVerification": {
    "dbPath": "C:/MITO/Project1/MITO.db",
    "jarPath": "C:/MITO/Project1/Generated.jar",
    "logName": "Import PCS7 Diagram-24-12-2025, 05:32 PM"
  },
  "connectionVerification": {
    "dbPath": "C:/MITO/Project1/MITO.db",
    "jarPath": "C:/MITO/Project1/Generated.jar",
    "diagramName": "=7BHA01GH001"
  },
  "blockCountVerification": {
    "dbPath": "C:/MITO/Project2/MITO.db",
    "jarPath": "C:/MITO/Project2/Generated.jar",
    "diagramName": "=7BHA01GH001"
  }
}



3. Updated tests/backend.spec.js
The test file is now even cleaner as it pulls everything from the JSON.

JavaScript

const { test } = require('@playwright/test');
const { LogValidator } = require('../validators/LogValidator');
const { ConnectionValidator } = require('../validators/ConnectionValidator');
const { BlockValidator } = require('../validators/BlockValidator'); // New
const testData = require('../testdata/execution-data.json');

test.describe('MITO Backend Logic Automation', () => {

  test('Verify Log Summary Errors', async () => {
    const data = testData.logVerification;
    const validator = new LogValidator(data.dbPath);
    validator.verifyPortUnavailableLogs(data.logName);
  });

  test('Verify Negation Connectors', async () => {
    const data = testData.connectionVerification;
    const validator = new ConnectionValidator(data.dbPath, data.jarPath);
    validator.verifyNegationConnectors(data.diagramName);
  });

  test('Verify XML Block Count vs DB', async () => {
    const data = testData.blockCountVerification;
    const validator = new BlockValidator(data.dbPath, data.jarPath);
    await validator.verifyBlockCounts(data.diagramName);
  });

});



Corrected validators/BlockValidator.js
This version removes any mention of symbol mapping and focuses purely on the Variant-to-Variant check as you described.

JavaScript

const { expect } = require('@playwright/test');
const { DbManager } = require('../lib/db-manager');
const { JarParser } = require('../lib/jar-parser');

class BlockValidator {
  constructor(dbPath, jarPath) {
    this.db = new DbManager(dbPath);
    this.jar = new JarParser(jarPath);
  }

  async verifyBlockCounts(diagramName) {
    // 1. Get total records from diagram_blocks (The baseline for all blocks)
    const dbTotalResult = this.db.query(
      `SELECT COUNT(*) as total FROM diagram_blocks WHERE diagram_name = ?`,
      [diagramName]
    );
    const expectedTotal = dbTotalResult[0].total;

    // 2. Count actual nodes in the ic_diagram.xml
    const $ = this.jar.getDiagramXml(diagramName);
    const afiCount = $('afi').length;
    const compoundCount = $('compound').length;
    const actualTotalXML = afiCount + compoundCount;

    console.log(`[Step 1] DB Total: ${expectedTotal} | XML Total: ${actualTotalXML}`);
    expect(actualTotalXML, `Total XML nodes (AFI+Compound) do not match diagram_blocks table`).toBe(expectedTotal);

    // 3. Identify Compound Blocks
    // First, find unique block/variant pairs from diagram_parameter ending in _CC
    const potentialCompounds = this.db.query(`
      SELECT DISTINCT block, variant 
      FROM diagram_parameter 
      WHERE diagram_name = ? AND variant LIKE '%_CC'
    `, [diagramName]);

    let calculatedCompoundCount = 0;

    for (const record of potentialCompounds) {
      // Filter functionmappinginfo by the Variant column using the variant text
      const mappings = this.db.query(`
        SELECT generation_type 
        FROM functionmappinginfo 
        WHERE Variant = ?
      `, [record.variant]);

      // Check if the generation_type is 'Compound Component'
      const isCompound = mappings.some(m => m.generation_type === 'Compound Component');
      
      if (isCompound) {
        calculatedCompoundCount++;
        console.log(`[Step 2] Block "${record.block}" confirmed as Compound (Variant: ${record.variant})`);
      }
    }

    // 4. Final Comparison for Compound nodes
    console.log(`[Step 3] Calculated Compounds from DB: ${calculatedCompoundCount} | XML <compound> nodes: ${compoundCount}`);
    expect(compoundCount, `XML <compound> node count does not match the Logic check`).toBe(calculatedCompoundCount);
  }
}

module.exports = { BlockValidator };



