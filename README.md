.env
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-api-token
FIX_VERSION=release-2.5
TEST_PLAN_KEY=TP-123
TEST_EXECUTION_KEY=TEMP-456
PROJECT_KEY=PROJ

import os
import requests
from typing import Dict, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class JiraXrayAnalyzer:
    def __init__(self):
        self.jira_url = os.getenv('JIRA_URL')
        self.email = os.getenv('JIRA_EMAIL')
        self.api_token = os.getenv('JIRA_API_TOKEN')
        self.auth = (self.email, self.api_token)
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Validate required environment variables
        if not all([self.jira_url, self.email, self.api_token]):
            raise ValueError("Missing required environment variables: JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN")

    def make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make API request to Jira"""
        url = f"{self.jira_url}/rest/api/3/{endpoint}"
        response = requests.get(url, auth=self.auth, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def get_tickets_by_fix_version(self) -> List[Dict]:
        """Get tickets based on fix version from environment variable"""
        fix_version = os.getenv('FIX_VERSION')
        project_key = os.getenv('PROJECT_KEY')
        
        if not fix_version:
            print("FIX_VERSION not set in environment variables")
            return []
        
        jql = f'fixVersion = "{fix_version}"'
        if project_key:
            jql = f'project = {project_key} AND {jql}'
        
        params = {
            'jql': jql,
            'fields': 'key,summary,issuetype',
            'maxResults': 1000
        }
        
        print(f"Fetching tickets for fix version: {fix_version}")
        data = self.make_request('search', params)
        
        tickets = []
        for issue in data.get('issues', []):
            tickets.append({
                'key': issue['key'],
                'summary': issue['fields']['summary'],
                'type': issue['fields']['issuetype']['name']
            })
        
        return tickets

    def get_test_execution_results(self) -> Dict:
        """Get test execution results from environment variable"""
        test_execution_key = os.getenv('TEST_EXECUTION_KEY')
        
        if not test_execution_key:
            print("TEST_EXECUTION_KEY not set in environment variables")
            return {}
        
        print(f"Fetching test execution results for: {test_execution_key}")
        
        # Get tests from the test execution using JQL
        params = {
            'jql': f'issue in testExecutions("{test_execution_key}")',
            'fields': 'key,status,summary,customfield_10030',  # customfield_10030 is typically defects in Xray
            'maxResults': 1000
        }
        
        tests_data = self.make_request('search', params)
        
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        failed_tests_with_bugs = []
        
        for test in tests_data.get('issues', []):
            total_tests += 1
            status = test['fields']['status']['name'].upper()
            
            if status in ['PASS', 'PASSED']:
                passed_tests += 1
            elif status in ['FAIL', 'FAILED']:
                failed_tests += 1
                
                # Get defects (bugs) associated with this test failure
                defects = test['fields'].get('customfield_10030', [])
                bug_ids = [defect['key'] for defect in defects]
                
                failed_tests_with_bugs.append({
                    'test_key': test['key'],
                    'test_summary': test['fields']['summary'],
                    'bug_ids': bug_ids
                })
        
        return {
            'test_execution_key': test_execution_key,
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'failed_tests_with_bugs': failed_tests_with_bugs
        }

    def get_test_plan_results(self) -> Dict:
        """Get results for test plan from environment variable"""
        test_plan_key = os.getenv('TEST_PLAN_KEY')
        
        if not test_plan_key:
            print("TEST_PLAN_KEY not set in environment variables")
            return {}
        
        print(f"Fetching test plan results for: {test_plan_key}")
        
        # Get test executions linked to the test plan
        params = {
            'jql': f'issue in testPlans("{test_plan_key}") and issuetype = "Test Execution"',
            'fields': 'key,summary',
            'maxResults': 1000
        }
        
        executions_data = self.make_request('search', params)
        
        all_results = []
        total_aggregated = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'failed_tests_with_bugs': []
        }
        
        for execution in executions_data.get('issues', []):
            execution_key = execution['key']
            
            # Get results for each test execution
            execution_params = {
                'jql': f'issue in testExecutions("{execution_key}")',
                'fields': 'key,status,customfield_10030',
                'maxResults': 1000
            }
            
            tests_data = self.make_request('search', execution_params)
            
            execution_total = 0
            execution_passed = 0
            execution_failed = 0
            execution_failed_with_bugs = []
            
            for test in tests_data.get('issues', []):
                execution_total += 1
                status = test['fields']['status']['name'].upper()
                
                if status in ['PASS', 'PASSED']:
                    execution_passed += 1
                elif status in ['FAIL', 'FAILED']:
                    execution_failed += 1
                    
                    defects = test['fields'].get('customfield_10030', [])
                    bug_ids = [defect['key'] for defect in defects]
                    
                    if bug_ids:
                        execution_failed_with_bugs.append({
                            'test_key': test['key'],
                            'bug_ids': bug_ids
                        })
            
            all_results.append({
                'execution_key': execution_key,
                'total_tests': execution_total,
                'passed_tests': execution_passed,
                'failed_tests': execution_failed,
                'failed_tests_with_bugs': execution_failed_with_bugs
            })
            
            # Aggregate results
            total_aggregated['total_tests'] += execution_total
            total_aggregated['passed_tests'] += execution_passed
            total_aggregated['failed_tests'] += execution_failed
            total_aggregated['failed_tests_with_bugs'].extend(execution_failed_with_bugs)
        
        return {
            'test_plan_key': test_plan_key,
            'execution_results': all_results,
            'aggregated_results': total_aggregated
        }

def main():
    try:
        analyzer = JiraXrayAnalyzer()
        
        print("Jira Xray Analysis Report")
        print("=" * 60)
        
        # 1. Get tickets by fix version
        if os.getenv('FIX_VERSION'):
            print("\n1. TICKETS BY FIX VERSION:")
            print("-" * 40)
            tickets = analyzer.get_tickets_by_fix_version()
            print(f"Total tickets found: {len(tickets)}")
            for ticket in tickets:
                print(f"  {ticket['key']} [{ticket['type']}]: {ticket['summary']}")
        
        # 2. Get test execution results
        if os.getenv('TEST_EXECUTION_KEY'):
            print("\n2. TEST EXECUTION RESULTS:")
            print("-" * 40)
            execution_results = analyzer.get_test_execution_results()
            if execution_results:
                print(f"Execution Key: {execution_results['test_execution_key']}")
                print(f"Total Tests: {execution_results['total_tests']}")
                print(f"Passed: {execution_results['passed_tests']}")
                print(f"Failed: {execution_results['failed_tests']}")
                
                if execution_results['failed_tests_with_bugs']:
                    print(f"\nFailed tests with bug IDs ({len(execution_results['failed_tests_with_bugs'])}):")
                    for failed_test in execution_results['failed_tests_with_bugs']:
                        print(f"  {failed_test['test_key']} -> Bugs: {', '.join(failed_test['bug_ids'])}")
        
        # 3. Get test plan results
        if os.getenv('TEST_PLAN_KEY'):
            print("\n3. TEST PLAN RESULTS:")
            print("-" * 40)
            plan_results = analyzer.get_test_plan_results()
            if plan_results:
                aggregated = plan_results['aggregated_results']
                print(f"Test Plan Key: {plan_results['test_plan_key']}")
                print(f"Total Test Executions: {len(plan_results['execution_results'])}")
                print(f"Total Tests: {aggregated['total_tests']}")
                print(f"Total Passed: {aggregated['passed_tests']}")
                print(f"Total Failed: {aggregated['failed_tests']}")
                
                if aggregated['failed_tests_with_bugs']:
                    print(f"\nFailed tests with bug IDs ({len(aggregated['failed_tests_with_bugs'])}):")
                    for failed_test in aggregated['failed_tests_with_bugs']:
                        print(f"  {failed_test['test_key']} -> Bugs: {', '.join(failed_test['bug_ids'])}")
        
        print("\n" + "=" * 60)
        print("Analysis completed!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
