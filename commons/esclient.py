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

import json
import logging
import requests
import elasticsearch
import elasticsearch.helpers
import commons.launch_objects
from elasticsearch import RequestsHttpConnection
from commons.launch_objects import SearchLogInfo
import utils.utils as utils
from time import time
from boosting_decision_making import weighted_similarity_calculator
from boosting_decision_making import similarity_calculator
from commons.es_query_builder import EsQueryBuilder
from commons.log_merger import LogMerger
from queue import Queue
from commons import namespace_finder
from commons.triggering_training.retraining_defect_type_triggering import RetrainingDefectTypeTriggering
from commons.log_preparation import LogPreparation
from amqp.amqp import AmqpClient

logger = logging.getLogger("analyzerApp.esclient")


class EsClient:
    """Elasticsearch client implementation"""
    def __init__(self, app_config={}, search_cfg={}):
        self.app_config = app_config
        self.host = app_config["esHost"]
        self.search_cfg = search_cfg
        self.es_client = elasticsearch.Elasticsearch([self.host], timeout=30,
                                                     max_retries=5, retry_on_timeout=True,
                                                     use_ssl=app_config["esUseSsl"],
                                                     verify_certs=app_config["esVerifyCerts"],
                                                     ssl_show_warn=app_config["esSslShowWarn"],
                                                     ca_certs=app_config["esCAcert"],
                                                     client_cert=app_config["esClientCert"],
                                                     client_key=app_config["esClientKey"])
        self.weighted_log_similarity_calculator = None
        self.namespace_finder = namespace_finder.NamespaceFinder(app_config)
        self.es_query_builder = EsQueryBuilder(self.search_cfg, utils.ERROR_LOGGING_LEVEL)
        self.log_preparation = LogPreparation()
        self.model_training_triggering = {
            "defect_type": RetrainingDefectTypeTriggering(self.app_config)
        }
        if self.search_cfg["SimilarityWeightsFolder"].strip():
            self.weighted_log_similarity_calculator = weighted_similarity_calculator.\
                WeightedSimilarityCalculator(folder=self.search_cfg["SimilarityWeightsFolder"])

    def create_es_client(self, app_config):
        if app_config["turnOffSslVerification"]:
            return elasticsearch.Elasticsearch(
                [self.host], timeout=30,
                max_retries=5, retry_on_timeout=True,
                use_ssl=app_config["esUseSsl"],
                verify_certs=app_config["esVerifyCerts"],
                ssl_show_warn=app_config["esSslShowWarn"],
                ca_certs=app_config["esCAcert"],
                client_cert=app_config["esClientCert"],
                client_key=app_config["esClientKey"],
                connection_class=RequestsHttpConnection)
        return elasticsearch.Elasticsearch(
            [self.host], timeout=30,
            max_retries=5, retry_on_timeout=True,
            use_ssl=app_config["esUseSsl"],
            verify_certs=app_config["esVerifyCerts"],
            ssl_show_warn=app_config["esSslShowWarn"],
            ca_certs=app_config["esCAcert"],
            client_cert=app_config["esClientCert"],
            client_key=app_config["esClientKey"])

    def update_settings_after_read_only(self, es_host):
        try:
            requests.put(
                "{}/_all/_settings".format(
                    es_host
                ),
                headers={"Content-Type": "application/json"},
                data="{\"index.blocks.read_only_allow_delete\": null}"
            ).raise_for_status()
        except Exception as err:
            logger.error(err)
            logger.error("Can't reset read only mode for elastic indices")

    def create_index(self, index_name):
        """Create index in elasticsearch"""
        logger.debug("Creating '%s' Elasticsearch index", str(index_name))
        logger.info("ES Url %s", utils.remove_credentials_from_url(self.host))
        try:
            response = self.es_client.indices.create(index=str(index_name), body={
                'settings': utils.read_json_file("", "index_settings.json", to_json=True),
                'mappings': utils.read_json_file("", "index_mapping_settings.json", to_json=True)
            })
            logger.debug("Created '%s' Elasticsearch index", str(index_name))
            return commons.launch_objects.Response(**response)
        except Exception as err:
            logger.error("Couldn't create index")
            logger.error("ES Url %s", utils.remove_credentials_from_url(self.host))
            logger.error(err)
            return commons.launch_objects.Response()

    def list_indices(self):
        """Get all indices from elasticsearch"""
        url = utils.build_url(self.host, ["_cat", "indices?format=json"])
        res = utils.send_request(url, "GET")
        return res

    def index_exists(self, index_name, print_error=True):
        """Checks whether index exists"""
        try:
            index = self.es_client.indices.get(index=str(index_name))
            return index is not None
        except Exception as err:
            if print_error:
                logger.error("Index %s was not found", str(index_name))
                logger.error("ES Url %s", self.host)
                logger.error(err)
            return False

    def delete_index(self, index_name):
        """Delete the whole index"""
        try:
            self.namespace_finder.remove_namespaces(index_name)
            for model_type in self.model_training_triggering:
                self.model_training_triggering[model_type].remove_triggering_info(
                    {"project_id": index_name})
            self.es_client.indices.delete(index=str(index_name))
            logger.info("ES Url %s", utils.remove_credentials_from_url(self.host))
            logger.debug("Deleted index %s", str(index_name))
            return 1
        except Exception as err:
            logger.error("Not found %s for deleting", str(index_name))
            logger.error("ES Url %s", utils.remove_credentials_from_url(self.host))
            logger.error(err)
            return 0

    def create_index_if_not_exists(self, index_name):
        """Creates index if it doesn't not exist"""
        if not self.index_exists(index_name, print_error=False):
            return self.create_index(index_name)
        return True

    def index_logs(self, launches):
        """Index launches to the index with project name"""
        cnt_launches = len(launches)
        logger.info("Indexing logs for %d launches", cnt_launches)
        logger.info("ES Url %s", utils.remove_credentials_from_url(self.host))
        t_start = time()
        bodies = []
        test_item_ids = []
        project = None
        test_item_queue = Queue()
        for launch in launches:
            project = str(launch.project)
            test_items = launch.testItems
            launch.testItems = []
            self.create_index_if_not_exists(str(launch.project))
            for test_item in test_items:
                test_item_queue.put((launch, test_item))
        del launches
        while not test_item_queue.empty():
            launch, test_item = test_item_queue.get()
            logs_added = False
            for log in test_item.logs:
                if log.logLevel < utils.ERROR_LOGGING_LEVEL or not log.message.strip():
                    continue

                bodies.append(self.log_preparation._prepare_log(launch, test_item, log))
                logs_added = True
            if logs_added:
                test_item_ids.append(str(test_item.testItemId))

        logs_with_exceptions = utils.extract_all_exceptions(bodies)
        result = self._bulk_index(bodies)
        result.logResults = logs_with_exceptions
        _, num_logs_with_defect_types = self._merge_logs(test_item_ids, project)
        try:
            if "amqpUrl" in self.app_config and self.app_config["amqpUrl"].strip():
                AmqpClient(self.app_config["amqpUrl"]).send_to_inner_queue(
                    self.app_config["exchangeName"], "train_models", json.dumps({
                        "model_type": "defect_type",
                        "project_id": project,
                        "num_logs_with_defect_types": num_logs_with_defect_types
                    }))
        except Exception as err:
            logger.error(err)
        logger.info("Finished indexing logs for %d launches. It took %.2f sec.",
                    cnt_launches, time() - t_start)
        return result

    def _merge_logs(self, test_item_ids, project):
        bodies = []
        batch_size = 1000
        self._delete_merged_logs(test_item_ids, project)
        num_logs_with_defect_types = 0
        for i in range(int(len(test_item_ids) / batch_size) + 1):
            test_items = test_item_ids[i * batch_size: (i + 1) * batch_size]
            if not test_items:
                continue
            test_items_dict = {}
            for r in elasticsearch.helpers.scan(self.es_client,
                                                query=self.es_query_builder.get_test_item_query(
                                                    test_items, False),
                                                index=project):
                test_item_id = r["_source"]["test_item"]
                if test_item_id not in test_items_dict:
                    test_items_dict[test_item_id] = []
                test_items_dict[test_item_id].append(r)
            for test_item_id in test_items_dict:
                merged_logs = LogMerger.decompose_logs_merged_and_without_duplicates(
                    test_items_dict[test_item_id])
                for log in merged_logs:
                    if log["_source"]["is_merged"]:
                        bodies.append(log)
                    else:
                        bodies.append({
                            "_op_type": "update",
                            "_id": log["_id"],
                            "_index": log["_index"],
                            "doc": {"merged_small_logs": log["_source"]["merged_small_logs"]}
                        })
                    log_issue_type = log["_source"]["issue_type"]
                    if log_issue_type.strip() and not log_issue_type.lower().startswith("ti"):
                        num_logs_with_defect_types += 1
        return self._bulk_index(bodies), num_logs_with_defect_types

    def _delete_merged_logs(self, test_items_to_delete, project):
        logger.debug("Delete merged logs for %d test items", len(test_items_to_delete))
        bodies = []
        batch_size = 1000
        for i in range(int(len(test_items_to_delete) / batch_size) + 1):
            test_item_ids = test_items_to_delete[i * batch_size: (i + 1) * batch_size]
            if not test_item_ids:
                continue
            for log in elasticsearch.helpers.scan(self.es_client,
                                                  query=self.es_query_builder.get_test_item_query(
                                                      test_item_ids, True),
                                                  index=project):
                bodies.append({
                    "_op_type": "delete",
                    "_id": log["_id"],
                    "_index": project
                })
        if bodies:
            self._bulk_index(bodies)

    def _bulk_index(self, bodies, host=None, es_client=None, refresh=True):
        if host is None:
            host = self.host
        if es_client is None:
            es_client = self.es_client
        if not bodies:
            return commons.launch_objects.BulkResponse(took=0, errors=False)
        logger.debug("Indexing %d logs...", len(bodies))
        try:
            try:
                success_count, errors = elasticsearch.helpers.bulk(es_client,
                                                                   bodies,
                                                                   chunk_size=1000,
                                                                   request_timeout=30,
                                                                   refresh=refresh)
            except Exception as err:
                logger.error(err)
                self.update_settings_after_read_only(host)
                success_count, errors = elasticsearch.helpers.bulk(es_client,
                                                                   bodies,
                                                                   chunk_size=1000,
                                                                   request_timeout=30,
                                                                   refresh=refresh)
            logger.debug("Processed %d logs", success_count)
            if errors:
                logger.debug("Occured errors %s", errors)
            return commons.launch_objects.BulkResponse(took=success_count, errors=len(errors) > 0)
        except Exception as err:
            logger.error("Error in bulk")
            logger.error("ES Url %s", utils.remove_credentials_from_url(host))
            logger.error(err)
            return commons.launch_objects.BulkResponse(took=0, errors=True)

    def delete_logs(self, clean_index):
        """Delete logs from elasticsearch"""
        logger.info("Delete logs %s for the project %s",
                    clean_index.ids, clean_index.project)
        logger.info("ES Url %s", utils.remove_credentials_from_url(self.host))
        t_start = time()
        if not self.index_exists(clean_index.project):
            return 0
        test_item_ids = set()
        try:
            search_query = self.es_query_builder.build_search_test_item_ids_query(
                clean_index.ids)
            for res in elasticsearch.helpers.scan(self.es_client,
                                                  query=search_query,
                                                  index=clean_index.project,
                                                  scroll="5m"):
                test_item_ids.add(res["_source"]["test_item"])
        except Exception as err:
            logger.error("Couldn't find test items for logs")
            logger.error(err)

        bodies = []
        for _id in clean_index.ids:
            bodies.append({
                "_op_type": "delete",
                "_id":      _id,
                "_index":   clean_index.project,
            })
        result = self._bulk_index(bodies)
        self._merge_logs(list(test_item_ids), clean_index.project)
        logger.info("Finished deleting logs %s for the project %s. It took %.2f sec",
                    clean_index.ids, clean_index.project, time() - t_start)
        return result.took

    def search_logs(self, search_req):
        """Get all logs similar to given logs"""
        similar_log_ids = set()
        logger.info("Started searching by request %s", search_req.json())
        logger.info("ES Url %s", utils.remove_credentials_from_url(self.host))
        t_start = time()
        if not self.index_exists(str(search_req.projectId)):
            return []
        searched_logs = set()
        test_item_info = {}

        for message in search_req.logMessages:
            if not message.strip():
                continue

            queried_log = self.log_preparation._create_log_template()
            queried_log = self.log_preparation._fill_log_fields(
                queried_log,
                commons.launch_objects.Log(logId=0, message=message),
                search_req.logLines)

            msg_words = " ".join(utils.split_words(queried_log["_source"]["message"]))
            if not msg_words.strip() or msg_words in searched_logs:
                continue
            searched_logs.add(msg_words)
            query = self.es_query_builder.build_search_query(
                search_req, queried_log["_source"]["message"])
            res = self.es_client.search(index=str(search_req.projectId), body=query)
            for es_res in res["hits"]["hits"]:
                test_item_info[es_res["_id"]] = es_res["_source"]["test_item"]

            _similarity_calculator = similarity_calculator.SimilarityCalculator(
                {
                    "max_query_terms": self.search_cfg["MaxQueryTerms"],
                    "min_word_length": self.search_cfg["MinWordLength"],
                    "min_should_match": "90%",
                    "number_of_log_lines": search_req.logLines
                },
                weighted_similarity_calculator=self.weighted_log_similarity_calculator)
            _similarity_calculator.find_similarity([(queried_log, res)], ["message"])

            for group_id, similarity_obj in _similarity_calculator.similarity_dict["message"].items():
                log_id, _ = group_id
                similarity_percent = similarity_obj["similarity"]
                logger.debug("Log with id %s has %.3f similarity with the queried log '%s'",
                             log_id, similarity_percent, queried_log["_source"]["message"])
                if similarity_percent >= self.search_cfg["SearchLogsMinSimilarity"]:
                    similar_log_ids.add((utils.extract_real_id(log_id), int(test_item_info[log_id])))

        logger.info("Finished searching by request %s with %d results. It took %.2f sec.",
                    search_req.json(), len(similar_log_ids), time() - t_start)
        return [SearchLogInfo(logId=log_info[0],
                              testItemId=log_info[1]) for log_info in similar_log_ids]

    def create_index_for_stats_info(self, es_client, rp_aa_stats_index):
        index = None
        try:
            index = es_client.indices.get(index=rp_aa_stats_index)
        except Exception:
            pass
        if index is None:
            es_client.indices.create(index=rp_aa_stats_index, body={
                'settings': utils.read_json_file("", "index_settings.json", to_json=True),
                'mappings': utils.read_json_file(
                    "", "rp_aa_stats_mappings.json", to_json=True)
            })
        else:
            es_client.indices.put_mapping(
                index=rp_aa_stats_index,
                body=utils.read_json_file("", "rp_aa_stats_mappings.json", to_json=True))

    @utils.ignore_warnings
    def send_stats_info(self, stats_info):
        rp_aa_stats_index = "rp_aa_stats"
        logger.info("Started sending stats about analysis")
        self.create_index_for_stats_info(self.es_client, rp_aa_stats_index)

        stat_info_array = []
        for launch_id in stats_info:
            stat_info_array.append({
                "_index": rp_aa_stats_index,
                "_source": stats_info[launch_id]
            })
        self._bulk_index(stat_info_array)
        logger.info("Finished sending stats about analysis")

    @utils.ignore_warnings
    def update_chosen_namespaces(self, launches):
        logger.info("Started updating chosen namespaces")
        t_start = time()
        log_words, project_id = self.log_preparation.prepare_log_words(launches)
        logger.debug("Project id %s", project_id)
        logger.debug("Found namespaces %s", log_words)
        if project_id is not None:
            self.namespace_finder.update_namespaces(
                project_id, log_words)
        logger.info("Finished updating chosen namespaces %.2f s", time() - t_start)

    @utils.ignore_warnings
    def train_models(self, train_info):
        logger.info("Started training")
        t_start = time()
        assert train_info["model_type"] in self.model_training_triggering

        _retraining_defect_type_triggering = self.model_training_triggering[train_info["model_type"]]
        if _retraining_defect_type_triggering.should_model_training_be_triggered(train_info):
            print("Should be trained ", train_info)
        logger.info("Finished training %.2f s", time() - t_start)
