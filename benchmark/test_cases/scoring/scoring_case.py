from benchmark.benchmark_model_types import BenchmarkModelTypesEnum
from benchmark.benchmark_utils import get_models_hyperparameters, get_scoring_case_data_paths, \
    save_metrics_result_file
from benchmark.executor import CaseExecutor
from core.repository.tasks import TaskTypesEnum

if __name__ == '__main__':
    train_file, test_file = get_scoring_case_data_paths()

    result_metrics = CaseExecutor(train_file=train_file,
                                  test_file=test_file,
                                  task=TaskTypesEnum.classification,
                                  models=[BenchmarkModelTypesEnum.tpot,
                                          BenchmarkModelTypesEnum.fedot],
                                  target_name='default',
                                  case_label='scoring',
                                  metric_list=['roc_auc', 'f1']).execute()

    result_metrics['hyperparameters'] = get_models_hyperparameters()

    save_metrics_result_file(result_metrics, file_name='scoring_metrics')
