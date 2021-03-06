"""
* Copyright 2019 EPAM Systems
*
* Licensed under the Apache License, Version 2.0 (the "License");
* you may not use this file except in compliance with the License.
* You may obtain a copy of the License at
*
* http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.
"""

import unittest
from unittest.mock import MagicMock
from http import HTTPStatus
import sure # noqa
import httpretty

import commons.launch_objects as launch_objects
from boosting_decision_making.boosting_decision_maker import BoostingDecisionMaker
from service.suggest_service import SuggestService
from test.test_service import TestService
from utils import utils


class TestSuggestService(TestService):

    @utils.ignore_warnings
    def test_suggest_items(self):
        """Test suggesting test items"""
        tests = [
            {
                "test_calls":          [{"method":         httpretty.GET,
                                         "uri":            "/1",
                                         "status":         HTTPStatus.OK,
                                         }, ],
                "test_item_info":      launch_objects.TestItemInfo(testItemId=1,
                                                                   uniqueId="341",
                                                                   testCaseHash=123,
                                                                   launchId=1,
                                                                   launchName="Launch",
                                                                   project=1,
                                                                   logs=[]),
                "expected_result":     [],
                "boost_predict":       ([], [])
            },
            {
                "test_calls":     [{"method":         httpretty.GET,
                                    "uri":            "/2",
                                    "status":         HTTPStatus.NOT_FOUND,
                                    }, ],
                "test_item_info": launch_objects.TestItemInfo(testItemId=1,
                                                              uniqueId="341",
                                                              testCaseHash=123,
                                                              launchId=1,
                                                              launchName="Launch",
                                                              project=2,
                                                              logs=[launch_objects.Log(
                                                                    logId=1,
                                                                    message="error found",
                                                                    logLevel=40000)]),
                "expected_result":     [],
                "boost_predict":       ([], [])
            },
            {
                "test_calls":          [{"method":         httpretty.GET,
                                         "uri":            "/1",
                                         "status":         HTTPStatus.OK,
                                         }, ],
                "test_item_info":      launch_objects.TestItemInfo(testItemId=1,
                                                                   uniqueId="341",
                                                                   testCaseHash=123,
                                                                   launchId=1,
                                                                   launchName="Launch",
                                                                   project=1,
                                                                   logs=[launch_objects.Log(
                                                                         logId=1,
                                                                         message=" ",
                                                                         logLevel=40000)]),
                "expected_result":     [],
                "boost_predict":       ([], [])
            },
            {
                "test_calls":     [{"method":         httpretty.GET,
                                    "uri":            "/1",
                                    "status":         HTTPStatus.OK,
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_first),
                                    "rs":           utils.get_fixture(
                                        self.no_hits_search_rs),
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_second),
                                    "rs":           utils.get_fixture(
                                        self.no_hits_search_rs),
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_third),
                                    "rs":           utils.get_fixture(
                                        self.no_hits_search_rs),
                                    }],
                "test_item_info":      launch_objects.TestItemInfo(
                    **utils.get_fixture(self.suggest_test_item_info_w_logs, to_json=True)),
                "expected_result":     [],
                "boost_predict":       ([], [])
            },
            {
                "test_calls":     [{"method":         httpretty.GET,
                                    "uri":            "/1",
                                    "status":         HTTPStatus.OK,
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_first),
                                    "rs":           utils.get_fixture(
                                        self.no_hits_search_rs),
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_second),
                                    "rs":           utils.get_fixture(
                                        self.no_hits_search_rs),
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_third),
                                    "rs":           utils.get_fixture(
                                        self.no_hits_search_rs),
                                    }],
                "test_item_info":      launch_objects.TestItemInfo(
                    **utils.get_fixture(self.suggest_test_item_info_w_logs, to_json=True)),
                "expected_result":     [],
                "boost_predict":       ([], [])
            },
            {
                "test_calls":     [{"method":         httpretty.GET,
                                    "uri":            "/1",
                                    "status":         HTTPStatus.OK,
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_first),
                                    "rs":           utils.get_fixture(
                                        self.no_hits_search_rs),
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_second),
                                    "rs":           utils.get_fixture(
                                        self.one_hit_search_rs),
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_third),
                                    "rs":           utils.get_fixture(
                                        self.one_hit_search_rs),
                                    }, ],
                "test_item_info":      launch_objects.TestItemInfo(
                    **utils.get_fixture(self.suggest_test_item_info_w_logs, to_json=True)),
                "expected_result":     [
                    launch_objects.SuggestAnalysisResult(testItem=123,
                                                         testItemLogId=178,
                                                         issueType='AB001',
                                                         relevantItem=1,
                                                         relevantLogId=1,
                                                         matchScore=80.0,
                                                         esScore=10.0,
                                                         esPosition=0,
                                                         modelFeatureNames='0',
                                                         modelFeatureValues='1.0',
                                                         modelInfo='',
                                                         resultPosition=0,
                                                         usedLogLines=-1,
                                                         minShouldMatch=80)],
                "boost_predict":       ([1], [[0.2, 0.8]])
            },
            {
                "test_calls":     [{"method":         httpretty.GET,
                                    "uri":            "/1",
                                    "status":         HTTPStatus.OK,
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_first),
                                    "rs":           utils.get_fixture(
                                        self.one_hit_search_rs),
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_second),
                                    "rs":           utils.get_fixture(
                                        self.one_hit_search_rs),
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_third),
                                    "rs":           utils.get_fixture(
                                        self.one_hit_search_rs),
                                    }, ],
                "test_item_info":      launch_objects.TestItemInfo(
                    **utils.get_fixture(self.suggest_test_item_info_w_logs, to_json=True)),
                "expected_result":     [
                    launch_objects.SuggestAnalysisResult(testItem=123,
                                                         testItemLogId=178,
                                                         issueType='AB001',
                                                         relevantItem=1,
                                                         relevantLogId=1,
                                                         matchScore=70.0,
                                                         esScore=10.0,
                                                         esPosition=0,
                                                         modelFeatureNames='0',
                                                         modelFeatureValues='1.0',
                                                         modelInfo='',
                                                         resultPosition=0,
                                                         usedLogLines=-1,
                                                         minShouldMatch=80)],
                "boost_predict":       ([1], [[0.3, 0.7]])
            },
            {
                "test_calls":     [{"method":         httpretty.GET,
                                    "uri":            "/1",
                                    "status":         HTTPStatus.OK,
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_first),
                                    "rs":           utils.get_fixture(
                                        self.one_hit_search_rs),
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_second),
                                    "rs":           utils.get_fixture(
                                        self.two_hits_search_rs),
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_third),
                                    "rs":           utils.get_fixture(
                                        self.two_hits_search_rs),
                                    }, ],
                "test_item_info":      launch_objects.TestItemInfo(
                    **utils.get_fixture(self.suggest_test_item_info_w_logs, to_json=True)),
                "expected_result":     [
                    launch_objects.SuggestAnalysisResult(testItem=123,
                                                         testItemLogId=178,
                                                         issueType='AB001',
                                                         relevantItem=1,
                                                         relevantLogId=1,
                                                         matchScore=70.0,
                                                         esScore=15.0,
                                                         esPosition=0,
                                                         modelFeatureNames='0',
                                                         modelFeatureValues='1.0',
                                                         modelInfo='',
                                                         resultPosition=0,
                                                         usedLogLines=-1,
                                                         minShouldMatch=80)],
                "boost_predict":       ([1, 0], [[0.3, 0.7], [0.9, 0.1]])
            },
            {
                "test_calls":     [{"method":         httpretty.GET,
                                    "uri":            "/1",
                                    "status":         HTTPStatus.OK,
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_first),
                                    "rs":           utils.get_fixture(
                                        self.one_hit_search_rs),
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_second),
                                    "rs":           utils.get_fixture(
                                        self.two_hits_search_rs),
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_third),
                                    "rs":           utils.get_fixture(
                                        self.no_hits_search_rs),
                                    }, ],
                "test_item_info":      launch_objects.TestItemInfo(
                    **utils.get_fixture(self.suggest_test_item_info_w_logs, to_json=True)),
                "expected_result":     [
                    launch_objects.SuggestAnalysisResult(testItem=123,
                                                         testItemLogId=178,
                                                         issueType='AB001',
                                                         relevantItem=1,
                                                         relevantLogId=1,
                                                         matchScore=70.0,
                                                         esScore=15.0,
                                                         esPosition=0,
                                                         modelFeatureNames='0',
                                                         modelFeatureValues='1.0',
                                                         modelInfo='',
                                                         resultPosition=0,
                                                         usedLogLines=-1,
                                                         minShouldMatch=80),
                    launch_objects.SuggestAnalysisResult(testItem=123,
                                                         testItemLogId=178,
                                                         issueType='PB001',
                                                         relevantItem=2,
                                                         relevantLogId=2,
                                                         matchScore=45.0,
                                                         esScore=10.0,
                                                         esPosition=1,
                                                         modelFeatureNames='0',
                                                         modelFeatureValues='0.67',
                                                         modelInfo='',
                                                         resultPosition=1,
                                                         usedLogLines=-1,
                                                         minShouldMatch=80)],
                "boost_predict":       ([1, 0], [[0.3, 0.7], [0.55, 0.45]])
            },
            {
                "test_calls":     [{"method":         httpretty.GET,
                                    "uri":            "/1",
                                    "status":         HTTPStatus.OK,
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_first),
                                    "rs":           utils.get_fixture(
                                        self.two_hits_search_rs),
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_second),
                                    "rs":           utils.get_fixture(
                                        self.three_hits_search_rs),
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_third),
                                    "rs":           utils.get_fixture(
                                        self.no_hits_search_rs),
                                    }, ],
                "test_item_info":      launch_objects.TestItemInfo(
                    **utils.get_fixture(self.suggest_test_item_info_w_logs, to_json=True)),
                "expected_result":     [
                    launch_objects.SuggestAnalysisResult(testItem=123,
                                                         testItemLogId=178,
                                                         issueType='PB001',
                                                         relevantItem=3,
                                                         relevantLogId=3,
                                                         matchScore=80.0,
                                                         esScore=10.0,
                                                         esPosition=2,
                                                         modelFeatureNames='0',
                                                         modelFeatureValues='0.67',
                                                         modelInfo='',
                                                         resultPosition=0,
                                                         usedLogLines=-1,
                                                         minShouldMatch=80),
                    launch_objects.SuggestAnalysisResult(testItem=123,
                                                         testItemLogId=178,
                                                         issueType='AB001',
                                                         relevantItem=1,
                                                         relevantLogId=1,
                                                         matchScore=70.0,
                                                         esScore=15.0,
                                                         esPosition=0,
                                                         modelFeatureNames='0',
                                                         modelFeatureValues='1.0',
                                                         modelInfo='',
                                                         resultPosition=1,
                                                         usedLogLines=-1,
                                                         minShouldMatch=80),
                    launch_objects.SuggestAnalysisResult(testItem=123,
                                                         testItemLogId=178,
                                                         issueType='PB001',
                                                         relevantItem=2,
                                                         relevantLogId=2,
                                                         matchScore=45.0,
                                                         esScore=10.0,
                                                         esPosition=1,
                                                         modelFeatureNames='0',
                                                         modelFeatureValues='0.67',
                                                         modelInfo='',
                                                         resultPosition=2,
                                                         usedLogLines=-1,
                                                         minShouldMatch=80)],
                "boost_predict":       ([1, 0, 1], [[0.3, 0.7], [0.55, 0.45], [0.2, 0.8]])
            },
            {
                "test_calls":     [{"method":         httpretty.GET,
                                    "uri":            "/1",
                                    "status":         HTTPStatus.OK,
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_first),
                                    "rs":           utils.get_fixture(
                                        self.two_hits_search_rs),
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_second),
                                    "rs":           utils.get_fixture(
                                        self.three_hits_search_rs_with_duplicate),
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_third),
                                    "rs":           utils.get_fixture(
                                        self.no_hits_search_rs),
                                    }, ],
                "test_item_info":      launch_objects.TestItemInfo(
                    **utils.get_fixture(self.suggest_test_item_info_w_logs, to_json=True)),
                "expected_result":     [
                    launch_objects.SuggestAnalysisResult(testItem=123,
                                                         testItemLogId=178,
                                                         issueType='AB001',
                                                         relevantItem=3,
                                                         relevantLogId=3,
                                                         matchScore=70.0,
                                                         esScore=15.0,
                                                         esPosition=0,
                                                         modelFeatureNames='0',
                                                         modelFeatureValues='1.0',
                                                         modelInfo='',
                                                         resultPosition=0,
                                                         usedLogLines=-1,
                                                         minShouldMatch=80),
                    launch_objects.SuggestAnalysisResult(testItem=123,
                                                         testItemLogId=178,
                                                         issueType='AB001',
                                                         relevantItem=1,
                                                         relevantLogId=1,
                                                         matchScore=70.0,
                                                         esScore=15.0,
                                                         esPosition=0,
                                                         modelFeatureNames='0',
                                                         modelFeatureValues='1.0',
                                                         modelInfo='',
                                                         resultPosition=1,
                                                         usedLogLines=-1,
                                                         minShouldMatch=80),
                    launch_objects.SuggestAnalysisResult(testItem=123,
                                                         testItemLogId=178,
                                                         issueType='PB001',
                                                         relevantItem=2,
                                                         relevantLogId=2,
                                                         matchScore=70.0,
                                                         esScore=10.0,
                                                         esPosition=1,
                                                         modelFeatureNames='0',
                                                         modelFeatureValues='0.67',
                                                         modelInfo='',
                                                         resultPosition=2,
                                                         usedLogLines=-1,
                                                         minShouldMatch=80)],
                "boost_predict":       ([1, 1, 1], [[0.3, 0.7], [0.3, 0.7], [0.3, 0.7]])
            },
            {
                "test_calls":     [{"method":         httpretty.GET,
                                    "uri":            "/1",
                                    "status":         HTTPStatus.OK,
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_merged_first),
                                    "rs":           utils.get_fixture(
                                        self.one_hit_search_rs_merged),
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_merged_second),
                                    "rs":           utils.get_fixture(
                                        self.one_hit_search_rs_merged),
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_merged_third),
                                    "rs":           utils.get_fixture(
                                        self.one_hit_search_rs_merged),
                                    }, ],
                "test_item_info":      launch_objects.TestItemInfo(
                    **utils.get_fixture(self.suggest_test_item_info_w_merged_logs, to_json=True)),
                "expected_result":     [
                    launch_objects.SuggestAnalysisResult(testItem=123,
                                                         testItemLogId=-1,
                                                         issueType='AB001',
                                                         relevantItem=1,
                                                         relevantLogId=1,
                                                         matchScore=90.0,
                                                         esScore=10.0,
                                                         esPosition=0,
                                                         modelFeatureNames='0',
                                                         modelFeatureValues='1.0',
                                                         modelInfo='',
                                                         resultPosition=0,
                                                         usedLogLines=-1,
                                                         minShouldMatch=80)],
                "boost_predict":       ([1], [[0.1, 0.9]])
            },
            {
                "test_calls":     [{"method":         httpretty.GET,
                                    "uri":            "/1",
                                    "status":         HTTPStatus.OK,
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_merged_first),
                                    "rs":           utils.get_fixture(
                                        self.one_hit_search_rs_merged_wrong),
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_merged_second),
                                    "rs":           utils.get_fixture(
                                        self.one_hit_search_rs_merged_wrong),
                                    },
                                   {"method":       httpretty.GET,
                                    "uri":          "/1/_search",
                                    "status":       HTTPStatus.OK,
                                    "content_type": "application/json",
                                    "rq":           utils.get_fixture(self.search_rq_merged_third),
                                    "rs":           utils.get_fixture(
                                        self.one_hit_search_rs_merged_wrong),
                                    }, ],
                "test_item_info":      launch_objects.TestItemInfo(
                    **utils.get_fixture(self.suggest_test_item_info_w_merged_logs, to_json=True)),
                "expected_result":     [],
                "boost_predict":       ([], [])
            },
        ]

        for idx, test in enumerate(tests):
            with sure.ensure('Error in the test case number: {0}', idx):
                self._start_server(test["test_calls"])
                config = self.get_default_search_config()
                suggest_service = SuggestService(app_config=self.app_config,
                                                 search_cfg=config)
                _boosting_decision_maker = BoostingDecisionMaker()
                _boosting_decision_maker.get_feature_ids = MagicMock(return_value=[0])
                _boosting_decision_maker.predict = MagicMock(return_value=test["boost_predict"])
                suggest_service.suggest_decision_maker = _boosting_decision_maker
                response = suggest_service.suggest_items(test["test_item_info"])

                response.should.have.length_of(len(test["expected_result"]))
                for real_resp, expected_resp in zip(response, test["expected_result"]):
                    real_resp.should.equal(expected_resp)

                TestSuggestService.shutdown_server(test["test_calls"])


if __name__ == '__main__':
    unittest.main()
