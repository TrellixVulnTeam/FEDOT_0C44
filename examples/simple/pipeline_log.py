import os

import pathlib

from examples.simple.classification.classification_pipelines import classification_complex_pipeline
from examples.simple.pipeline_tune import get_case_train_test_data, get_scoring_case_data_paths
from fedot.core.log import Log
from test.unit.test_logger import release_log


def run_log_example(log_file):
    train_data, test_data = get_case_train_test_data()

    # Use default_log if you do not have json config file for log
    log = Log(logger_name='logger', log_file=log_file)
    log_adapter = log.get_adapter(prefix=pathlib.Path(__file__).stem)

    log_adapter.info('start creating pipeline')
    pipeline = classification_complex_pipeline()

    log_adapter.info('start fitting pipeline')
    pipeline.fit(train_data, use_fitted=False)


if __name__ == '__main__':
    run_log_example(log_file='example_log.log')
