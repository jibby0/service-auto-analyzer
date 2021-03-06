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
from utils import utils
from commons.launch_objects import SuggestAnalysisResult
from boosting_decision_making import boosting_decision_maker
from boosting_decision_making.suggest_boosting_featurizer import SuggestBoostingFeaturizer
from amqp.amqp import AmqpClient
from commons.log_merger import LogMerger
from service.analyzer_service import AnalyzerService
from commons import similarity_calculator
import json
import logging
from time import time
from datetime import datetime

logger = logging.getLogger("analyzerApp.suggestService")


class SuggestService(AnalyzerService):

    def __init__(self, app_config={}, search_cfg={}):
        super(SuggestService, self).__init__(app_config=app_config, search_cfg=search_cfg)
        self.suggest_threshold = 0.4
        if self.search_cfg["SuggestBoostModelFolder"].strip():
            self.suggest_decision_maker = boosting_decision_maker.BoostingDecisionMaker(
                folder=self.search_cfg["SuggestBoostModelFolder"])

    def get_config_for_boosting_suggests(self, analyzerConfig):
        return {
            "max_query_terms": self.search_cfg["MaxQueryTerms"],
            "min_should_match": 0.4,
            "min_word_length": self.search_cfg["MinWordLength"],
            "filter_min_should_match": [],
            "filter_min_should_match_any": self.choose_fields_to_filter_suggests(
                analyzerConfig.numberOfLogLines),
            "number_of_log_lines": analyzerConfig.numberOfLogLines,
            "filter_by_unique_id": True}

    def choose_fields_to_filter_suggests(self, log_lines_num):
        if log_lines_num == -1:
            return [
                "detected_message_extended",
                "detected_message_without_params_extended",
                "detected_message_without_params_and_brackets"]
        return ["message_extended", "message_without_params_extended",
                "message_without_params_and_brackets"]

    def build_suggest_query(self, test_item_info, log, size=10,
                            message_field="message", det_mes_field="detected_message",
                            stacktrace_field="stacktrace"):
        min_should_match = "{}%".format(test_item_info.analyzerConfig.minShouldMatch)\
            if test_item_info.analyzerConfig.minShouldMatch > 0\
            else self.search_cfg["MinShouldMatch"]
        log_lines = test_item_info.analyzerConfig.numberOfLogLines

        query = self.build_common_query(log, size=size)

        if test_item_info.analyzerConfig.analyzerMode in ["LAUNCH_NAME"]:
            query["query"]["bool"]["must"].append(
                {"term": {
                    "launch_name": {
                        "value": test_item_info.launchName}}})
        elif test_item_info.analyzerConfig.analyzerMode in ["CURRENT_LAUNCH"]:
            query["query"]["bool"]["must"].append(
                {"term": {
                    "launch_id": {
                        "value": test_item_info.launchId}}})
        else:
            query["query"]["bool"]["should"].append(
                {"term": {
                    "launch_name": {
                        "value": test_item_info.launchName,
                        "boost": abs(self.search_cfg["BoostLaunch"])}}})

        if log["_source"]["message"].strip():
            query["query"]["bool"]["filter"].append({"term": {"is_merged": False}})
            if log_lines == -1:
                query["query"]["bool"]["must"].append(
                    self.build_more_like_this_query("60%",
                                                    log["_source"][det_mes_field],
                                                    field_name=det_mes_field,
                                                    boost=4.0))
                if log["_source"][stacktrace_field].strip():
                    query["query"]["bool"]["must"].append(
                        self.build_more_like_this_query("60%",
                                                        log["_source"][stacktrace_field],
                                                        field_name=stacktrace_field,
                                                        boost=2.0))
                else:
                    query["query"]["bool"]["must_not"].append({"wildcard": {stacktrace_field: "*"}})
            else:
                query["query"]["bool"]["must"].append(
                    self.build_more_like_this_query("60%",
                                                    log["_source"][message_field],
                                                    field_name=message_field,
                                                    boost=4.0))
                query["query"]["bool"]["should"].append(
                    self.build_more_like_this_query("60%",
                                                    log["_source"][stacktrace_field],
                                                    field_name=stacktrace_field,
                                                    boost=1.0))
                query["query"]["bool"]["should"].append(
                    self.build_more_like_this_query(
                        "60%",
                        log["_source"]["detected_message_without_params_extended"],
                        field_name="detected_message_without_params_extended",
                        boost=1.0))
            query["query"]["bool"]["should"].append(
                self.build_more_like_this_query("80%",
                                                log["_source"]["merged_small_logs"],
                                                field_name="merged_small_logs",
                                                boost=0.5))
            query["query"]["bool"]["should"].append(
                self.build_more_like_this_query("1",
                                                log["_source"]["only_numbers"],
                                                field_name="only_numbers",
                                                boost=4.0,
                                                override_min_should_match="1"))
            query["query"]["bool"]["should"].append(
                self.build_more_like_this_query("1",
                                                log["_source"]["message_params"],
                                                field_name="message_params",
                                                boost=4.0,
                                                override_min_should_match="1"))
            query["query"]["bool"]["should"].append(
                self.build_more_like_this_query("1",
                                                log["_source"]["urls"],
                                                field_name="urls",
                                                boost=4.0,
                                                override_min_should_match="1"))
            query["query"]["bool"]["should"].append(
                self.build_more_like_this_query("1",
                                                log["_source"]["paths"],
                                                field_name="paths",
                                                boost=4.0,
                                                override_min_should_match="1"))
        else:
            query["query"]["bool"]["filter"].append({"term": {"is_merged": True}})
            query["query"]["bool"]["must_not"].append({"wildcard": {"message": "*"}})
            query["query"]["bool"]["must"].append(
                self.build_more_like_this_query(min_should_match,
                                                log["_source"]["merged_small_logs"],
                                                field_name="merged_small_logs",
                                                boost=2.0))

        query["query"]["bool"]["should"].append(
            self.build_more_like_this_query("1",
                                            log["_source"]["found_exceptions_extended"],
                                            field_name="found_exceptions_extended",
                                            boost=4.0,
                                            override_min_should_match="1"))
        query["query"]["bool"]["should"].append(
            self.build_more_like_this_query("1",
                                            log["_source"]["potential_status_codes"],
                                            field_name="potential_status_codes",
                                            boost=4.0,
                                            override_min_should_match="1"))

        return query

    def query_es_for_suggested_items(self, test_item_info, logs):
        full_results = []

        for log in logs:
            message = log["_source"]["message"].strip()
            merged_small_logs = log["_source"]["merged_small_logs"].strip()
            if log["_source"]["log_level"] < utils.ERROR_LOGGING_LEVEL or\
                    (not message and not merged_small_logs):
                continue

            query = self.build_suggest_query(
                test_item_info, log,
                message_field="message_extended",
                det_mes_field="detected_message_extended",
                stacktrace_field="stacktrace_extended")
            es_res = self.es_client.es_client.search(index=str(test_item_info.project), body=query)
            full_results.append((log, es_res))

            query = self.build_suggest_query(
                test_item_info, log,
                message_field="message_without_params_extended",
                det_mes_field="detected_message_without_params_extended",
                stacktrace_field="stacktrace_extended")
            es_res = self.es_client.es_client.search(index=str(test_item_info.project), body=query)
            full_results.append((log, es_res))

            query = self.build_suggest_query(
                test_item_info, log,
                message_field="message_without_params_and_brackets",
                det_mes_field="detected_message_without_params_and_brackets",
                stacktrace_field="stacktrace_extended")
            es_res = self.es_client.es_client.search(index=str(test_item_info.project), body=query)
            full_results.append((log, es_res))
        return full_results

    def deduplicate_results(self, gathered_results, scores_by_test_items, test_item_ids):
        _similarity_calculator = similarity_calculator.SimilarityCalculator(
            {
                "max_query_terms": self.search_cfg["MaxQueryTerms"],
                "min_word_length": self.search_cfg["MinWordLength"],
                "min_should_match": "98%",
                "number_of_log_lines": -1
            },
            weighted_similarity_calculator=self.weighted_log_similarity_calculator)
        all_pairs_to_check = []
        for i in range(len(gathered_results)):
            for j in range(i + 1, len(gathered_results)):
                test_item_id_first = test_item_ids[gathered_results[i][0]]
                test_item_id_second = test_item_ids[gathered_results[j][0]]
                issue_type1 = scores_by_test_items[test_item_id_first]["mrHit"]["_source"]["issue_type"]
                issue_type2 = scores_by_test_items[test_item_id_second]["mrHit"]["_source"]["issue_type"]
                if issue_type1 != issue_type2:
                    continue
                items_to_compare = {"hits": {"hits": [scores_by_test_items[test_item_id_first]["mrHit"]]}}
                all_pairs_to_check.append((scores_by_test_items[test_item_id_second]["mrHit"],
                                           items_to_compare))
        _similarity_calculator.find_similarity(
            all_pairs_to_check,
            ["detected_message_with_numbers", "stacktrace", "merged_small_logs"])

        filtered_results = []
        deleted_indices = set()
        for i in range(len(gathered_results)):
            if i in deleted_indices:
                continue
            for j in range(i + 1, len(gathered_results)):
                test_item_id_first = test_item_ids[gathered_results[i][0]]
                test_item_id_second = test_item_ids[gathered_results[j][0]]
                group_id = (scores_by_test_items[test_item_id_first]["mrHit"]["_id"],
                            scores_by_test_items[test_item_id_second]["mrHit"]["_id"])
                if group_id not in _similarity_calculator.similarity_dict["detected_message_with_numbers"]:
                    continue
                det_message = _similarity_calculator.similarity_dict["detected_message_with_numbers"]
                detected_message_sim = det_message[group_id]
                stacktrace_sim = _similarity_calculator.similarity_dict["stacktrace"][group_id]
                merged_logs_sim = _similarity_calculator.similarity_dict["merged_small_logs"][group_id]
                if detected_message_sim["similarity"] >= 0.98 and\
                        stacktrace_sim["similarity"] >= 0.98 and merged_logs_sim["similarity"] >= 0.98:
                    deleted_indices.add(j)
            filtered_results.append(gathered_results[i])
        return filtered_results

    def sort_results(self, scores_by_test_items, test_item_ids, predicted_labels_probability):
        gathered_results = []
        for idx, prob in enumerate(predicted_labels_probability):
            test_item_id = test_item_ids[idx]
            gathered_results.append(
                (idx,
                 round(prob[1], 2),
                 scores_by_test_items[test_item_id]["mrHit"]["_source"]["start_time"]))

        gathered_results = sorted(gathered_results, key=lambda x: (x[1], x[2]), reverse=True)
        return self.deduplicate_results(gathered_results, scores_by_test_items, test_item_ids)

    @utils.ignore_warnings
    def suggest_items(self, test_item_info, num_items=5):
        logger.info("Started suggesting test items")
        logger.info("ES Url %s", utils.remove_credentials_from_url(self.es_client.host))
        if not self.es_client.index_exists(str(test_item_info.project)):
            logger.info("Project %d doesn't exist", test_item_info.project)
            logger.info("Finished suggesting for test item with 0 results.")
            return []

        t_start = time()
        results = []
        unique_logs = utils.leave_only_unique_logs(test_item_info.logs)
        prepared_logs = [self.log_preparation._prepare_log_for_suggests(test_item_info, log)
                         for log in unique_logs if log.logLevel >= utils.ERROR_LOGGING_LEVEL]
        logs = LogMerger.decompose_logs_merged_and_without_duplicates(prepared_logs)
        searched_res = self.query_es_for_suggested_items(test_item_info, logs)

        boosting_config = self.get_config_for_boosting_suggests(test_item_info.analyzerConfig)
        boosting_config["chosen_namespaces"] = self.namespace_finder.get_chosen_namespaces(
            test_item_info.project)

        _boosting_data_gatherer = SuggestBoostingFeaturizer(
            searched_res,
            boosting_config,
            feature_ids=self.suggest_decision_maker.get_feature_ids(),
            weighted_log_similarity_calculator=self.weighted_log_similarity_calculator)
        defect_type_model_to_use = self.choose_model(
            test_item_info.project, "defect_type_model/")
        if defect_type_model_to_use is None:
            _boosting_data_gatherer.set_defect_type_model(self.global_defect_type_model)
        else:
            _boosting_data_gatherer.set_defect_type_model(defect_type_model_to_use)
        feature_data, test_item_ids = _boosting_data_gatherer.gather_features_info()
        scores_by_test_items = _boosting_data_gatherer.scores_by_issue_type
        model_info_tags = _boosting_data_gatherer.get_used_model_info() +\
            self.suggest_decision_maker.get_model_info()

        if feature_data:
            predicted_labels, predicted_labels_probability = self.suggest_decision_maker.predict(feature_data)
            sorted_results = self.sort_results(
                scores_by_test_items, test_item_ids, predicted_labels_probability)

            logger.debug("Found %d results for test items ", len(sorted_results))
            for idx, prob, _ in sorted_results:
                test_item_id = test_item_ids[idx]
                issue_type = scores_by_test_items[test_item_id]["mrHit"]["_source"]["issue_type"]
                logger.debug("Test item id %d with issue type %s has probability %.2f",
                             test_item_id, issue_type, prob)

            global_idx = 0
            for idx, prob, _ in sorted_results[:num_items]:
                if prob >= self.suggest_threshold:
                    test_item_id = test_item_ids[idx]
                    issue_type = scores_by_test_items[test_item_id]["mrHit"]["_source"]["issue_type"]
                    relevant_log_id = utils.extract_real_id(
                        scores_by_test_items[test_item_id]["mrHit"]["_id"])
                    test_item_log_id = utils.extract_real_id(
                        scores_by_test_items[test_item_id]["compared_log"]["_id"])
                    analysis_result = SuggestAnalysisResult(
                        testItem=test_item_info.testItemId,
                        testItemLogId=test_item_log_id,
                        issueType=issue_type,
                        relevantItem=test_item_id,
                        relevantLogId=relevant_log_id,
                        matchScore=round(prob * 100, 2),
                        esScore=round(scores_by_test_items[test_item_id]["mrHit"]["_score"], 2),
                        esPosition=scores_by_test_items[test_item_id]["mrHit"]["es_pos"],
                        modelFeatureNames=";".join(
                            [str(feature) for feature in self.suggest_decision_maker.get_feature_ids()]),
                        modelFeatureValues=";".join(
                            [str(feature) for feature in feature_data[idx]]),
                        modelInfo=";".join(model_info_tags),
                        resultPosition=global_idx,
                        usedLogLines=test_item_info.analyzerConfig.numberOfLogLines,
                        minShouldMatch=self.find_min_should_match_threshold(test_item_info.analyzerConfig))
                    results.append(analysis_result)
                    logger.debug(analysis_result)
                global_idx += 1
        else:
            logger.debug("There are no results for test item %s", test_item_info.testItemId)
        results_to_share = {test_item_info.launchId: {
            "not_found": int(len(results) == 0), "items_to_process": 1,
            "processed_time": time() - t_start, "found_items": len(results),
            "launch_id": test_item_info.launchId, "launch_name": test_item_info.launchName,
            "project_id": test_item_info.project, "method": "suggest",
            "gather_date": datetime.now().strftime("%Y-%m-%d"),
            "gather_datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "number_of_log_lines": test_item_info.analyzerConfig.numberOfLogLines,
            "model_info": model_info_tags,
            "module_version": [self.app_config["appVersion"]],
            "min_should_match": self.find_min_should_match_threshold(
                test_item_info.analyzerConfig)}}
        if "amqpUrl" in self.app_config and self.app_config["amqpUrl"].strip():
            AmqpClient(self.app_config["amqpUrl"]).send_to_inner_queue(
                self.app_config["exchangeName"], "stats_info", json.dumps(results_to_share))

        logger.debug("Stats info %s", results_to_share)
        logger.info("Processed the test item. It took %.2f sec.", time() - t_start)
        logger.info("Finished suggesting for test item with %d results.", len(results))
        return results
