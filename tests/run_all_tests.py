#!/usr/bin/env python3
"""
完整测试套件运行器
Comprehensive test suite runner for EPUB to Markdown converter

运行所有集成测试和边缘情况测试
验证系统的完整功能和健壮性
"""

import os
import sys
import unittest
import time
from io import StringIO

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 导入测试模块
from test_integration import TestEPUBIntegration
from test_edge_cases import TestEPUBEdgeCases


class TestResults:
    """测试结果统计"""
    
    def __init__(self):
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.error_tests = 0
        self.skipped_tests = 0
        self.start_time = None
        self.end_time = None
        self.test_details = []
    
    def start_timing(self):
        """开始计时"""
        self.start_time = time.time()
    
    def end_timing(self):
        """结束计时"""
        self.end_time = time.time()
    
    def get_duration(self):
        """获取测试持续时间"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0
    
    def add_test_result(self, test_name, status, message=""):
        """添加测试结果"""
        self.test_details.append({
            'name': test_name,
            'status': status,
            'message': message
        })
        
        if status == 'PASS':
            self.passed_tests += 1
        elif status == 'FAIL':
            self.failed_tests += 1
        elif status == 'ERROR':
            self.error_tests += 1
        elif status == 'SKIP':
            self.skipped_tests += 1
        
        self.total_tests += 1
    
    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "=" * 70)
        print("测试结果摘要 / Test Results Summary")
        print("=" * 70)
        print(f"总测试数 / Total Tests: {self.total_tests}")
        print(f"通过 / Passed: {self.passed_tests}")
        print(f"失败 / Failed: {self.failed_tests}")
        print(f"错误 / Errors: {self.error_tests}")
        print(f"跳过 / Skipped: {self.skipped_tests}")
        print(f"测试时间 / Duration: {self.get_duration():.2f} 秒")
        
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        print(f"成功率 / Success Rate: {success_rate:.1f}%")
        
        if self.failed_tests > 0 or self.error_tests > 0:
            print("\n失败的测试 / Failed Tests:")
            for detail in self.test_details:
                if detail['status'] in ['FAIL', 'ERROR']:
                    print(f"  - {detail['name']}: {detail['status']}")
                    if detail['message']:
                        print(f"    {detail['message']}")
        
        print("=" * 70)


def run_test_suite(test_class, suite_name):
    """
    运行测试套件
    
    Args:
        test_class: 测试类
        suite_name: 套件名称
        
    Returns:
        TestResults: 测试结果
    """
    print(f"\n运行 {suite_name} 测试套件...")
    print("-" * 50)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(test_class)
    
    # 创建自定义测试运行器
    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    
    # 运行测试
    result = runner.run(suite)
    
    # 解析结果
    test_results = TestResults()
    
    # 统计成功的测试
    tests_run = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped) if hasattr(result, 'skipped') else 0
    passed = tests_run - failures - errors - skipped
    
    test_results.total_tests = tests_run
    test_results.passed_tests = passed
    test_results.failed_tests = failures
    test_results.error_tests = errors
    test_results.skipped_tests = skipped
    
    # 添加详细结果
    for test, traceback in result.failures:
        test_name = str(test).split()[0]
        test_results.add_test_result(test_name, 'FAIL', str(traceback).split('\n')[-2] if traceback else "")
    
    for test, traceback in result.errors:
        test_name = str(test).split()[0]
        test_results.add_test_result(test_name, 'ERROR', str(traceback).split('\n')[-2] if traceback else "")
    
    # 打印套件结果
    print(f"{suite_name} 结果:")
    print(f"  通过: {passed}/{tests_run}")
    print(f"  失败: {failures}")
    print(f"  错误: {errors}")
    if skipped > 0:
        print(f"  跳过: {skipped}")
    
    return test_results


def main():
    """主函数"""
    print("EPUB到Markdown转换器 - 完整测试套件")
    print("EPUB to Markdown Converter - Complete Test Suite")
    print("=" * 70)
    
    overall_results = TestResults()
    overall_results.start_timing()
    
    # 运行集成测试
    integration_results = run_test_suite(TestEPUBIntegration, "集成测试 / Integration Tests")
    
    # 运行边缘情况测试
    edge_case_results = run_test_suite(TestEPUBEdgeCases, "边缘情况测试 / Edge Case Tests")
    
    overall_results.end_timing()
    
    # 合并结果
    overall_results.total_tests = integration_results.total_tests + edge_case_results.total_tests
    overall_results.passed_tests = integration_results.passed_tests + edge_case_results.passed_tests
    overall_results.failed_tests = integration_results.failed_tests + edge_case_results.failed_tests
    overall_results.error_tests = integration_results.error_tests + edge_case_results.error_tests
    overall_results.skipped_tests = integration_results.skipped_tests + edge_case_results.skipped_tests
    
    # 合并详细结果
    overall_results.test_details.extend(integration_results.test_details)
    overall_results.test_details.extend(edge_case_results.test_details)
    
    # 打印总体摘要
    overall_results.print_summary()
    
    # 返回退出代码
    if overall_results.failed_tests > 0 or overall_results.error_tests > 0:
        print("\n❌ 部分测试失败")
        return 1
    else:
        print("\n✅ 所有测试通过")
        return 0


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)