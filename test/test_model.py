import numpy as np
import pytest
from sklearn.metrics import roc_auc_score as roc_auc

from core.models.data import InputData, train_test_data_setup
from core.models.model import Model
from core.models.preprocessing import scaling_preprocess
from core.repository.model_types_repository import ModelTypesIdsEnum
from core.repository.task_types import MachineLearningTasksEnum


@pytest.fixture()
def classification_dataset():
    samples = 1000
    x = 10.0 * np.random.rand(samples, ) - 5.0
    x = np.expand_dims(x, axis=1)
    y = 1.0 / (1.0 + np.exp(np.power(x, -1.0)))
    threshold = 0.5
    classes = np.array([0.0 if val <= threshold else 1.0 for val in y])
    classes = np.expand_dims(classes, axis=1)
    data = InputData(features=x, target=classes, idx=np.arange(0, len(x)),
                     task_type=MachineLearningTasksEnum.classification)

    return data


def test_log_regression_fit_correct(classification_dataset):
    data = classification_dataset
    data.features = scaling_preprocess(data.features)
    train_data, test_data = train_test_data_setup(data=data)

    log_reg = Model(model_type=ModelTypesIdsEnum.logit)

    _, train_predicted = log_reg.fit(data=train_data)
    roc_on_train = roc_auc(y_true=train_data.target,
                           y_score=train_predicted)
    roc_threshold = 0.95
    assert roc_on_train >= roc_threshold


@pytest.mark.parametrize('data_fixture', ['classification_dataset'])
def test_random_forest_fit_correct(data_fixture, request):
    data = request.getfixturevalue(data_fixture)
    data.features = scaling_preprocess(data.features)
    train_data, test_data = train_test_data_setup(data=data)

    random_forest = Model(model_type=ModelTypesIdsEnum.rf)

    _, train_predicted = random_forest.fit(data=train_data)
    roc_on_train = roc_auc(y_true=train_data.target,
                           y_score=train_predicted)
    roc_threshold = 0.95
    assert roc_on_train >= roc_threshold


@pytest.mark.parametrize('data_fixture', ['classification_dataset'])
def test_decision_tree_fit_correct(data_fixture, request):
    data = request.getfixturevalue(data_fixture)
    data.features = scaling_preprocess(data.features)
    train_data, test_data = train_test_data_setup(data=data)

    decision_tree = Model(model_type=ModelTypesIdsEnum.dt)

    decision_tree.fit(data=train_data)
    _, train_predicted = decision_tree.fit(data=train_data)
    roc_on_train = roc_auc(y_true=train_data.target,
                           y_score=train_predicted)
    roc_threshold = 0.95
    assert roc_on_train >= roc_threshold


@pytest.mark.parametrize('data_fixture', ['classification_dataset'])
def test_lda_fit_correct(data_fixture, request):
    data = request.getfixturevalue(data_fixture)
    data.features = scaling_preprocess(data.features)
    train_data, test_data = train_test_data_setup(data=data)

    lda = Model(model_type=ModelTypesIdsEnum.lda)

    _, train_predicted = lda.fit(data=train_data)
    roc_on_train = roc_auc(y_true=train_data.target,
                           y_score=train_predicted)
    roc_threshold = 0.95
    assert roc_on_train >= roc_threshold


@pytest.mark.parametrize('data_fixture', ['classification_dataset'])
def test_qda_fit_correct(data_fixture, request):
    data = request.getfixturevalue(data_fixture)
    data.features = scaling_preprocess(data.features)
    train_data, test_data = train_test_data_setup(data=data)

    qda = Model(model_type=ModelTypesIdsEnum.qda)

    _, train_predicted = qda.fit(data=train_data)
    roc_on_train = roc_auc(y_true=train_data.target,
                           y_score=train_predicted)
    roc_threshold = 0.95
    assert roc_on_train >= roc_threshold


@pytest.mark.parametrize('data_fixture', ['classification_dataset'])
def test_log_clustering_fit_correct(data_fixture, request):
    data = request.getfixturevalue(data_fixture)
    data.features = scaling_preprocess(data.features)
    train_data, test_data = train_test_data_setup(data=data)

    kmeans = Model(model_type=ModelTypesIdsEnum.kmeans)

    _, train_predicted = kmeans.fit(data=train_data)

    assert all(np.unique(train_predicted) == [0, 1])
