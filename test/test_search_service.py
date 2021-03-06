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
from http import HTTPStatus
import sure # noqa
import httpretty

import commons.launch_objects as launch_objects
from service.search_service import SearchService
from test.test_service import TestService
from utils import utils


class TestSearchService(TestService):

    @utils.ignore_warnings
    def test_search_logs(self):
        """Test search logs"""
        tests = [
            {
                "test_calls":     [{"method":         httpretty.GET,
                                    "uri":            "/1",
                                    "status":         HTTPStatus.OK,
                                    },
                                   {"method":         httpretty.GET,
                                    "uri":            "/1/_search",
                                    "status":         HTTPStatus.OK,
                                    "content_type":   "application/json",
                                    "rq":             utils.get_fixture(self.search_logs_rq),
                                    "rs":             utils.get_fixture(
                                        self.no_hits_search_rs),
                                    }, ],
                "rq":             launch_objects.SearchLogs(launchId=1,
                                                            launchName="Launch 1",
                                                            itemId=3,
                                                            projectId=1,
                                                            filteredLaunchIds=[1],
                                                            logMessages=["error"],
                                                            logLines=-1),
                "expected_count": 0
            },
            {
                "test_calls":     [{"method":         httpretty.GET,
                                    "uri":            "/1",
                                    "status":         HTTPStatus.OK,
                                    }, ],
                "rq":             launch_objects.SearchLogs(launchId=1,
                                                            launchName="Launch 1",
                                                            itemId=3,
                                                            projectId=1,
                                                            filteredLaunchIds=[1],
                                                            logMessages=[""],
                                                            logLines=-1),
                "expected_count": 0
            },
            {
                "test_calls":     [{"method":         httpretty.GET,
                                    "uri":            "/1",
                                    "status":         HTTPStatus.OK,
                                    },
                                   {"method":         httpretty.GET,
                                    "uri":            "/1/_search",
                                    "status":         HTTPStatus.OK,
                                    "content_type":   "application/json",
                                    "rq":             utils.get_fixture(self.search_logs_rq),
                                    "rs":             utils.get_fixture(
                                        self.one_hit_search_rs_search_logs),
                                    }, ],
                "rq":             launch_objects.SearchLogs(launchId=1,
                                                            launchName="Launch 1",
                                                            itemId=3,
                                                            projectId=1,
                                                            filteredLaunchIds=[1],
                                                            logMessages=["error"],
                                                            logLines=-1),
                "expected_count": 0
            },
            {
                "test_calls":     [{"method":         httpretty.GET,
                                    "uri":            "/1",
                                    "status":         HTTPStatus.OK,
                                    },
                                   {"method":         httpretty.GET,
                                    "uri":            "/1/_search",
                                    "status":         HTTPStatus.OK,
                                    "content_type":   "application/json",
                                    "rq":             utils.get_fixture(
                                        self.search_logs_rq_not_found),
                                    "rs":             utils.get_fixture(
                                        self.two_hits_search_rs_search_logs),
                                    }, ],
                "rq":             launch_objects.SearchLogs(launchId=1,
                                                            launchName="Launch 1",
                                                            itemId=3,
                                                            projectId=1,
                                                            filteredLaunchIds=[1],
                                                            logMessages=["error occured once"],
                                                            logLines=-1),
                "expected_count": 1
            },
        ]

        for idx, test in enumerate(tests):
            with sure.ensure('Error in the test case number: {0}', idx):
                self._start_server(test["test_calls"])

                search_service = SearchService(app_config=self.app_config,
                                               search_cfg=self.get_default_search_config())

                response = search_service.search_logs(test["rq"])
                response.should.have.length_of(test["expected_count"])

                TestSearchService.shutdown_server(test["test_calls"])


if __name__ == '__main__':
    unittest.main()
